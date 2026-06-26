"""Unit tests for the runtime-agnostic handler logic."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from bot import make_bot
from storage import user_hash


class FakeStorage:
    """In-memory Storage implementation for tests."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    async def get_count(self, uh: str) -> int:
        return self.counts.get(uh, 0)

    async def increment(self, uh: str) -> int:
        self.counts[uh] = self.counts.get(uh, 0) + 1
        return self.counts[uh]


def make_message(user_id: int, text: str = "hi") -> Message:
    return Message.de_json(
        {
            "message_id": 1,
            "date": 0,
            "chat": {"id": user_id, "type": "private"},
            "from": {"id": user_id, "is_bot": False, "first_name": "T"},
            "text": text,
        }
    )


def get_handler(bot: AsyncTeleBot):  # type: ignore[no-untyped-def]
    return bot.message_handlers[0]["function"]


@pytest.fixture
def storage() -> FakeStorage:
    return FakeStorage()


async def test_handler_increments_and_replies(storage: FakeStorage) -> None:
    bot = make_bot("123:TEST", storage)
    bot.reply_to = AsyncMock()  # type: ignore[method-assign]
    handler = get_handler(bot)

    message = make_message(user_id=7)
    await handler(message)

    assert await storage.get_count(user_hash(7)) == 1
    bot.reply_to.assert_awaited_once()
    _, text = bot.reply_to.await_args.args
    assert text == "Your message count: 1"


async def test_handler_counts_grow_per_user(storage: FakeStorage) -> None:
    bot = make_bot("123:TEST", storage)
    bot.reply_to = AsyncMock()  # type: ignore[method-assign]
    handler = get_handler(bot)

    await handler(make_message(user_id=7))
    await handler(make_message(user_id=7))

    assert bot.reply_to.await_args_list[0].args[1] == "Your message count: 1"
    assert bot.reply_to.await_args_list[1].args[1] == "Your message count: 2"
