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

# The device token is a bearer credential. We never store it raw: Redis keys use a
# salted SHA-256 of it (like a password hash), so a Redis dump exposes neither a
# usable token nor a link from a known token to its data. The client keeps sending
# the raw token; the server hashes it on every lookup. 256-bit tokens make this
# irreversible. Lookups are exact-match, so hashing is transparent to callers.
_DEVICE_KEY_SALT = "compre-barato-alagoas/device-key/v1"


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

            # Explicit connect/socket timeouts so a stalled Redis surfaces fast
            # instead of hanging a request indefinitely.
            self._redis = aioredis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=10,
            )
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
        if isinstance(items, list):
            # Also refresh the content-hash pointer so that identical-list dedup
            # continues to work even if only gets (share link opens) happen for a
            # while; prevents the hash key expiring while the list is still live.
            norm = [s.strip() for s in items if s and s.strip()]
            if norm:
                digest = hashlib.sha256(
                    "|".join(s.lower() for s in norm).encode()
                ).hexdigest()
                await self._expire(f"listhash:{digest}", ttl)
            return items
        return None

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
    def _device_hash(token: str) -> str:
        return hashlib.sha256((_DEVICE_KEY_SALT + token).encode()).hexdigest()

    @classmethod
    def _device_key(cls, token: str) -> str:
        return f"device:{cls._device_hash(token)}"

    @classmethod
    def _device_lists_key(cls, token: str) -> str:
        return f"device:{cls._device_hash(token)}:lists"

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
        # Must have an explicit consent record (presence of consent_at), not just
        # any key. Prevents attaching lists for devices that never opted in.
        if not await self._redis.hexists(key, "consent_at"):
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

    # --- Simple RAG / known mappings for agents (lightweight, no vector yet) ---
    # Records "user spoke X, effective SEFAZ search_term Y gave good matches".
    # Used by future Requester/Verifier to rewrite vague terms without extra SEFAZ calls.
    # Keys are cheap Redis hashes + zsets. TTL long for historical value.

    MAPPING_TTL = 60 * 60 * 24 * 180  # 180 days

    async def record_successful_mapping(
        self, user_term: str, effective_search_term: str, offers_found: int
    ) -> None:
        """Record that a user term mapped well to a SEFAZ term (for RAG in agents)."""
        if not user_term or not effective_search_term or offers_found < 1:
            return
        u = user_term.lower().strip()[:64]
        e = effective_search_term.lower().strip()[:64]
        try:
            pipe = self._redis.pipeline()
            # Hash of user_term -> best effective
            pipe.hset(f"rag:user_to_term:{u}", mapping={e: str(offers_found)})
            pipe.expire(f"rag:user_to_term:{u}", self.MAPPING_TTL)
            # Global top effective terms for a user_term stem (for suggestions)
            pipe.zincrby(f"rag:effective_for:{u}", offers_found, e)
            pipe.expire(f"rag:effective_for:{u}", self.MAPPING_TTL)
            await pipe.execute()
        except Exception:  # pragma: no cover
            logger.exception("record_successful_mapping failed")

    async def lookup_effective_terms(self, user_term: str, limit: int = 3) -> list[str]:
        """Return previously successful SEFAZ search_terms for this user term."""
        u = user_term.lower().strip()[:64]
        try:
            raw = await self._redis.zrevrange(f"rag:effective_for:{u}", 0, limit - 1)
            return [r.decode() if isinstance(r, bytes) else r for r in raw]
        except Exception:  # pragma: no cover
            return []

    async def get_best_effective_term(self, user_term: str) -> str | None:
        terms = await self.lookup_effective_terms(user_term, 1)
        return terms[0] if terms else None

    async def find_similar_effective_terms(
        self, user_term: str, limit: int = 3, min_overlap: int = 2
    ) -> list[str]:
        """Creative lightweight 'semantic' RAG without embeddings/deps.

        Uses simple token overlap on previously recorded effective terms.
        This helps vague user input like "pao" find "pao frances" or "pao de forma"
        from past successful searches, reducing bad SEFAZ calls at scale.
        Pure Python, very cheap, logarithmic benefit as more data is learned.
        """
        u = user_term.lower().strip()[:64]
        user_tokens = set(u.split())
        if not user_tokens:
            return []

        candidates: dict[str, int] = {}
        try:
            # Scan recent effective keys (we keep limited via the zsets)
            # For simplicity we scan a few known patterns from top items + direct keys.
            # In real use the zsets from record_ are the source of truth.
            keys = await self._redis.keys("rag:effective_for:*")
            for k in keys[:50]:  # bound the scan for safety
                try:
                    eterm = k.split(":", 2)[-1] if isinstance(k, str) else ""
                    if not eterm:
                        continue
                    et_tokens = set(eterm.lower().split())
                    overlap = len(user_tokens & et_tokens)
                    if overlap >= min_overlap:
                        score = await self._redis.zscore(f"rag:effective_for:{eterm}", eterm) or 1
                        candidates[eterm] = max(candidates.get(eterm, 0), overlap * int(score))
                except Exception:
                    continue
        except Exception:  # pragma: no cover
            pass

        ranked = sorted(candidates.items(), key=lambda x: -x[1])[:limit]
        return [t for t, _ in ranked]
