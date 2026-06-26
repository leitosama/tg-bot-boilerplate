# tg-bot-boilerplate — Architecture Spec

## Overview
Telegram bot boilerplate with two deployment targets:
- **Local**: Docker Compose + SQLite (for development and testing)
- **Production**: Cloudflare Workers + D1 (free tier)

## Stack
- Python 3.12+ (Cloudflare Workers Python via Pyodide, open beta)
- pyTelegramBotAPI (telebot)
- python-dotenv
- Standard logging module
- Type hints everywhere — mypy strict mode is mandatory

## Bot Logic
Simple counter table with two columns:
- `user_hash` — SHA-256 of Telegram user ID (TEXT, primary key)
- `count` — message count per user (INTEGER)

## Deployment Modes

### Local (Docker Compose)
- SQLite for persistence, DB file `bot.db` in named volume at `/app/data/`
- Settings via `.env` + python-dotenv, including `BOT_TOKEN`
- Logs → stdout → `docker compose logs`
- Bot runs in **polling** mode: `bot.infinity_polling()`
- `docker-compose.yml`: default policy is `image: ghcr.io/...` (pull);
  build profile available via `--profile build` for local development

### Cloudflare Workers + D1
- **D1** (SQLite-compatible) as persistent storage — free tier
- Python Worker via Pyodide runtime (`python_workers` compatibility flag)
- Bot runs in **webhook** mode:
  - Worker's `fetch` handler receives POST from Telegram
  - Deserialize: `telebot.types.Update.de_json(body)`
  - Dispatch: `bot.process_new_updates([update])`
  - Bot instantiated with `threaded=False` (no thread pool in Workers)
- Secrets via `wrangler secret put BOT_TOKEN`
- Config in `wrangler.toml` with D1 binding
- Webhook registration: one-time via `/setup` endpoint or `wrangler` CLI call
- Toolchain: `pywrangler` CLI, dependencies in `pyproject.toml`

## Architecture: Polling vs Webhook

The same bot logic (handlers, decorators) is used in both modes.
Entry point differs:

```python
# local.py — polling entry point
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
# ... register handlers ...
bot.infinity_polling()

# worker.py — webhook entry point (Cloudflare Worker)
from workers import WorkerEntrypoint, Response

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
# ... same handlers registered ...

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        body = await request.text()
        update = telebot.types.Update.de_json(body)
        bot.process_new_updates([update])
        return Response("ok")
```

## Architecture: Storage Abstraction

Abstract DB access behind a `Storage` interface with two implementations:

```python
class Storage(Protocol):
    def get_count(self, user_hash: str) -> int: ...
    def increment(self, user_hash: str) -> int: ...

class SqliteStorage(Storage):   # local Docker
    ...

class D1Storage(Storage):       # Cloudflare D1
    ...
```

Runtime selection: check for `env.DB` binding (D1) vs `DB_PATH` env var (SQLite).

## Project Structure
```
/
├── src/
│   ├── bot.py          # handlers, runtime-agnostic
│   ├── storage.py      # Storage protocol + SqliteStorage + D1Storage
│   ├── local.py        # entry point: polling (Docker)
│   └── worker.py       # entry point: webhook (Cloudflare Worker)
├── tests/
│   ├── unit/           # bot logic, storage, handlers — no runtime needed
│   └── integration/    # webhook entry point with mocked Workers env
├── pyproject.toml      # dependencies, ruff + mypy config, pywrangler
├── wrangler.toml       # Cloudflare config, D1 binding
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── CLAUDE.md
```

## Code Quality
- **ruff** — linter and formatter, configured in `pyproject.toml`
- **mypy** — strict mode (`--strict`), configured in `pyproject.toml`
- **pytest** — unit and integration tests, mocking Workers environment
  - Unit tests: bot logic, handlers, storage implementations
  - Integration tests: webhook entry point with mocked `WorkerEntrypoint` and `env.DB`
  - No real `workerd` or Telegram API calls in tests
- pre-commit hooks (ruff + mypy): setup instructions in `CONTRIBUTING.md`,
  not enforced by default

## CI/CD (GitHub Actions)

Two separate workflows:

**On every push and PR** (all branches):
lint:      ruff check + ruff format --check
typecheck: mypy --strict src/
test:      pytest tests/

**On push/merge to `main` only:**
deploy:
pywrangler deploy → Cloudflare Workers
docker buildx build --platform linux/amd64,linux/arm64 → ghcr.io/<owner>/<repo>:latest

- Deploy runs only if lint + typecheck + test all pass
- Secrets required: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `GITHUB_TOKEN` (built-in)
- Claude Code works in `claude/*` branches, PRs into `main`

## README
- "Deploy to Cloudflare" button for one-click infra provisioning (D1 + Worker)
- Local quickstart (Docker Compose, `.env.example`)

## Constraints
- Cloudflare free tier only — no paid features
- D1 free limits: 5M reads/day, 100k writes/day, 5GB — sufficient
- Python Workers are open beta — use `python_workers` compatibility flag
- `threaded=False` on TeleBot is mandatory for Workers runtime
- No staging environment — `main` is production
- No release versioning — working code ships directly to `main`

## Docs for LLMs
- [Cloudflare Workers](https://developers.cloudflare.com/workers/llms-full.txt)
