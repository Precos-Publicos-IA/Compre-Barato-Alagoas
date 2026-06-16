"""Requester agent (first step of the two-agent architecture).

Takes raw user basket, parses it (current LLM), then uses RAG over past successful
mappings (stored in Cache) + user prefs to produce better search_terms for SEFAZ.

This is the "organize user input tidily + write good API query" role.
Keeps the existing parse_list contract but adds refinement for scale/cost (fewer bad SEFAZ calls).

Lightweight start: uses the new Cache RAG methods (keyword + success counts).
Later can add real embeddings / pgvector without changing callers.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from .base import LLMClient, ParsedItem, ParseResult
from ...cache import Cache

logger = logging.getLogger(__name__)


class Requester(Protocol):
    async def refine_and_parse(
        self, raw_items: list[str], *, cache: Cache | None = None
    ) -> ParseResult:
        """Parse + rewrite using historical RAG for better SEFAZ terms."""
        ...


@dataclass
class BasicRequester:
    """Basic implementation: current parser + simple RAG rewrite from Cache."""

    inner: LLMClient

    async def refine_and_parse(
        self, raw_items: list[str], *, cache: Cache | None = None
    ) -> ParseResult:
        base = await self.inner.parse_list(raw_items)
        if cache is None:
            return base

        refined: list[ParsedItem] = []
        for item in base.items:
            # Try to find a historically successful search_term for this user label/term
            candidates = await cache.lookup_effective_terms(item.label, limit=2)
            if candidates:
                best = candidates[0]
                if best and best != item.search_term.lower():
                    logger.debug("requester: refined %r -> %r (from RAG)", item.search_term, best)
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

        # Record the (possibly refined) terms as "used" for future learning happens in verifier
        return ParseResult(items=refined, usage=base.usage)
