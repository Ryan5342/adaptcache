"""Cache storage backends for CacheAI.

Two backends ship in v0.1:
- MemoryBackend: pure-Python dict, zero dependencies. Default backend,
  good for a single process, development, and tests.
- RedisBackend: thin wrapper around redis-py (`pip install cacheai[redis]`).
"""

from __future__ import annotations

import time
from typing import Any, Optional


class MemoryBackend:
    """In-process dict backend. Not shared across processes/workers."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self._tags: dict[str, set] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at < time.time():
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._store[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()
        self._tags.clear()

    def tag_add(self, tag: str, key: str) -> None:
        self._tags.setdefault(tag, set()).add(key)

    def tag_members(self, tag: str) -> set:
        return set(self._tags.get(tag, ()))

    def tag_clear(self, tag: str) -> None:
        self._tags.pop(tag, None)


class RedisBackend:
    """Wraps redis-py. Values are JSON strings (serialized in core.py)."""

    def __init__(self, redis_url: str) -> None:
        try:
            import redis  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "RedisBackend requires redis-py. Install with: pip install cacheai[redis]"
            ) from exc
        self._client = redis.from_url(redis_url)

    def get(self, key: str) -> Optional[str]:
        value = self._client.get(key)
        return value.decode() if value is not None else None

    def set(self, key: str, value: str, ttl: int) -> None:
        self._client.set(key, value, ex=ttl)

    def delete(self, key: str) -> None:
        self._client.delete(key)

    def clear(self) -> None:
        # Deliberately not implemented: FLUSHDB is dangerous on a shared
        # Redis instance. Delete keys individually if you need this.
        raise NotImplementedError("clear() is not supported for RedisBackend")

    def tag_add(self, tag: str, key: str) -> None:
        self._client.sadd(f"cacheai:tagset:{tag}", key)

    def tag_members(self, tag: str) -> set:
        members = self._client.smembers(f"cacheai:tagset:{tag}")
        return {m.decode() if isinstance(m, bytes) else m for m in members}

    def tag_clear(self, tag: str) -> None:
        self._client.delete(f"cacheai:tagset:{tag}")
