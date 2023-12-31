import os
from dotenv import load_dotenv

load_dotenv()

# ── Discord ───────────────────────────────────────────────────────────────────
DISCORD_TOKEN      = os.getenv("DISCORD_TOKEN")
ALLOWED_CHANNEL_IDS = (
    list(map(int, os.getenv("ALLOWED_CHANNEL_IDS", "").split(",")))
    if os.getenv("ALLOWED_CHANNEL_IDS") else []
)

# ── Anthropic ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
HAIKU_MODEL       = "claude-haiku-4-5-20251001"
SONNET_MODEL      = "claude-sonnet-4-6"

# ── Bittensor ─────────────────────────────────────────────────────────────────
NETUID             = int(os.getenv("NETUID", "1"))
SUBTENSOR_NETWORK  = os.getenv("SUBTENSOR_NETWORK", "finney")
CACHE_TTL_PRICE    = 60
CACHE_TTL_MINERS   = 300

# ── wandb (no run IDs — auto-discovered) ─────────────────────────────────────
WANDB_API_KEY       = os.getenv("WANDB_API_KEY")
WANDB_ENTITY        = os.getenv("WANDB_ENTITY", "")
WANDB_PROJECT       = os.getenv("WANDB_PROJECT", "")
WANDB_POLL_INTERVAL = int(os.getenv("WANDB_POLL_INTERVAL", "300"))   # seconds
WANDB_TARGET_RECORDS = int(os.getenv("WANDB_TARGET_RECORDS", "100")) # stop fetching runs after this many records
WANDB_MAX_RUNS       = int(os.getenv("WANDB_MAX_RUNS", "10"))        # hard cap per cycle

# ── GitHub docs ───────────────────────────────────────────────────────────────
GITHUB_REPO   = os.getenv("GITHUB_REPO", "")
GITHUB_TOKEN  = os.getenv("GITHUB_TOKEN", "")
DOCS_PATHS    = [p.strip() for p in os.getenv("DOCS_PATHS", "README.md").split(",") if p.strip()]

# ── Qdrant ────────────────────────────────────────────────────────────────────
QDRANT_HOST       = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT       = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "subnet_docs")

# ── OpenAI (embeddings only) ──────────────────────────────────────────────────
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"

# ── Admin UI ──────────────────────────────────────────────────────────────────
ADMIN_UI_TOKEN = os.getenv("ADMIN_UI_TOKEN", "changeme")
ADMIN_PORT     = int(os.getenv("ADMIN_PORT", "8888"))
