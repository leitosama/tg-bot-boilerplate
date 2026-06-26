"""Runtime-agnostic bot logic.

The same handlers are registered for both deployment targets (polling under
Docker and webhook on Cloudflare Workers). Only the entry point and the
:class:`~storage.Storage` implementation differ.
"""

from __future__ import annotations

from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from storage import Storage, user_hash


def register_handlers(bot: AsyncTeleBot, storage: Storage) -> None:
    """Register the message-counter handlers on ``bot``."""

    @bot.message_handler(func=lambda _message: True)  # type: ignore[no-untyped-call, untyped-decorator]
    async def count_handler(message: Message) -> None:
        if message.from_user is None:
            return
        new_count = await storage.increment(user_hash(message.from_user.id))
        await bot.reply_to(message, f"Your message count: {new_count}")


def make_bot(token: str, storage: Storage) -> AsyncTeleBot:
    """Build an :class:`AsyncTeleBot` with handlers wired to ``storage``."""
    bot = AsyncTeleBot(token)
    register_handlers(bot, storage)
    return bot
