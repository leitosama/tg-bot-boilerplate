# tg-bot-boilerplate

A Telegram bot boilerplate with two deployment targets:

- **Local** — Docker Compose + SQLite, **polling** mode (development & testing)
- **Production** — Cloudflare Workers + D1, **webhook** mode (free tier)

The bot is a simple per-user message counter. The same async handlers run in
both modes; only the entry point and storage backend differ. See
[`CLAUDE.md`](./CLAUDE.md) for the full architecture spec.

## Local quickstart (Docker Compose)

1. Copy the env template and add your bot token (from [@BotFather](https://t.me/BotFather)):

   ```bash
   cp .env.example .env
   # edit .env → set BOT_TOKEN
   ```

2. Start the bot:

   ```bash
   # pull prebuilt image from GHCR (default):
   docker compose up -d

   # or build the image locally:
   docker compose up -d --build
   ```

Logs: `docker compose logs -f`. The SQLite database is persisted in the
`bot-data` named volume at `/app/data/bot.db`.

## Cloudflare Workers deployment

### Prerequisites

- [Node.js](https://nodejs.org/) and [uv](https://docs.astral.sh/uv/) installed
- Cloudflare account (free tier)

### 1. Create the D1 database

```bash
npx wrangler d1 create tg_bot_counters
```

Copy the `database_id` from the output into `wrangler.toml`.

### 2. Set secrets

```bash
npx wrangler secret put BOT_TOKEN    # your Telegram bot token
npx wrangler secret put WORKER_URL   # https://<name>.<subdomain>.workers.dev
```

### 3. Deploy

```bash
uvx --from workers-py pywrangler deploy
```

### 4. Register the webhook (once)

```bash
curl https://<name>.<subdomain>.workers.dev/setup
```

## Development (without Docker)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

ruff check . && ruff format --check .
mypy --strict src/
pytest tests/

# run the poller against a real bot token:
BOT_TOKEN=123456:your-token DB_PATH=./bot.db python src/local.py
```

## CI/CD

- **Every push / PR**: lint (`ruff`), typecheck (`mypy --strict`), tests (`pytest`)
- **Push to `main`**: deploy to Cloudflare Workers + build multi-arch Docker image to GHCR

Required repository secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`.
