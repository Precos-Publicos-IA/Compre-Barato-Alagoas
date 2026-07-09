"""Plan-then-execute search orchestration with a single Verifier re-query round.

Supports optional progress callbacks so the UI can show live status while SEFAZ/web
fetches complete (as_completed), without open multi-agent chat.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from ..normalization.matcher import NormalizedOffer
from ..rag.store import RAGStore
from .base import LLMClient, ParsedItem, ParseResult
from .requester import BasicRequester
from .verifier import BasicVerifier, VerifyOutcome

logger = logging.getLogger(__name__)

FetchFn = Callable[[str, str], Awaitable[list[NormalizedOffer]]]
ProgressFn = Callable[[dict], Awaitable[None] | None]


@dataclass
class OrchestratorResult:
    parsed: list[ParsedItem]
    offers_by_item: dict[str, list[NormalizedOffer]]
    suggestions: list[str] = field(default_factory=list)
    usage: object | None = None
    retries_done: int = 0
    rag_hits_on_retry: int = 0
    rewrites: list[dict[str, str]] = field(default_factory=list)


async def _emit(progress: ProgressFn | None, payload: dict) -> None:
    if progress is None:
        return
    maybe = progress(payload)
    if asyncio.iscoroutine(maybe):
        await maybe


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
        on_progress: ProgressFn | None = None,
    ) -> OrchestratorResult:
        await _emit(
            on_progress,
            {
                "phase": "parse",
                "message": "Entendendo sua lista…",
                "items_completed": 0,
                "items_total": len(raw_items),
            },
        )
        parse_result: ParseResult = await self.requester.refine_and_parse(
            raw_items, rag=self.rag
        )
        parsed = list(parse_result.items)
        total = len(parsed) or 1

        rewrites: list[dict[str, str]] = []
        for item in parsed:
            orig = (item.label or item.raw or "").strip()
            st = (item.search_term or "").strip()
            if st and orig and st.casefold() != orig.casefold():
                rewrites.append(
                    {
                        "label": item.label,
                        "original": orig,
                        "search_term": st,
                    }
                )

        await _emit(
            on_progress,
            {
                "phase": "fetch",
                "message": f"Buscando preços (0/{len(parsed)})…",
                "items_completed": 0,
                "items_total": len(parsed),
                "rewrites": rewrites,
            },
        )

        offers_by_item: dict[str, list[NormalizedOffer]] = {
            item.label: [] for item in parsed
        }
        completed = 0

        async def _one(item: ParsedItem) -> tuple[str, list[NormalizedOffer]]:
            offers = await fetch_offers(item.search_term, item.label)
            return item.label, offers

        tasks = [asyncio.create_task(_one(it)) for it in parsed]
        for coro in asyncio.as_completed(tasks):
            label, offers = await coro
            offers_by_item[label] = offers
            completed += 1
            await _emit(
                on_progress,
                {
                    "phase": "fetch",
                    "message": f"Buscando preços ({completed}/{len(parsed)})…",
                    "items_completed": completed,
                    "items_total": len(parsed),
                    "item_done": label,
                    "offers_found": len(offers),
                    "offers_by_item": {
                        k: list(v) for k, v in offers_by_item.items()
                    },
                    "parsed": parsed,
                    "rewrites": rewrites,
                },
            )

        outcome = await self.verifier.verify_and_organize(
            parsed, offers_by_item, rag=self.rag, allow_retry=True
        )
        offers_by_item = outcome.offers_by_item
        suggestions = list(outcome.suggestions)
        retries = 0
        rag_retry_hits = 0

        if outcome.retry_terms and self.max_retries_per_item > 0:
            await _emit(
                on_progress,
                {
                    "phase": "retry",
                    "message": "Ajustando buscas com termos melhores…",
                    "items_completed": completed,
                    "items_total": len(parsed),
                },
            )
            for label, alt_term in list(outcome.retry_terms.items())[:20]:
                idx = next((i for i, p in enumerate(parsed) if p.label == label), None)
                if idx is None:
                    continue
                item = parsed[idx]
                logger.info(
                    "orchestrator: retry label=%r term %r -> %r",
                    label,
                    item.search_term,
                    alt_term,
                )
                parsed[idx] = ParsedItem(
                    raw=item.raw,
                    label=item.label,
                    search_term=alt_term,
                    quantity=item.quantity,
                )
                rewrites.append(
                    {
                        "label": label,
                        "original": item.search_term,
                        "search_term": alt_term,
                    }
                )
                new_offers = await fetch_offers(alt_term, label)
                offers_by_item[label] = new_offers
                retries += 1

            outcome2 = await self.verifier.verify_and_organize(
                parsed, offers_by_item, rag=self.rag, allow_retry=False
            )
            offers_by_item = outcome2.offers_by_item
            seen = set(suggestions)
            for s in outcome2.suggestions:
                if s not in seen:
                    suggestions.append(s)
                    seen.add(s)
            rag_retry_hits = outcome2.rag_successes

        await _emit(
            on_progress,
            {
                "phase": "rank",
                "message": "Montando o ranking das lojas…",
                "items_completed": len(parsed),
                "items_total": len(parsed),
            },
        )

        return OrchestratorResult(
            parsed=parsed,
            offers_by_item=offers_by_item,
            suggestions=suggestions,
            usage=parse_result.usage,
            retries_done=retries,
            rag_hits_on_retry=rag_retry_hits,
            rewrites=rewrites,
        )
