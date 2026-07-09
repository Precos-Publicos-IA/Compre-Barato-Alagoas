"""Deterministic relevance scoring for Verifier (CRAG-style critic, zero LLM cost).

Compares the user's intended label/search_term against SEFAZ product descriptions
without calling a model. Pet-food and seasoning-only noise is down-ranked for
grocery queries.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from ..normalization.matcher import NormalizedOffer

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)
_PET = re.compile(
    r"\b(caes?|cao|gatos?|dog|cat|racao|pet|filhote|canina|felina|"
    r"animal(?:is)?|cachorro|arrozcao|amigaco|luppy)\b",
    re.I,
)
_SEASONING = re.compile(
    r"\b(tempero|sazon|caldo|tablete|maggi|sache|temperinho)\b", re.I
)


def _strip_accents(s: str) -> str:
    nk = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nk if not unicodedata.combining(c))


def _tokens(text: str) -> set[str]:
    t = _strip_accents(text.lower())
    return {m.group(0) for m in _TOKEN_RE.finditer(t) if len(m.group(0)) >= 2}


@dataclass(frozen=True)
class RelevanceResult:
    score: float  # 0..1
    kept: list[NormalizedOffer]
    dropped: int


def score_offer(user_label: str, search_term: str, offer: NormalizedOffer) -> float:
    """Return 0..1 how well one offer matches the user's intent."""
    intent = f"{user_label} {search_term}".strip()
    intent_toks = _tokens(intent)
    desc_toks = _tokens(offer.description or "")
    if not intent_toks or not desc_toks:
        return 0.0

    overlap = intent_toks & desc_toks
    # Primary content words (skip pure size tokens like 1l, 5kg)
    content = {t for t in intent_toks if not re.fullmatch(r"\d+[a-z]*", t)}
    if content and not (content & desc_toks):
        base = 0.05
    else:
        base = len(overlap) / max(len(content) or len(intent_toks), 1)

    desc = offer.description or ""
    if _PET.search(desc) and not _PET.search(intent):
        base *= 0.15
    if _SEASONING.search(desc) and not _SEASONING.search(intent):
        # "feijao" should not rank "tempero feijao" as a great match
        if "tempero" not in intent_toks and "sazon" not in intent_toks:
            base *= 0.35

    return max(0.0, min(1.0, base))


def filter_offers(
    user_label: str,
    search_term: str,
    offers: list[NormalizedOffer],
    *,
    min_score: float = 0.15,
) -> RelevanceResult:
    """Keep offers above ``min_score``; if all would drop, keep original (soft fail)."""
    if not offers:
        return RelevanceResult(score=0.0, kept=[], dropped=0)

    scored = [(score_offer(user_label, search_term, o), o) for o in offers]
    scored.sort(key=lambda x: -x[0])
    kept = [o for s, o in scored if s >= min_score]
    best = scored[0][0]
    if not kept:
        # Soft: keep top few by score so ranking still has something
        kept = [o for _, o in scored[: min(5, len(scored))]]
        return RelevanceResult(score=best, kept=kept, dropped=0)
    return RelevanceResult(
        score=best,
        kept=kept,
        dropped=len(offers) - len(kept),
    )
