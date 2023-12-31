"""
fetcher.py

Fetches live data from the Bittensor chain.
All results are cached to avoid hammering the subtensor RPC on every query.
"""

from __future__ import annotations

import time
import logging
from datetime import datetime
from typing import Optional

from config.settings import (
    NETUID, SUBTENSOR_NETWORK,
    CACHE_TTL_PRICE, CACHE_TTL_MINERS,
)

logger = logging.getLogger(__name__)

_cache: dict = {}

def _get(key: str, ttl: int):
    entry = _cache.get(key)
    if entry and (time.time() - entry[1]) < ttl:
        return entry[0]
    return None

def _set(key: str, value):
    _cache[key] = (value, time.time())


def get_subnet_info() -> dict:
    cached = _get("subnet_info", CACHE_TTL_PRICE)
    if cached:
        return cached
    try:
        import bittensor as bt
        sub = bt.Subtensor(network=SUBTENSOR_NETWORK)
        meta = sub.metagraph(NETUID)
        subnet = sub.get_subnet_info(NETUID)
        n_neurons = int(meta.n.item()) if hasattr(meta.n, "item") else int(meta.n)
        data = {
            "netuid": NETUID,
            "name": getattr(subnet, "subnet_name", f"Subnet {NETUID}"),
            "n_neurons": n_neurons,
            "total_stake": round(float(meta.S.sum()), 4),
            "tempo": getattr(subnet, "tempo", "N/A"),
            "emission": float(getattr(subnet, "emission_value", 0)),
        }
        try:
            data["alpha_price"] = str(sub.get_subnet_price(NETUID))
        except Exception:
            data["alpha_price"] = "N/A"
        _set("subnet_info", data)
        return data
    except Exception as e:
        logger.error(f"Chain subnet fetch error: {e}")
        return {"error": str(e)}


def get_uid_info(uid: int) -> dict:
    key = f"uid_{uid}"
    cached = _get(key, CACHE_TTL_MINERS)
    if cached:
        return cached
    try:
        import bittensor as bt
        sub = bt.Subtensor(network=SUBTENSOR_NETWORK)
        meta = sub.metagraph(NETUID)
        n_neurons = int(meta.n.item()) if hasattr(meta.n, "item") else int(meta.n)
        if uid >= n_neurons:
            return {"error": f"UID {uid} does not exist on subnet {NETUID}"}
        incentives = meta.I.tolist()
        ranked = sorted(enumerate(incentives), key=lambda x: x[1], reverse=True)
        rank_map = {u: r + 1 for r, (u, _) in enumerate(ranked)}
        result = {
            "uid": uid,
            "chain_rank": rank_map.get(uid, "N/A"),
            "chain_score": round(float(meta.I[uid]), 6),
            "stake": round(float(meta.S[uid]), 4),
            "trust": round(float(meta.T[uid]), 4),
            "hotkey": meta.hotkeys[uid][:12] + "...",
        }
        _set(key, result)
        return result
    except Exception as e:
        logger.error(f"Chain UID fetch error: {e}")
        return {"error": str(e)}


def build_live_data_block() -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    info = get_subnet_info()
    lines = [f"[Chain data as of {now}]"]
    if "error" not in info:
        lines.append(f"Subnet: {info.get('name')} (netuid {info.get('netuid')})")
        lines.append(f"Alpha price: {info.get('alpha_price')}")
        lines.append(f"Total neurons: {info.get('n_neurons')}")
        lines.append(f"Total stake: {info.get('total_stake')} TAO")
        lines.append(f"Tempo: {info.get('tempo')}")
    else:
        lines.append(f"Chain unavailable: {info['error']}")
    return "\n".join(lines)
