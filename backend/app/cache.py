"""Caching, shared-list storage, device records and rate limiting — all on Redis.

Redis is **mandatory** (not an optional optimization): shareable-link UUIDs, the
pseudo-anonymous device records and the daily rate limit are all first-class Redis
data. The app fails fast at startup if Redis is unreachable (see ``main.lifespan``),
so the rest of the code can assume a live connection.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Saved search lists (for shareable links) live for 30 days, refreshed on access.
SEARCH_LIST_TTL = 60 * 60 * 24 * 30
# Device records (pseudo-anonymous identity) live for 90 idle days, refreshed on
# access. No portability by design: lose the device, lose the server-side data.
DEVICE_TTL = 60 * 60 * 24 * 90


class Cache:
    def __init__(
        self, redis_url: str = "", default_ttl: int = 21600, *, client: Any = None
    ) -> None:
        self._default_ttl = default_ttl
        if client is not None:
            self._redis = client
        else:
            if not redis_url:
                raise RuntimeError(
                    "REDIS_URL is required — Redis is a mandatory dependency."
                )
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(redis_url, decode_responses=True)
        logger.info("Cache backend: Redis")

    @property
    def backend_name(self) -> str:
        return "redis"

    @property
    def redis(self) -> Any:
        """The live Redis client, shared with sibling services (e.g. Analytics)."""
        return self._redis

    async def ping(self) -> None:
        """Fail fast at startup if Redis is unreachable."""
        await self._redis.ping()

    # --- Generic JSON cache -------------------------------------------------

    async def get_json(self, key: str) -> Any | None:
        try:
            raw = await self._redis.get(key)
        except Exception:  # pragma: no cover
            logger.exception("cache get failed for %s", key)
            return None
        return json.loads(raw) if raw else None

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = ttl if ttl is not None else self._default_ttl
        try:
            await self._redis.set(key, json.dumps(value), ex=ttl)
        except Exception:  # pragma: no cover
            logger.exception("cache set failed for %s", key)

    async def incr_with_ttl(self, key: str, ttl: int) -> int:
        try:
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, ttl)
            return count
        except Exception:  # pragma: no cover
            logger.exception("rate-limit incr failed; allowing request")
            return 1

    async def _expire(self, key: str, ttl: int) -> None:
        try:
            await self._redis.expire(key, ttl)
        except Exception:  # pragma: no cover
            logger.exception("expire failed for %s", key)

    # --- Shareable shopping lists ------------------------------------------

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

    # --- Pseudo-anonymous device records (no login) ------------------------
    #
    # A device proves identity with an opaque high-entropy bearer token it
    # generated and keeps in secure storage. We store only what server-side
    # features need: the LGPD consent record and the set of saved-list UUIDs.

    @staticmethod
    def _decode(value: Any) -> Any:
        # Real Redis (decode_responses=True) yields str; some clients yield bytes.
        return value.decode() if isinstance(value, bytes) else value

    @staticmethod
    def _device_key(token: str) -> str:
        return f"device:{token}"

    @staticmethod
    def _device_lists_key(token: str) -> str:
        return f"device:{token}:lists"

    async def register_consent(self, token: str, policy_version: str) -> None:
        """Record (or refresh) the device's LGPD consent — the legal basis for
        storing its data server-side."""
        key = self._device_key(token)
        await self._redis.hset(
            key,
            mapping={
                "consent_at": datetime.now(timezone.utc).isoformat(),
                "policy_version": policy_version,
            },
        )
        await self._expire(key, DEVICE_TTL)

    async def get_device(self, token: str) -> dict[str, Any] | None:
        """Return the device record (consent + saved lists), or None if unknown.
        Refreshes the idle TTL on access."""
        key = self._device_key(token)
        record = await self._redis.hgetall(key)
        if not record:
            return None
        record = {self._decode(k): self._decode(v) for k, v in record.items()}
        lists_key = self._device_lists_key(token)
        saved = await self._redis.smembers(lists_key)
        await self._expire(key, DEVICE_TTL)
        await self._expire(lists_key, DEVICE_TTL)
        return {
            "consent_at": record.get("consent_at"),
            "policy_version": record.get("policy_version"),
            "saved_lists": sorted(self._decode(s) for s in saved),
        }

    async def attach_list(self, token: str, list_id: str) -> None:
        """Associate a shareable-list UUID with a device — only if the device has
        consented (an unknown/un-consented token stores nothing)."""
        key = self._device_key(token)
        if not await self._redis.exists(key):
            return
        lists_key = self._device_lists_key(token)
        await self._redis.sadd(lists_key, list_id)
        await self._expire(key, DEVICE_TTL)
        await self._expire(lists_key, DEVICE_TTL)

    async def delete_device(self, token: str) -> bool:
        """LGPD erasure: wipe all server-side data for a device. Returns whether
        anything existed. The shared list contents themselves are not deleted —
        they may be shared with others — only this device's association to them."""
        removed = await self._redis.delete(
            self._device_key(token), self._device_lists_key(token)
        )
        return bool(removed)

    async def aclose(self) -> None:
        try:  # pragma: no cover - connection teardown
            await self._redis.aclose()
        except Exception:
            pass
