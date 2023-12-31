"""
rag/pipeline.py

Fetches docs from GitHub, chunks them, embeds with OpenAI,
stores in Qdrant, and retrieves relevant chunks at query time.
Re-indexed every 6h automatically and on GitHub webhook push.
"""

from __future__ import annotations

import hashlib
import logging
import requests
from typing import List

from config.settings import (
    GITHUB_REPO, GITHUB_TOKEN, DOCS_PATHS,
    QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION,
    OPENAI_API_KEY, EMBEDDING_MODEL,
)

logger = logging.getLogger(__name__)

CHUNK_SIZE    = 500   # words per chunk
CHUNK_OVERLAP = 50
TOP_K         = 3


# ── GitHub ────────────────────────────────────────────────────────────────────

def fetch_github_docs() -> List[dict]:
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    docs = []
    for path in DOCS_PATHS:
        path = path.strip()
        if not path:
            continue
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"GitHub fetch failed for {path}: {resp.status_code}")
            continue
        data = resp.json()
        if isinstance(data, dict) and data.get("type") == "file":
            text = requests.get(data["download_url"], timeout=15).text
            docs.append({"source": path, "text": text})
        elif isinstance(data, list):
            for item in data:
                if item.get("name", "").endswith(".md"):
                    text = requests.get(item["download_url"], timeout=15).text
                    docs.append({"source": item["path"], "text": text})
    return docs


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(text: str, source: str) -> List[dict]:
    words = text.split()
    step = CHUNK_SIZE - CHUNK_OVERLAP
    chunks = []
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + CHUNK_SIZE])
        chunk_id = hashlib.md5(f"{source}_{i}".encode()).hexdigest()
        chunks.append({"id": chunk_id, "source": source, "text": chunk})
    return chunks


# ── Embeddings ────────────────────────────────────────────────────────────────

def embed_texts(texts: List[str]) -> List[List[float]]:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in resp.data]


# ── Qdrant ────────────────────────────────────────────────────────────────────

def _client():
    from qdrant_client import QdrantClient
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

def _ensure_collection(vector_size: int):
    from qdrant_client.models import Distance, VectorParams
    c = _client()
    names = [col.name for col in c.get_collections().collections]
    if QDRANT_COLLECTION not in names:
        c.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info(f"Created Qdrant collection: {QDRANT_COLLECTION}")


def index_docs():
    from qdrant_client.models import PointStruct

    if not GITHUB_REPO:
        logger.warning("GITHUB_REPO not set — skipping doc indexing")
        return

    logger.info("Indexing docs from GitHub...")
    docs = fetch_github_docs()
    if not docs:
        logger.warning("No docs fetched")
        return

    all_chunks = []
    for doc in docs:
        all_chunks.extend(chunk_text(doc["text"], doc["source"]))

    logger.info(f"Embedding {len(all_chunks)} chunks...")
    texts = [c["text"] for c in all_chunks]
    embeddings = embed_texts(texts)

    _ensure_collection(len(embeddings[0]))
    c = _client()
    points = [
        PointStruct(
            id=abs(hash(chunk["id"])) % (2 ** 63),
            vector=emb,
            payload={"source": chunk["source"], "text": chunk["text"]},
        )
        for chunk, emb in zip(all_chunks, embeddings)
    ]
    c.upsert(collection_name=QDRANT_COLLECTION, points=points)
    logger.info(f"Indexed {len(points)} chunks into Qdrant")


def retrieve(query: str, top_k: int = TOP_K) -> str:
    try:
        vec = embed_texts([query])[0]
        c = _client()
        results = c.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=vec,
            limit=top_k,
        )
        if not results:
            return ""
        chunks = [f"[{r.payload.get('source','')}]\n{r.payload.get('text','')}" for r in results]
        return "\n\n---\n\n".join(chunks)
    except Exception as e:
        logger.error(f"RAG retrieval error: {e}")
        return ""
