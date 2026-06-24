"""Orchestrates a basket search: parse -> fetch per item -> normalize -> rank.

Each item is an independent SEFAZ call (the API takes only one criterion per request),
so results are cached per (search_term, origin, radius, days) to keep repeat searches
fast and to limit load on SEFAZ once we're live.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time

from fastapi import BackgroundTasks

from ..analytics import SearchAnalyticsBatch
from ..config import MACEIO_LAT, MACEIO_LON, Settings
from ..schemas.search import (
    Origin,
    SearchMetrics,
    SearchRequest,
    SearchResponse,
)
from .llm.base import LLMClient, LLMUsage
from .llm.pricing import cost_usd
from .llm.requester import BasicRequester
from .llm.verifier import BasicVerifier
from .normalization.matcher import NormalizedOffer, normalize_offer
from .ranking import build_store_results
from .sefaz.base import SefazClient
from .sefaz.models import PesquisaResponse

logger = logging.getLogger(__name__)


def _cache_key(term: str, lat: float, lon: float, radius: int, days: int) -> str:
    raw = f"{term.lower()}|{lat:.4f}|{lon:.4f}|{radius}|{days}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"sefaz:search:{digest}"


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token) for the mock/fallback path so the
    cost dashboard isn't empty before the real Claude key is wired."""
    return max(1, len(text) // 4)


async def run_search(
    req: SearchRequest,
    *,
    settings: Settings,
    sefaz: SefazClient,
    llm: LLMClient,
    cache,
    analytics=None,
    device_token: str | None = None,
    analytics_id: str | None = None,
    background: BackgroundTasks | None = None,
) -> SearchResponse:
    lat = req.latitude if req.latitude is not None else MACEIO_LAT
    lon = req.longitude if req.longitude is not None else MACEIO_LON
    radius = req.radius_km or settings.default_radius_km
    days = req.days or settings.default_days

    # Analytics are collected on the hot path but written off it (see the dispatch at the
    # end): a single best-effort background flush, so they never add to user wait time.
    batch = SearchAnalyticsBatch() if analytics is not None else None

    # Stage timers (ms) feed the admin "Desempenho"/"Provedores" tabs. Best-effort:
    # perf_counter deltas only, recorded after the response is built.
    t_start = time.perf_counter()
    sefaz_ms = cache_ms = normalize_ms = 0.0

    t0 = time.perf_counter()
    # Use Requester agent (wraps LLM + RAG refinement from past successful mappings)
    requester = BasicRequester(inner=llm)
    result = await requester.refine_and_parse(req.items, cache=cache)
    llm_ms = (time.perf_counter() - t0) * 1000
    parsed = result.items

    # Token usage for cost tracking. Real client returns it; the mock/fallback
    # path returns None, so we estimate from the text size and flag it as mock.
    usage = result.usage

    # Provider (AI) health: in production a None usage means the real Claude call
    # failed and fell back to the mock parser — a meaningful degradation signal.
    if batch is not None:
        llm_ok = settings.use_mock_llm or usage is not None
        batch.provider_calls.append(
            {"provider": "llm", "duration_ms": llm_ms, "ok": llm_ok}
        )
    if usage is None:
        usage = LLMUsage(
            input_tokens=_estimate_tokens("\n".join(req.items)),
            output_tokens=_estimate_tokens(
                " ".join(f"{p.label}{p.search_term}" for p in parsed)
            ),
        )
    if batch is not None:
        batch.llm_call = {
            "model": settings.llm_model,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cache_read_tokens": usage.cache_read_tokens,
            "cache_creation_tokens": usage.cache_creation_tokens,
            "cost_usd": cost_usd(
                settings.llm_model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_read_tokens=usage.cache_read_tokens,
                cache_creation_tokens=usage.cache_creation_tokens,
            ),
        }

    # Unique items in first-seen order. We carry the user's desired quantity per item
    # (parsed by the LLM/mock, e.g. "3 arroz", "meia dúzia ovos") into ranking so basket
    # totals reflect how much they actually want to buy.
    seen_labels: set[str] = set()
    unique_items = []
    for item in parsed:
        if item.label in seen_labels:
            continue
        seen_labels.add(item.label)
        unique_items.append(item)
    item_queries: list[str] = [it.label for it in unique_items]
    desired_qtys: dict[str, int] = {
        it.label: max(1, int(it.quantity or 1)) for it in unique_items
    }

    # Per-item fetch, run concurrently (bounded) to cut wall time for cold multi-item
    # baskets. Each item is independent (one SEFAZ criterion per call). A per-item
    # failure yields *partial* results instead of failing the whole search.
    sem = asyncio.Semaphore(max(1, settings.sefaz_concurrency))

    async def _fetch_one(item) -> dict:
        out = {
            "label": item.label,
            "offers": [],
            "sefaz_ms": 0.0,
            "cache_ms": 0.0,
            "normalize_ms": 0.0,
            "provider_calls": [],
            "degraded": False,
        }
        key = _cache_key(item.search_term, lat, lon, radius, days)
        t0 = time.perf_counter()
        cached = await cache.get_json(key)
        out["cache_ms"] += (time.perf_counter() - t0) * 1000
        if cached is not None:
            resp = PesquisaResponse.model_validate(cached)
        else:
            try:
                async with sem:
                    resp = await _fetch_all_pages(item, out)
            except Exception:
                # Resilience: one failing item must not 502 the whole basket.
                logger.warning("SEFAZ fetch failed for %r; partial results", item.label)
                out["degraded"] = True
                return out
            t0 = time.perf_counter()
            await cache.set_json(
                key, resp.model_dump(by_alias=True), ttl=settings.cache_ttl_seconds
            )
            out["cache_ms"] += (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        out["offers"] = [
            o for r in resp.conteudo if (o := normalize_offer(r)) is not None
        ]
        out["normalize_ms"] += (time.perf_counter() - t0) * 1000
        return out

    async def _fetch_all_pages(item, out: dict) -> PesquisaResponse:
        """Fetch up to ``max_sefaz_pages`` pages and merge them. Records per-call
        timing/health on ``out`` so provider stats stay accurate."""
        merged: PesquisaResponse | None = None
        page = 1
        while page <= max(1, settings.max_sefaz_pages):
            t0 = time.perf_counter()
            ok = True
            try:
                resp = await sefaz.search_product(
                    descricao=item.search_term,
                    latitude=lat,
                    longitude=lon,
                    radius_km=radius,
                    days=days,
                    pagina=page,
                    registros_por_pagina=settings.records_per_page,
                )
            except Exception:
                ok = False
                raise
            finally:
                call_ms = (time.perf_counter() - t0) * 1000
                out["sefaz_ms"] += call_ms
                out["provider_calls"].append(
                    {"provider": "sefaz", "duration_ms": call_ms, "ok": ok}
                )
            if merged is None:
                merged = resp
            else:
                merged.conteudo.extend(resp.conteudo)
            if page >= (resp.total_paginas or 1):
                break
            page += 1
        return merged  # type: ignore[return-value]

    results = await asyncio.gather(*(_fetch_one(it) for it in unique_items))

    offers_by_item: dict[str, list[NormalizedOffer]] = {}
    degraded_items: list[str] = []
    total_offers = 0
    parsed_offers = 0
    items_with_match = 0
    parse_methods: dict[str, int] = {}
    for r in results:
        sefaz_ms += r["sefaz_ms"]
        cache_ms += r["cache_ms"]
        normalize_ms += r["normalize_ms"]
        if batch is not None and r["provider_calls"]:
            batch.provider_calls.extend(r["provider_calls"])
        if r.get("degraded"):
            degraded_items.append(r["label"])
        offers = r["offers"]
        offers_by_item[r["label"]] = offers
        if offers:
            items_with_match += 1
        total_offers += len(offers)
        parsed_offers += sum(1 for o in offers if o.quantity_parsed)
        for o in offers:
            parse_methods[o.parse_method] = parse_methods.get(o.parse_method, 0) + 1

    # Verifier agent (before ranking): records successful mappings into RAG for the
    # Requester to learn from, and produces audience-friendly refinements for vague terms.
    verifier = BasicVerifier()
    offers_by_item, suggested_refinements = await verifier.verify_and_organize(
        parsed_items=parsed, offers_by_item=offers_by_item, cache=cache
    )

    t0 = time.perf_counter()
    stores = build_store_results(
        item_queries=item_queries,
        offers_by_item=offers_by_item,
        origin=(lat, lon),
        top_n=settings.top_stores,
        excluded_cnpjs=set(req.excluded_cnpjs),
        quantities=desired_qtys,
    )
    rank_ms = (time.perf_counter() - t0) * 1000

    n = len(item_queries) or 1
    metrics = SearchMetrics(
        items_requested=len(item_queries),
        stores_found=len(stores),
        match_rate=round(items_with_match / n, 3),
        quantity_parse_rate=(
            round(parsed_offers / total_offers, 3) if total_offers else 0.0
        ),
    )

    if batch is not None:
        notfound = [lbl for lbl in item_queries if not offers_by_item.get(lbl)]
        batch.search = {
            "items_requested": len(item_queries),
            "items_with_match": items_with_match,
            "total_offers": total_offers,
            "parsed_offers": parsed_offers,
            "data_source": sefaz.source_name,
            "item_labels": item_queries,
            "notfound_labels": notfound,
            "parse_methods": parse_methods,
            "device_token": device_token,
            "analytics_id": analytics_id,
        }

    # Persist the list under a UUID so it can be shared via a short link and
    # reused on identical searches. Never blocks the search if storage fails.
    t0 = time.perf_counter()
    list_id = await cache.save_search_list(req.items)

    # If a consented device made this search, remember the list under that device
    # (login-free server-side history). No-op for unknown/un-consented tokens.
    if device_token and list_id:
        await cache.attach_list(device_token, list_id)
    cache_ms += (time.perf_counter() - t0) * 1000

    # Dispatch all analytics writes off the request critical path. ``total`` is measured
    # here, before dispatch, so it reflects the user's actual wait (analytics excluded).
    if analytics is not None and batch is not None:
        batch.timings = {
            "total": (time.perf_counter() - t_start) * 1000,
            "llm": llm_ms,
            "sefaz": sefaz_ms,
            "cache": cache_ms,
            "normalize": normalize_ms,
            "rank": rank_ms,
        }
        if background is not None:
            background.add_task(analytics.flush, batch)
        else:
            # No background context (e.g. direct service-level tests): write inline.
            await analytics.flush(batch)

    # Include verifier suggestions so the app can show "Talvez você quis dizer..."
    # or pre-fill better terms for poor users who type vaguely.
    metrics.suggested_refinements = suggested_refinements

    return SearchResponse(
        origin=Origin(latitude=lat, longitude=lon),
        radius_km=radius,
        days=days,
        items_requested=len(item_queries),
        data_source=sefaz.source_name,
        list_id=list_id,
        stores=stores,
        metrics=metrics,
        degraded_items=degraded_items,
    )
