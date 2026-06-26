"""Integration tests for the Cloudflare Worker webhook entry point.

All external seams (``workers`` module, D1 binding, aiohttp, Telegram API)
are replaced with mocks so no real network calls or Pyodide runtime is needed.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

# conftest.py installs the fake ``workers`` module before this import.
from worker import Default

# ---------------------------------------------------------------------------
# Minimal Telegram Update payload (message from user 42 in chat 42)
# ---------------------------------------------------------------------------
_UPDATE: dict[object, object] = {
    "update_id": 1,
    "message": {
        "message_id": 1,
        "date": 0,
        "chat": {"id": 42, "type": "private"},
        "from": {"id": 42, "is_bot": False, "first_name": "T"},
        "text": "hello",
    },
}
_UPDATE_JSON = json.dumps(_UPDATE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeRequest:
    def __init__(self, method: str, body: str) -> None:
        self.method = method
        self._body = body

    async def text(self) -> str:
        return self._body


def _build_d1_mock(count: int = 0) -> MagicMock:
    """Return a mock that mimics the D1 binding fluent API."""
    row = SimpleNamespace(count=count)

    run_mock = AsyncMock()
    first_mock = AsyncMock(return_value=row)

    # prepare("DDL").run()  — for ensure_schema
    # prepare("SELECT ...").bind(uh).first()  — for get_count
    # prepare("INSERT ...").bind(uh, n).run()  — for increment
    bound = MagicMock()
    bound.first = first_mock
    bound.run = run_mock

    stmt = MagicMock()
    stmt.bind = MagicMock(return_value=bound)
    stmt.run = run_mock  # prepare(...).run() used by ensure_schema

    db = MagicMock()
    db.prepare = MagicMock(return_value=stmt)
    return db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_post_increments_and_returns_ok() -> None:
    db = _build_d1_mock(count=3)
    env = SimpleNamespace(DB=db, BOT_TOKEN="123:TEST")

    with patch("telebot.async_telebot.AsyncTeleBot.reply_to", new_callable=AsyncMock):
        resp = await Default(env).fetch(FakeRequest("POST", _UPDATE_JSON))

    assert resp.body == "ok"
    # D1 was queried (ensure_schema + at least one SELECT)
    assert db.prepare.call_count >= 2


async def test_post_unknown_update_returns_ok() -> None:
    """A body that de_json can't parse as a known Update should not crash."""
    db = _build_d1_mock()
    env = SimpleNamespace(DB=db, BOT_TOKEN="123:TEST")

    # Update with no message — process_new_updates handles it gracefully
    empty = json.dumps({"update_id": 2})
    resp = await Default(env).fetch(FakeRequest("POST", empty))
    assert resp.body == "ok"


async def test_get_calls_setwebhook() -> None:
    env = SimpleNamespace(DB=None, BOT_TOKEN="123:TEST", WORKER_URL="https://w.example.com")

    fake_resp = AsyncMock()
    fake_resp.text = AsyncMock(return_value='{"ok":true}')

    fake_session = MagicMock()
    fake_session.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session.__aexit__ = AsyncMock(return_value=False)
    fake_session.post = AsyncMock(return_value=fake_resp)

    with patch("aiohttp.ClientSession", return_value=fake_session):
        resp = await Default(env).fetch(FakeRequest("GET", ""))

    assert "ok" in resp.body
    fake_session.post.assert_awaited_once()
    call_args = fake_session.post.await_args
    assert "setWebhook" in call_args.args[0]
    assert call_args.kwargs["json"]["url"] == "https://w.example.com"
