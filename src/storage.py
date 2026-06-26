"""Storage abstraction for the message counter.

Defines a runtime-agnostic async ``Storage`` protocol with two implementations:

* :class:`SqliteStorage` -- standard library ``sqlite3``, used by the polling
  entry point running under Docker.
* :class:`D1Storage` -- Cloudflare D1 (async ``env.DB`` binding), used by the
  Cloudflare Worker webhook entry point.

Both back the same ``counters`` table so the schema can never drift.
"""

from __future__ import annotations

import hashlib
import sqlite3
from typing import Any, Protocol, runtime_checkable

# Shared DDL: identical schema for SQLite (local) and D1 (production).
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS counters (
    user_hash TEXT PRIMARY KEY,
    count     INTEGER NOT NULL DEFAULT 0
)
""".strip()

_UPSERT_SQL = (
    "INSERT INTO counters (user_hash, count) VALUES (?, ?) "
    "ON CONFLICT(user_hash) DO UPDATE SET count = excluded.count"
)

_SELECT_SQL = "SELECT count FROM counters WHERE user_hash = ?"


def user_hash(user_id: int) -> str:
    """Return the SHA-256 hex digest of a Telegram user id.

    Deterministic across restarts (no salt) so the same user always maps to the
    same primary key.
    """
    return hashlib.sha256(str(user_id).encode("utf-8")).hexdigest()


@runtime_checkable
class Storage(Protocol):
    """Async persistence interface for per-user message counts."""

    async def get_count(self, user_hash: str) -> int:
        """Return the current count for ``user_hash`` (0 if unseen)."""
        ...

    async def increment(self, user_hash: str) -> int:
        """Increment and return the new count for ``user_hash``."""
        ...


class SqliteStorage:
    """SQLite-backed storage for the local/polling deployment.

    The underlying ``sqlite3`` calls are synchronous; they are wrapped in async
    methods to satisfy the :class:`Storage` protocol. A single polling process
    has no real concurrency, so blocking the loop on these fast local reads is
    acceptable.
    """

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)

    async def ensure_schema(self) -> None:
        self._conn.execute(CREATE_TABLE_SQL)
        self._conn.commit()

    async def get_count(self, user_hash: str) -> int:
        row = self._conn.execute(_SELECT_SQL, (user_hash,)).fetchone()
        return int(row[0]) if row else 0

    async def increment(self, user_hash: str) -> int:
        new_count = await self.get_count(user_hash) + 1
        self._conn.execute(_UPSERT_SQL, (user_hash, new_count))
        self._conn.commit()
        return new_count


class D1Storage:
    """Cloudflare D1-backed storage for the Worker/webhook deployment.

    ``db`` is the D1 binding (``env.DB``); every operation is awaited. Query
    results come back as JS objects through Pyodide's FFI, so column access is
    done defensively (attribute access with a mapping fallback).
    """

    def __init__(self, db: Any) -> None:
        self._db = db

    async def ensure_schema(self) -> None:
        await self._db.prepare(CREATE_TABLE_SQL).run()

    async def get_count(self, user_hash: str) -> int:
        row = await self._db.prepare(_SELECT_SQL).bind(user_hash).first()
        if row is None:
            return 0
        return int(_read_count(row))

    async def increment(self, user_hash: str) -> int:
        new_count = await self.get_count(user_hash) + 1
        await self._db.prepare(_UPSERT_SQL).bind(user_hash, new_count).run()
        return new_count


def _read_count(row: Any) -> int:
    """Read the ``count`` column from a D1 result row (FFI-tolerant)."""
    try:
        return int(row.count)
    except (AttributeError, TypeError):
        return int(row["count"])
