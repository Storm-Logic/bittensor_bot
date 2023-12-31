"""
router.py — decides which model to use based on query intent.
Haiku for factual/data lookups (~90%), Sonnet for creative/open-ended (~10%).
"""

CREATIVE_TRIGGERS = [
    "why should", "what makes", "tell me about", "what's exciting",
    "convince me", "unique", "vision", "future", "roadmap",
    "what do you think", "describe", "explain the idea", "what is the goal",
    "potential", "opportunity", "worth joining", "interesting",
    "innovative", "how does this compare", "what sets",
]

def route_query(query: str) -> str:
    """Returns 'sonnet' for creative queries, 'haiku' for everything else."""
    lowered = query.lower()
    if any(t in lowered for t in CREATIVE_TRIGGERS):
        print(9999)
        return "sonnet"
    return "haiku"
