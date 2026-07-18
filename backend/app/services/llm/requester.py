"""Requester agent — query writer (plan side of plan-then-execute).

Takes raw user basket text, parses it (LLM or mock), then rewrites each
``search_term`` using RAG over past successful mappings so SEFAZ/web calls
are more likely to hit real products.

Validated pattern: Enhanced RAG rewrite *before* tool call; no free-form agent loop.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from .base import LLMClient, ParsedItem, ParseResult
from ..rag.store import RAGStore, filter_compatible_terms, rewrite_compatible

logger = logging.getLogger(__name__)


class Requester(Protocol):
    async def refine_and_parse(
        self,
        raw_items: list[str],
        *,
        rag: RAGStore | None = None,
    ) -> ParseResult:
        """Parse + rewrite using historical RAG for better SEFAZ terms."""
        ...


@dataclass
class BasicRequester:
    """Parser + deterministic RAG rewrite (no second LLM call)."""

    inner: LLMClient

    async def refine_and_parse(
        self,
        raw_items: list[str],
        *,
        rag: RAGStore | None = None,
        cache=None,  # backward-compat alias; prefer ``rag``
    ) -> ParseResult:
        if rag is None and cache is not None:
            rag = RAGStore(redis=cache.redis)

        base = await self.inner.parse_list(raw_items)
        if rag is None:
            return base

        refined: list[ParsedItem] = []
        rag_hits = 0
        for item in base.items:
            label = item.label or item.raw or ""
            candidates = await rag.lookup_effective_terms(label, limit=4)
            if not candidates:
                candidates = await rag.find_similar_effective_terms(
                    label, limit=4, min_overlap=1
                )
            # Also try the raw search_term as a key (still class-filtered).
            if not candidates and item.search_term != item.label:
                candidates = await rag.lookup_effective_terms(
                    item.search_term, limit=4
                )
                # Only keep rewrites still compatible with the *user label*.
                candidates = filter_compatible_terms(label, candidates)

            candidates = filter_compatible_terms(label, candidates)
            if candidates:
                best = candidates[0]
                if (
                    best
                    and best != (item.search_term or "").lower()
                    and rewrite_compatible(label, best)
                ):
                    rag_hits += 1
                    logger.debug(
                        "requester: refined %r -> %r (RAG)", item.search_term, best
                    )
                    refined.append(
                        ParsedItem(
                            raw=item.raw,
                            label=item.label,
                            search_term=best,
                            quantity=item.quantity,
                        )
                    )
                    continue
            refined.append(item)

        if rag_hits:
            logger.info("requester: RAG rewrote %d/%d items", rag_hits, len(refined))
        return ParseResult(items=refined, usage=base.usage)
