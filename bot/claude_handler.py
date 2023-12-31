"""
claude_handler.py

Calls Claude API with full context: chain data, wandb miner data,
RAG doc chunks, manual Q&A matches, and reference links.
"""

from __future__ import annotations

import logging
import anthropic

from config.settings import ANTHROPIC_API_KEY, HAIKU_MODEL, SONNET_MODEL
from bot.router import route_query
from data.knowledge_store import get_links_block, find_matching_qa

logger = logging.getLogger(__name__)
_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_HAIKU = """You are a helpful assistant for a Bittensor subnet. Answer clearly and accurately.

Rules:
- Answer only from the data sections provided below (CHAIN DATA, MINER DATA, Q&A, DOCS, LINKS).
- If the answer isn't in the provided data, say "I don't have that information right now."
- Keep answers concise and friendly.
- Never fabricate numbers, UIDs, scores, or prices.
- When mentioning links, use exact URLs from the REFERENCE LINKS section only.
"""

SYSTEM_SONNET = """You are an enthusiastic and knowledgeable assistant for a Bittensor subnet. Be creative, engaging, and inspiring when discussing vision, opportunities, and ideas.

Rules:
- Ground your answer in the provided data sections below.
- You can be expressive and elaborate, but never fabricate specific stats or numbers.
- Speak honestly if something isn't in the data.
- When mentioning links, use exact URLs from the REFERENCE LINKS section only.
"""


def _build_prompt(query, chain_data, wandb_data, rag_context, qa_context, links_block) -> str:
    parts = []
    if chain_data:   parts.append(f"CHAIN DATA:\n{chain_data}")
    if wandb_data:   parts.append(f"MINER DATA (wandb):\n{wandb_data}")
    if qa_context:   parts.append(f"REFERENCE Q&A:\n{qa_context}")
    if rag_context:  parts.append(f"DOCS CONTEXT:\n{rag_context}")
    if links_block:  parts.append(f"REFERENCE LINKS:\n{links_block}")
    parts.append(f"USER QUESTION:\n{query}")
    return "\n\n---\n\n".join(parts)


async def ask_claude(
    query: str,
    chain_data: str = "",
    wandb_data: str = "",
    rag_context: str = "",
) -> str:
    model_key = route_query(query)
    model  = SONNET_MODEL if model_key == "sonnet" else HAIKU_MODEL
    system = SYSTEM_SONNET if model_key == "sonnet" else SYSTEM_HAIKU

    qa_context  = find_matching_qa(query)
    links_block = get_links_block()

    prompt = _build_prompt(query, chain_data, wandb_data, rag_context, qa_context, links_block)
    logger.info(f"[{model_key.upper()}] {query[:70]}...")

    try:
        response = _client.messages.create(
            model=model,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return "Sorry, I ran into an issue. Please try again in a moment."
