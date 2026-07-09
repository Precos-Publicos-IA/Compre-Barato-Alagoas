"""Term-mapping knowledge store used by Requester and Verifier.

Wraps Redis so agents depend on a narrow interface (not the whole Cache).
Stores *metadata* about what users type and which SEFAZ search_terms worked —
never full price catalogs (SEFAZ remains source of truth).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9à-ú]+", re.I)


def _norm(term: str) -> str:
    return term.lower().strip()[:64]


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if len(t) >= 2}


@dataclass
class RAGStore:
    """Thin async facade over Redis keys owned by the search cache client."""

    redis: object  # redis.asyncio.Redis-like
    mapping_ttl: int = 60 * 60 * 24 * 180  # 180 days

    async def record_success(
        self, user_term: str, effective_search_term: str, offers_found: int
    ) -> None:
        """Record that ``user_term`` worked when searched as ``effective_search_term``."""
        if not user_term or not effective_search_term or offers_found < 1:
            return
        u, e = _norm(user_term), _norm(effective_search_term)
        try:
            pipe = self.redis.pipeline()
            pipe.hset(f"rag:user_to_term:{u}", mapping={e: str(offers_found)})
            pipe.expire(f"rag:user_to_term:{u}", self.mapping_ttl)
            pipe.zincrby(f"rag:effective_for:{u}", float(offers_found), e)
            pipe.expire(f"rag:effective_for:{u}", self.mapping_ttl)
            # Reverse index: effective term → user terms that hit it (for similar scan)
            pipe.sadd(f"rag:users_for_effective:{e}", u)
            pipe.expire(f"rag:users_for_effective:{e}", self.mapping_ttl)
            await pipe.execute()
        except Exception:  # pragma: no cover
            logger.exception("RAGStore.record_success failed")

    async def record_miss(self, user_term: str, attempted_search_term: str) -> None:
        """Remember a failed attempt (soft signal; does not block retries forever)."""
        if not user_term or not attempted_search_term:
            return
        u, e = _norm(user_term), _norm(attempted_search_term)
        try:
            key = f"rag:miss:{u}"
            await self.redis.zincrby(key, 1.0, e)
            await self.redis.expire(key, self.mapping_ttl)
        except Exception:  # pragma: no cover
            logger.exception("RAGStore.record_miss failed")

    async def lookup_effective_terms(self, user_term: str, limit: int = 3) -> list[str]:
        u = _norm(user_term)
        if not u:
            return []
        try:
            raw = await self.redis.zrevrange(f"rag:effective_for:{u}", 0, limit - 1)
            return [_decode(r) for r in raw]
        except Exception:  # pragma: no cover
            return []

    async def best_effective_term(self, user_term: str) -> str | None:
        terms = await self.lookup_effective_terms(user_term, 1)
        return terms[0] if terms else None

    async def find_similar_effective_terms(
        self, user_term: str, limit: int = 3, min_overlap: int = 1
    ) -> list[str]:
        """Token-overlap RAG without embeddings (cheap, good enough until scale).

        Scans a bounded set of known user-term keys and ranks by token overlap ×
        historical success score of their top effective terms.
        """
        u = _norm(user_term)
        user_tokens = _tokens(u)
        if not user_tokens:
            return []

        scores: dict[str, float] = {}
        try:
            keys = await self.redis.keys("rag:effective_for:*")
            # Bound scan — production Redis should use SCAN; keys() is OK at small N.
            for key in keys[:200]:
                key_s = _decode(key)
                # rag:effective_for:{user_term}
                other_user = key_s.split(":", 2)[-1] if key_s else ""
                if not other_user:
                    continue
                other_tokens = _tokens(other_user)
                overlap = len(user_tokens & other_tokens)
                # Also reward substring / stem-ish containment for "pao" vs "pao frances"
                if other_user.startswith(u) or u.startswith(other_user):
                    overlap = max(overlap, 1)
                if u in other_user or other_user in u:
                    overlap = max(overlap, 1)
                if overlap < min_overlap and not (
                    len(u) >= 3 and (u in other_user or other_user in u)
                ):
                    continue
                top = await self.redis.zrevrange(key_s, 0, 2, withscores=True)
                for member, score in top or []:
                    eff = _decode(member)
                    if not eff:
                        continue
                    scores[eff] = max(
                        scores.get(eff, 0.0),
                        float(overlap) * (float(score) + 1.0),
                    )
        except Exception:  # pragma: no cover
            logger.exception("RAGStore.find_similar_effective_terms failed")
            return []

        ranked = sorted(scores.items(), key=lambda kv: -kv[1])
        return [t for t, _ in ranked[:limit]]


def _decode(v: object) -> str:
    if isinstance(v, bytes):
        return v.decode()
    return str(v) if v is not None else ""
