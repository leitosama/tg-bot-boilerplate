"""Unit tests for the storage layer."""

from __future__ import annotations

import pytest

from storage import SqliteStorage, user_hash


@pytest.fixture
async def storage() -> SqliteStorage:
    store = SqliteStorage(":memory:")
    await store.ensure_schema()
    return store


async def test_sqlite_roundtrip(storage: SqliteStorage) -> None:
    uh = user_hash(1)
    assert await storage.increment(uh) == 1
    assert await storage.increment(uh) == 2
    assert await storage.increment(uh) == 3
    assert await storage.get_count(uh) == 3


async def test_get_count_unknown_user(storage: SqliteStorage) -> None:
    assert await storage.get_count(user_hash(999)) == 0


async def test_counts_are_per_user(storage: SqliteStorage) -> None:
    a, b = user_hash(1), user_hash(2)
    await storage.increment(a)
    await storage.increment(a)
    await storage.increment(b)
    assert await storage.get_count(a) == 2
    assert await storage.get_count(b) == 1


def test_user_hash_is_deterministic() -> None:
    assert user_hash(42) == user_hash(42)


def test_user_hash_differs_per_user() -> None:
    assert user_hash(1) != user_hash(2)


def test_user_hash_format() -> None:
    digest = user_hash(123)
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)
