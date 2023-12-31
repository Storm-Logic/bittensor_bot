"""
knowledge_store.py

Persists reference links and manual Q&A pairs as JSON files.
The admin web UI reads/writes via the FastAPI server.
The bot reads from these on every query.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent
LINKS_FILE = DATA_DIR / "reference_links.json"
QA_FILE    = DATA_DIR / "manual_qa.json"

_lock = threading.RLock()


def _load(path: Path) -> list:
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Load failed {path}: {e}")
    return []

def _save(path: Path, data: list):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def _id() -> str:
    return uuid.uuid4().hex[:8]


# ── Reference links ───────────────────────────────────────────────────────────

def get_links() -> List[dict]:
    with _lock:
        return _load(LINKS_FILE)

def add_link(label: str, url: str, description: str = "") -> dict:
    with _lock:
        links = _load(LINKS_FILE)
        entry = {"id": _id(), "label": label, "url": url,
                 "description": description, "added": datetime.utcnow().isoformat()}
        links.append(entry)
        _save(LINKS_FILE, links)
        return entry

def update_link(link_id: str, label=None, url=None, description=None) -> Optional[dict]:
    with _lock:
        links = _load(LINKS_FILE)
        for l in links:
            if l["id"] == link_id:
                if label is not None: l["label"] = label
                if url is not None: l["url"] = url
                if description is not None: l["description"] = description
                _save(LINKS_FILE, links)
                return l
        return None

def remove_link(link_id: str) -> bool:
    with _lock:
        links = _load(LINKS_FILE)
        new = [l for l in links if l["id"] != link_id]
        if len(new) == len(links): return False
        _save(LINKS_FILE, new)
        return True


# ── Manual Q&A ────────────────────────────────────────────────────────────────

def get_qa_pairs() -> List[dict]:
    with _lock:
        return _load(QA_FILE)

def add_qa(question: str, answer: str, tags: List[str] = None) -> dict:
    with _lock:
        pairs = _load(QA_FILE)
        entry = {"id": _id(), "question": question, "answer": answer,
                 "tags": tags or [], "added": datetime.utcnow().isoformat()}
        pairs.append(entry)
        _save(QA_FILE, pairs)
        return entry

def update_qa(qa_id: str, question=None, answer=None, tags=None) -> Optional[dict]:
    with _lock:
        pairs = _load(QA_FILE)
        for p in pairs:
            if p["id"] == qa_id:
                if question is not None: p["question"] = question
                if answer is not None:   p["answer"] = answer
                if tags is not None:     p["tags"] = tags
                _save(QA_FILE, pairs)
                return p
        return None

def remove_qa(qa_id: str) -> bool:
    with _lock:
        pairs = _load(QA_FILE)
        new = [p for p in pairs if p["id"] != qa_id]
        if len(new) == len(pairs): return False
        _save(QA_FILE, new)
        return True


# ── Bot-facing helpers ────────────────────────────────────────────────────────

def get_links_block() -> str:
    links = get_links()
    if not links:
        return ""
    lines = ["Reference links:"]
    for l in links:
        desc = f" — {l['description']}" if l.get("description") else ""
        lines.append(f"  {l['label']}: {l['url']}{desc}")
    return "\n".join(lines)


def find_matching_qa(query: str, top_k: int = 3) -> str:
    """Keyword overlap match — no embeddings needed for small Q&A sets."""
    pairs = get_qa_pairs()
    if not pairs:
        return ""
    q_words = set(query.lower().split())
    scored = []
    for p in pairs:
        overlap = len(set(p["question"].lower().split()) & q_words)
        if overlap > 0:
            scored.append((overlap, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return ""
    lines = ["Manual Q&A context:"]
    for _, p in scored[:top_k]:
        lines.append(f"Q: {p['question']}")
        lines.append(f"A: {p['answer']}")
        lines.append("")
    return "\n".join(lines).strip()
