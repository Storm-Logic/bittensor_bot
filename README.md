# Bittensor Subnet Discord Bot

A Discord bot for your Bittensor subnet. Answers questions about live chain data, miner stats, subnet docs, and more.

## Architecture

```
User query
    │
    ├── Live data keywords → fetch chain / wandb → Haiku formats answer
    ├── UID query          → fetch specific UID  → Haiku formats answer
    ├── Creative/vision    → RAG + Sonnet answers engagingly
    └── Docs question      → RAG retrieval       → Haiku answers
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Qdrant (vector DB, free self-hosted)

```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 3. Configure environment

```bash
cp .env.example .env
# Fill in your keys in .env
```

### 4. Index your docs (first time)

```python
from rag.pipeline import index_docs
index_docs()
```

### 5. Run the bot

```bash
python -m bot.main
```

### 6. (Optional) Run webhook for auto doc updates

```bash
python webhook.py
```
Set up a GitHub webhook pointing to `http://your-server:8080/webhook`.

---

## Slash Commands

| Command | Description |
|---|---|
| `/uid <number>` | Get rank, score, stake for a specific UID |
| `/top` | Show top 10 miners |
| `/subnet` | Show live subnet stats |
| `/reindex` | [Admin] Re-index docs from GitHub |

## Mention / DM

Users can also @mention the bot or DM it with any question. The bot will:
- Inject live data if the question is about prices, miners, etc.
- Pull relevant doc chunks via RAG for setup/concept questions
- Use Haiku for factual answers, Sonnet for creative/vision questions

---

## Cost

~$5–9/month at 500 queries/day with the Haiku + 10% Sonnet split.
