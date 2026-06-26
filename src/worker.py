"""Webhook entry point for the Cloudflare Workers deployment."""

from __future__ import annotations

import json
import logging

import aiohttp
from telebot.types import Update
from workers import Response, WorkerEntrypoint

from bot import make_bot
from storage import D1Storage

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org"


class _Request:
    method: str

    async def text(self) -> str:
        return ""


class Default(WorkerEntrypoint):
    async def fetch(self, request: _Request) -> Response:
        if request.method == "GET":
            return await self._handle_setup()

        body: str = await request.text()
        update = Update.de_json(json.loads(body))  # type: ignore[no-untyped-call]
        if update is None:
            return Response("ok")

        storage = D1Storage(self.env.DB)
        await storage.ensure_schema()
        bot = make_bot(self.env.BOT_TOKEN, storage)
        await bot.process_new_updates([update])
        return Response("ok")

    async def _handle_setup(self) -> Response:
        token: str = self.env.BOT_TOKEN
        worker_url: str = self.env.WORKER_URL
        async with aiohttp.ClientSession() as session:
            resp = await session.post(
                f"{_TELEGRAM_API}/bot{token}/setWebhook",
                json={"url": worker_url},
            )
            return Response(await resp.text())
