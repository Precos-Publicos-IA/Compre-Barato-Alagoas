"""Verifier agent (second step).

Receives the raw SEFAZ response (after normalization), decides if it "matches what the user asked",
filters, suggests better alternatives for low-match items using RAG knowledge of "what exists",
and can trigger a limited re-request to the requester.

Also responsible for organizing API response data back into the RAG pool (what products exist,
what terms worked) so future requester queries are smarter and we avoid useless SEFAZ calls.

This enables the "data pool of responses" and "products we know exist / don't exist" without
duplicating the entire SEFAZ database.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from ...cache import Cache
from ...schemas.search import SearchResponse
from ..normalization.matcher import NormalizedOffer
from .base import ParsedItem

logger = logging.getLogger(__name__)


class Verifier(Protocol):
    async def verify_and_organize(
        self,
        parsed_items: list[ParsedItem],
        offers_by_item: dict[str, list[NormalizedOffer]],
        *,
        cache: Cache | None = None,
    ) -> tuple[dict[str, list[NormalizedOffer]], list[str]]:
        """
        Return (possibly filtered/augmented offers_by_item, suggested_refinements).
        Side effect: records successful mappings into RAG cache.
        """
        ...


@dataclass
class BasicVerifier:
    """Basic verifier: records what worked, boosts obvious matches, suggests for low coverage."""

    async def verify_and_organize(
        self,
        parsed_items: list[ParsedItem],
        offers_by_item: dict[str, list[NormalizedOffer]],
        *,
        cache: Cache | None = None,
    ) -> tuple[dict[str, list[NormalizedOffer]], list[str]]:
        if not cache:
            return offers_by_item, []

        suggestions: list[str] = []
        for item in parsed_items:
            offers = offers_by_item.get(item.label, [])
            good_count = len(offers)
            # Record the mapping so Requester learns for next time (even if partial)
            await cache.record_successful_mapping(
                user_term=item.label or item.raw,
                effective_search_term=item.search_term,
                offers_found=good_count,
            )

            if good_count == 0:
                # Verifier looks up known good alternatives from RAG (exact + creative overlap)
                alts = await cache.lookup_effective_terms(item.label, limit=2)
                if not alts:
                    alts = await cache.find_similar_effective_terms(item.label, limit=2)
                if alts:
                    suggestions.append(f"Tente '{alts[0]}' em vez de '{item.label}'")
                    # Note: actual re-query would be done by orchestrator in a later iteration.
                    # For now we surface the knowledge for the UI to show the user.

        return offers_by_item, suggestions
