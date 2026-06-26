"""Polling entry point for the local/Docker deployment."""

from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv

from bot import make_bot
from storage import SqliteStorage

logger = logging.getLogger(__name__)


async def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    token = os.environ["BOT_TOKEN"]
    db_path = os.environ.get("DB_PATH", "/app/data/bot.db")

    storage = SqliteStorage(db_path)
    await storage.ensure_schema()

    bot = make_bot(token, storage)
    logger.info("Starting polling (db_path=%s)", db_path)
    await bot.infinity_polling()


if __name__ == "__main__":
    asyncio.run(main())
