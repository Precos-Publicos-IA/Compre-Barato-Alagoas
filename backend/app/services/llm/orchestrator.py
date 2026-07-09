"""Plan-then-execute search orchestration with a single Verifier re-query round.

Keeps Requester and Verifier specialized (no peer-agent chat). The orchestrator
is plain Python control flow — the production pattern recommended when latency
and cost matter more than open-ended agency.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from ..normalization.matcher import NormalizedOffer
from ..rag.store import RAGStore
from .base import LLMClient, ParsedItem, ParseResult
from .requester import BasicRequester
from .verifier import BasicVerifier, VerifyOutcome

logger = logging.getLogger(__name__)

# (search_term, label) -> offers  after SEFAZ + normalize
FetchFn = Callable[[str, str], Awaitable[list[NormalizedOffer]]]


@dataclass
class OrchestratorResult:
    parsed: list[ParsedItem]
    offers_by_item: dict[str, list[NormalizedOffer]]
    suggestions: list[str] = field(default_factory=list)
    usage: object | None = None
    retries_done: int = 0
    rag_hits_on_retry: int = 0


@dataclass
class SearchOrchestrator:
    """Requester → fetch → Verifier → optional one re-fetch → Verifier again."""

    llm: LLMClient
    rag: RAGStore
    max_retries_per_item: int = 1

    def __post_init__(self) -> None:
        self.requester = BasicRequester(inner=self.llm)
        self.verifier = BasicVerifier()

    async def run(
        self,
        raw_items: list[str],
        *,
        fetch_offers: FetchFn,
    ) -> OrchestratorResult:
        parse_result: ParseResult = await self.requester.refine_and_parse(
            raw_items, rag=self.rag
        )
        parsed = list(parse_result.items)

        offers_by_item: dict[str, list[NormalizedOffer]] = {}
        for item in parsed:
            offers_by_item[item.label] = await fetch_offers(
                item.search_term, item.label
            )

        outcome = await self.verifier.verify_and_organize(
            parsed, offers_by_item, rag=self.rag, allow_retry=True
        )
        offers_by_item = outcome.offers_by_item
        suggestions = list(outcome.suggestions)
        retries = 0
        rag_retry_hits = 0

        # One bounded re-query round for zero-match labels with a known alternative.
        if outcome.retry_terms and self.max_retries_per_item > 0:
            for label, alt_term in list(outcome.retry_terms.items())[
                :20
            ]:  # safety bound
                item = next((p for p in parsed if p.label == label), None)
                if item is None:
                    continue
                logger.info(
                    "orchestrator: retry label=%r term %r -> %r",
                    label,
                    item.search_term,
                    alt_term,
                )
                item.search_term = alt_term
                new_offers = await fetch_offers(alt_term, label)
                offers_by_item[label] = new_offers
                retries += 1

            # Re-verify after retries (no further retry allowed)
            outcome2 = await self.verifier.verify_and_organize(
                parsed, offers_by_item, rag=self.rag, allow_retry=False
            )
            offers_by_item = outcome2.offers_by_item
            # Prefer post-retry suggestions; keep unique
            seen = set(suggestions)
            for s in outcome2.suggestions:
                if s not in seen:
                    suggestions.append(s)
                    seen.add(s)
            rag_retry_hits = outcome2.rag_successes

        return OrchestratorResult(
            parsed=parsed,
            offers_by_item=offers_by_item,
            suggestions=suggestions,
            usage=parse_result.usage,
            retries_done=retries,
            rag_hits_on_retry=rag_retry_hits,
        )
