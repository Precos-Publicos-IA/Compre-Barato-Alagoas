"""Caching and rate limiting.

Uses Redis when ``REDIS_URL`` is set, otherwise an in-process dict with TTLs so the app
runs with zero infrastructure during development. The interface is the small subset the
app actually needs: JSON get/set and an atomic-ish "increment with expiry" for the
daily rate limit.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# Saved search lists (for shareable links) live for 30 days, refreshed on access.
SEARCH_LIST_TTL = 60 * 60 * 24 * 30


class _MemoryBackend:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str]] = {}  # key -> (expire_ts, value)
        self._counters: dict[str, tuple[float, int]] = {}

    def _expired(self, expire_ts: float) -> bool:
        return expire_ts > 0 and expire_ts < time.time()

    async def get(self, key: str) -> str | None:
        item = self._store.get(key)
        if item is None:
            return None
        expire_ts, value = item
        if self._expired(expire_ts):
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str, ttl: int) -> None:
        self._store[key] = (time.time() + ttl if ttl else 0, value)

    async def incr_with_ttl(self, key: str, ttl: int) -> int:
        now = time.time()
        item = self._counters.get(key)
        if item is None or (item[0] and item[0] < now):
            self._counters[key] = (now + ttl, 1)
            return 1
        expire_ts, count = item
        count += 1
        self._counters[key] = (expire_ts, count)
        return count

    async def expire(self, key: str, ttl: int) -> bool:
        item = self._store.get(key)
        if item is None:
            return False
        _, value = item
        self._store[key] = (time.time() + ttl if ttl else 0, value)
        return True

    async def aclose(self) -> None:
        return None


class Cache:
    def __init__(self, redis_url: str = "", default_ttl: int = 21600) -> None:
        self._default_ttl = default_ttl
        self._redis = None
        self._memory = _MemoryBackend()
        if redis_url:
            try:
                import redis.asyncio as aioredis

                self._redis = aioredis.from_url(redis_url, decode_responses=True)
                logger.info("Cache backend: Redis")
            except Exception:  # pragma: no cover - falls back gracefully
                logger.exception("Redis init failed; using in-memory cache")
        else:
            logger.info("Cache backend: in-memory")

    @property
    def backend_name(self) -> str:
        return "redis" if self._redis is not None else "memory"

    async def get_json(self, key: str) -> Any | None:
        try:
            raw = (
                await self._redis.get(key)
                if self._redis is not None
                else await self._memory.get(key)
            )
        except Exception:  # pragma: no cover
            logger.exception("cache get failed for %s", key)
            return None
        return json.loads(raw) if raw else None

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = ttl if ttl is not None else self._default_ttl
        raw = json.dumps(value)
        try:
            if self._redis is not None:
                await self._redis.set(key, raw, ex=ttl)
            else:
                await self._memory.set(key, raw, ttl)
        except Exception:  # pragma: no cover
            logger.exception("cache set failed for %s", key)

    async def incr_with_ttl(self, key: str, ttl: int) -> int:
        if self._redis is not None:
            try:
                count = await self._redis.incr(key)
                if count == 1:
                    await self._redis.expire(key, ttl)
                return count
            except Exception:  # pragma: no cover
                logger.exception("rate-limit incr failed; allowing request")
                return 1
        return await self._memory.incr_with_ttl(key, ttl)

    async def _expire(self, key: str, ttl: int) -> None:
        try:
            if self._redis is not None:
                await self._redis.expire(key, ttl)
            else:
                await self._memory.expire(key, ttl)
        except Exception:  # pragma: no cover
            logger.exception("expire failed for %s", key)

    async def save_search_list(
        self, items: list[str], ttl: int = SEARCH_LIST_TTL
    ) -> str | None:
        """Store a shopping list under a UUID for shareable links.

        Identical lists (same items, case-insensitive, same order) reuse the same
        UUID. Any access refreshes the 30-day TTL; after 30 idle days it expires
        and the link becomes invalid.
        """
        norm = [s.strip() for s in items if s and s.strip()]
        if not norm:
            return None
        digest = hashlib.sha256(
            "|".join(s.lower() for s in norm).encode()
        ).hexdigest()
        hash_key = f"listhash:{digest}"
        try:
            existing = await self.get_json(hash_key)
            if isinstance(existing, str):
                await self._expire(f"list:{existing}", ttl)
                await self._expire(hash_key, ttl)
                return existing
            new_id = uuid.uuid4().hex
            await self.set_json(f"list:{new_id}", {"items": norm}, ttl=ttl)
            await self.set_json(hash_key, new_id, ttl=ttl)
            return new_id
        except Exception:  # pragma: no cover
            logger.exception("save_search_list failed")
            return None

    async def get_search_list(
        self, list_id: str, ttl: int = SEARCH_LIST_TTL
    ) -> list[str] | None:
        """Resolve a shareable list UUID back to its items, refreshing the TTL."""
        data = await self.get_json(f"list:{list_id}")
        if not isinstance(data, dict):
            return None
        await self._expire(f"list:{list_id}", ttl)
        items = data.get("items")
        return items if isinstance(items, list) else None

    async def aclose(self) -> None:
        if self._redis is not None:  # pragma: no cover
            await self._redis.aclose()
