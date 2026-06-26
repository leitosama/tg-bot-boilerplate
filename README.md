# tg-bot-boilerplate

A Telegram bot boilerplate with two deployment targets:

- **Local** — Docker Compose + SQLite, **polling** mode (development & testing)
- **Production** — Cloudflare Workers + D1, **webhook** mode (free tier)

The bot is a simple per-user message counter. The same async handlers run in
both modes; only the entry point and storage backend differ. See
[`CLAUDE.md`](./CLAUDE.md) for the full architecture spec.

> **Status:** core (storage + bot logic + polling entry point + tests) is
> implemented. The Cloudflare Worker entry point, D1 wiring, and CI/CD are the
> next phase.

## Local quickstart (Docker Compose)

1. Create your env file and add your bot token (from [@BotFather](https://t.me/BotFather)):

   ```bash
   cp .env.example .env
   # edit .env → set BOT_TOKEN
   ```

2. Start the bot (pulls the prebuilt image):

   ```bash
   docker compose up
   ```

   To build the image locally instead of pulling:

   ```bash
   docker compose --profile build up bot-build
   ```

Logs go to stdout (`docker compose logs`). The SQLite database is persisted in
the `bot-data` named volume at `/app/data/bot.db`.

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
