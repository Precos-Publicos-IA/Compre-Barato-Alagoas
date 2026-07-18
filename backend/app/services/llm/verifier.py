"""Verifier agent — critic (CRAG-style) after SEFAZ returns.

Scores offers deterministically, records RAG success/miss, and may request
*one* alternative search_term for zero-match items (orchestrator performs the
re-fetch — Verifier does not call SEFAZ itself).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

from ..normalization.matcher import NormalizedOffer
from ..rag.relevance import filter_offers, offer_package_class_ok
from ..rag.store import RAGStore, filter_compatible_terms, rewrite_compatible
from .base import ParsedItem

logger = logging.getLogger(__name__)


@dataclass
class VerifyOutcome:
    offers_by_item: dict[str, list[NormalizedOffer]]
    suggestions: list[str] = field(default_factory=list)
    # label -> alternative search_term the orchestrator may re-fetch once
    retry_terms: dict[str, str] = field(default_factory=dict)
    rag_successes: int = 0
    rag_misses: int = 0


class Verifier(Protocol):
    async def verify_and_organize(
        self,
        parsed_items: list[ParsedItem],
        offers_by_item: dict[str, list[NormalizedOffer]],
        *,
        rag: RAGStore | None = None,
        allow_retry: bool = True,
    ) -> VerifyOutcome:
        ...


@dataclass
class BasicVerifier:
    """Rules + RAG critic; no LLM on the hot path."""

    # Stricter default: candy/pet noise must not pass as "success" for RAG learning.
    min_score: float = 0.35
    # Only learn mappings when the best offer is clearly on-intent (D5: in-class).
    min_score_to_learn: float = 0.50

    async def verify_and_organize(
        self,
        parsed_items: list[ParsedItem],
        offers_by_item: dict[str, list[NormalizedOffer]],
        *,
        rag: RAGStore | None = None,
        cache=None,  # backward-compat
        allow_retry: bool = True,
    ) -> VerifyOutcome | tuple:
        if rag is None and cache is not None:
            rag = RAGStore(redis=cache.redis)

        suggestions: list[str] = []
        retry_terms: dict[str, str] = {}
        out: dict[str, list[NormalizedOffer]] = {}
        successes = 0
        misses = 0

        for item in parsed_items:
            offers = list(offers_by_item.get(item.label, []))
            rel = filter_offers(
                item.label, item.search_term, offers, min_score=self.min_score
            )
            out[item.label] = rel.kept
            good_count = len(rel.kept)

            if rag is not None:
                best_offer = rel.kept[0] if rel.kept else None
                in_class = (
                    best_offer is not None
                    and offer_package_class_ok(
                        item.label, item.search_term, best_offer
                    )
                )
                # D5: do not learn coco-oil / pasta-as-egg into staple term maps.
                if (
                    good_count > 0
                    and rel.score >= self.min_score_to_learn
                    and in_class
                ):
                    await rag.record_success(
                        user_term=item.label or item.raw,
                        effective_search_term=item.search_term,
                        offers_found=good_count,
                    )
                    successes += 1
                elif good_count == 0:
                    await rag.record_miss(
                        user_term=item.label or item.raw,
                        attempted_search_term=item.search_term,
                    )
                    misses += 1

            if good_count == 0 and rag is not None:
                label = item.label or item.raw or ""
                alts = await rag.lookup_effective_terms(label, limit=5)
                if not alts:
                    alts = await rag.find_similar_effective_terms(
                        label, limit=5, min_overlap=1
                    )
                alts = filter_compatible_terms(label, alts)
                # Don't retry the same term we already used or cross-class poison.
                alts = [
                    a
                    for a in alts
                    if a
                    and a.lower() != (item.search_term or "").lower()
                    and rewrite_compatible(label, a)
                ]
                if alts and allow_retry:
                    retry_terms[item.label] = alts[0]
                if alts:
                    suggestions.append(
                        f"Tente '{alts[0]}' em vez de '{item.label}'"
                    )

        return VerifyOutcome(
            offers_by_item=out,
            suggestions=suggestions,
            retry_terms=retry_terms,
            rag_successes=successes,
            rag_misses=misses,
        )
