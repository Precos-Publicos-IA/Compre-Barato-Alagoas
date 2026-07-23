"""Term-mapping knowledge store used by Requester and Verifier.

Wraps Redis so agents depend on a narrow interface (not the whole Cache).
Stores *metadata* about what users type and which SEFAZ search_terms worked —
never full price catalogs (SEFAZ remains source of truth).

Never learn or apply cross-class / head-incompatible rewrites
(e.g. peito de frango → ovos, queijo → pão de queijo). Head alignment is
the systemic gate (``rag/intent.py``); residual class rules remain as belt.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass

from .intent import rewrite_heads_compatible

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)

# Function words that must not create false RAG overlap ("de" linking everything).
_STOP = frozenset(
    "de da do das dos com para em no na nos nas um uma uns umas ao a o e ou "
    "tipo und un pct pacote cx kg g l ml lt po em".split()
)

# Known synonym groups (accent-stripped) so "ovo"↔"ovos" still rewrites.
_SYN_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"ovo", "ovos"}),
    frozenset({"pao", "paes"}),
    frozenset({"cafe", "cafes"}),
    frozenset({"feijao", "feijoes"}),
    frozenset({"oleo", "oleos"}),
    frozenset({"acucar", "acucares"}),
    frozenset({"maca", "macas"}),
    frozenset({"limao", "limoes"}),
)


def _strip_accents(s: str) -> str:
    nk = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nk if not unicodedata.combining(c))


def _norm(term: str) -> str:
    return _strip_accents(term or "").lower().strip()[:64]


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(_norm(text)) if len(t) >= 2}


def content_tokens(text: str) -> set[str]:
    """Content tokens for rewrite compatibility (no stopwords; min len 3)."""
    return {t for t in _tokens(text) if t not in _STOP and len(t) >= 3}


def _expand_synonyms(toks: set[str]) -> set[str]:
    out = set(toks)
    for group in _SYN_GROUPS:
        if out & group:
            out |= group
    return out


def _class_conflict(user_toks: set[str], eff_toks: set[str]) -> bool:
    """True when effective term flips product class vs user intent."""
    # Egg rewrites only for egg intents (live poison: * → ovos).
    egg = {"ovo", "ovos"}
    if (eff_toks & egg) and not (user_toks & egg):
        return True
    # Toilet paper ≠ paper towel (honest id=96).
    if "higienico" in user_toks and "toalha" in eff_toks and "higienico" not in eff_toks:
        return True
    if "toalha" in user_toks and "higienico" in eff_toks and "toalha" not in eff_toks:
        return True
    # Sausage / snack must not collapse to table salt.
    if "salsicha" in user_toks and "salsicha" not in eff_toks:
        if eff_toks <= {"sal"} or (eff_toks & {"sal"} and not (eff_toks & {"salsicha"})):
            if not any(t.startswith("salsich") for t in eff_toks):
                return True
    if "salgadinho" in user_toks and "salgadinho" not in eff_toks:
        if "sal" in eff_toks and not any(
            t.startswith("salg") for t in eff_toks
        ):
            return True
    # Laundry soap must not become dairy (honest id=85 → leite).
    if "sabao" in user_toks and "sabao" not in eff_toks:
        dairy = {"leite", "queijo", "iogurte", "manteiga", "requeijao"}
        if eff_toks & dairy:
            return True
    # Cleaning water ≠ drinking water → egg already covered; água sanitária.
    if "sanitaria" in user_toks or "sanitario" in user_toks:
        if eff_toks & egg:
            return True
        if eff_toks <= {"agua"}:
            return True
    return False


def rewrite_compatible(user_term: str, effective: str) -> bool:
    """Whether ``effective`` is a safe SEFAZ rewrite for ``user_term``.

    Primary gate: head-aligned intents (``rewrite_heads_compatible``) so we never
    learn peito→ovos, queijo→pão de queijo, or drop required ``X de Y`` modifiers.
    Residual ``_class_conflict`` remains as a belt-and-suspenders check.
    """
    u, e = _norm(user_term), _norm(effective)
    if not u or not e:
        return False
    if u == e:
        return True
    # Systemic head gate first (no per-product pairs).
    if not rewrite_heads_compatible(user_term, effective):
        return False
    ut = _expand_synonyms(content_tokens(u))
    et = _expand_synonyms(content_tokens(e))
    if not ut or not et:
        return False
    if _class_conflict(ut, et):
        return False
    if ut & et:
        return True
    # Prefix only for longer stems (pao↔paes already via syn; feijao↔feijoes).
    for a in ut:
        for b in et:
            if len(a) >= 4 and len(b) >= 4 and (a.startswith(b) or b.startswith(a)):
                return True
    return False


def filter_compatible_terms(user_term: str, terms: list[str]) -> list[str]:
    """Drop cross-class / unrelated effective terms for ``user_term``."""
    out: list[str] = []
    seen: set[str] = set()
    for t in terms:
        nt = _norm(t)
        if not nt or nt in seen:
            continue
        if rewrite_compatible(user_term, t):
            seen.add(nt)
            out.append(nt)
    return out


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
        if not rewrite_compatible(user_term, effective_search_term):
            logger.info(
                "RAGStore: refuse cross-class success %r -> %r",
                user_term,
                effective_search_term,
            )
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
            # Over-fetch then filter — poison rows stay in Redis but never apply.
            raw = await self.redis.zrevrange(
                f"rag:effective_for:{u}", 0, max(limit * 4, 8) - 1
            )
            terms = filter_compatible_terms(user_term, [_decode(r) for r in raw])
            return terms[:limit]
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

        ``min_overlap`` defaults to 1 but is applied on *content* tokens only
        (stopwords stripped). Short substring matches like sal⊂salsicha are not
        enough without a real content-token hit.
        """
        u = _norm(user_term)
        user_tokens = _expand_synonyms(content_tokens(u))
        if not user_tokens:
            return []
        # Stricter default: multi-token intents need 2 content hits when possible.
        need = min_overlap
        if len(user_tokens) >= 2:
            need = max(min_overlap, 1)

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
                other_tokens = _expand_synonyms(content_tokens(other_user))
                if not other_tokens:
                    continue
                overlap = len(user_tokens & other_tokens)
                # Stem/prefix boost only for 4+ char content tokens.
                if overlap < need:
                    for a in user_tokens:
                        for b in other_tokens:
                            if len(a) >= 4 and len(b) >= 4 and (
                                a.startswith(b) or b.startswith(a)
                            ):
                                overlap = max(overlap, 1)
                # Full-string containment only when both sides are long enough
                # (pao ⊂ pao frances) — never sal ⊂ salsicha via bare "in".
                if overlap < need and len(u) >= 4 and len(other_user) >= 4:
                    if other_user.startswith(u) or u.startswith(other_user):
                        # Still require at least one content token relationship
                        if user_tokens & other_tokens or any(
                            len(a) >= 4
                            and len(b) >= 4
                            and (a.startswith(b) or b.startswith(a))
                            for a in user_tokens
                            for b in other_tokens
                        ):
                            overlap = max(overlap, 1)
                if overlap < need:
                    continue
                top = await self.redis.zrevrange(key_s, 0, 2, withscores=True)
                for member, score in top or []:
                    eff = _decode(member)
                    if not eff or not rewrite_compatible(user_term, eff):
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
