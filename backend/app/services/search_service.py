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
    SearchRewrite,
)
from .llm.base import LLMClient, LLMUsage
from .llm.orchestrator import SearchOrchestrator
from .llm.pricing import cost_usd
from .normalization.matcher import NormalizedOffer, normalize_offer
from .rag.intent import MATCH_RULES_VERSION
from .rag.outcome_log import log_search_item_outcomes
from .rag.store import RAGStore
from .ranking import build_store_results
from .sefaz.base import SefazClient
from .sefaz.models import PesquisaResponse

logger = logging.getLogger(__name__)


def _cache_key(
    term: str, lat: float, lon: float, radius: int, days: int, source: str = ""
) -> str:
    # Include data source so mock / API / web results never share a cache slot.
    raw = f"{term.lower()}|{lat:.4f}|{lon:.4f}|{radius}|{days}|{source}"
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
    on_progress=None,
    favorite_cnpjs: set[str] | None = None,
) -> SearchResponse:
    lat = req.latitude if req.latitude is not None else MACEIO_LAT
    lon = req.longitude if req.longitude is not None else MACEIO_LON
    radius = req.radius_km or settings.default_radius_km
    days = req.days or settings.default_days

    # Analytics are collected on the hot path but written off it (see the dispatch at the
    # end): a single best-effort background flush, so they never add to user wait time.
    batch = SearchAnalyticsBatch() if analytics is not None else None

    # Stage timers (ms) feed the admin "Performance"/"Providers" tabs. Best-effort:
    # perf_counter deltas only, recorded after the response is built.
    t_start = time.perf_counter()
    sefaz_ms = cache_ms = normalize_ms = 0.0

    # --- Plan-then-execute: Requester → SEFAZ → Verifier (+ optional 1 retry) ---
    rag = RAGStore(redis=cache.redis)
    orchestrator = SearchOrchestrator(llm=llm, rag=rag)

    # Shared timers/provider stats mutated by fetch callback (orchestrator may call
    # fetch twice for the same label when the Verifier requests a better term).
    sefaz_ms = cache_ms = normalize_ms = 0.0
    provider_calls_acc: list[dict] = []
    parse_methods: dict[str, int] = {}
    total_offers = 0
    parsed_offers = 0
    # Track per-label SEFAZ outcome so clients/evals can tell no_data vs upstream_failed.
    # A later successful attempt (e.g. Verifier retry) clears the failed classification.
    labels_fetch_error: set[str] = set()
    labels_fetch_ok: set[str] = set()
    sem = asyncio.Semaphore(max(1, settings.sefaz_concurrency))
    src_ns = getattr(sefaz, "cache_namespace", sefaz.source_name)

    async def _fetch_all_pages(search_term: str, out: dict) -> PesquisaResponse:
        merged: PesquisaResponse | None = None
        page = 1
        while page <= max(1, settings.max_sefaz_pages):
            t0 = time.perf_counter()
            ok = True
            try:
                resp = await sefaz.search_product(
                    descricao=search_term,
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

    async def fetch_offers(search_term: str, label: str) -> list[NormalizedOffer]:
        nonlocal sefaz_ms, cache_ms, normalize_ms, total_offers, parsed_offers
        out = {
            "sefaz_ms": 0.0,
            "cache_ms": 0.0,
            "normalize_ms": 0.0,
            "provider_calls": [],
        }
        key = _cache_key(search_term, lat, lon, radius, days, source=src_ns)
        t0 = time.perf_counter()
        cached = await cache.get_json(key)
        out["cache_ms"] += (time.perf_counter() - t0) * 1000
        resp: PesquisaResponse | None = None
        from_cache = False
        if cached is not None:
            candidate = PesquisaResponse.model_validate(cached)
            # Never trust empty cache entries (stampede/timeout poison with 6h TTL).
            if candidate.conteudo:
                resp = candidate
                from_cache = True
            else:
                logger.info(
                    "Ignoring empty cached SEFAZ response for %r (%r); re-fetching",
                    label,
                    search_term,
                )
                try:
                    await cache.delete(key)
                except Exception:  # pragma: no cover - best-effort purge
                    pass

        if resp is None:
            try:
                async with sem:
                    resp = await asyncio.wait_for(
                        _fetch_all_pages(search_term, out),
                        timeout=settings.sefaz_item_deadline_seconds,
                    )
            except Exception:
                # Do not cache failures — next request must retry upstream.
                labels_fetch_error.add(label)
                logger.warning(
                    "SEFAZ fetch failed for %r (%r); upstream_failed, not caching",
                    label,
                    search_term,
                )
                sefaz_ms += out["sefaz_ms"]
                cache_ms += out["cache_ms"]
                provider_calls_acc.extend(out["provider_calls"])
                return []
            labels_fetch_ok.add(label)
            # Successful empty is true no_data — still do not cache for full TTL.
            # Caching empties poisoned evals/users for hours under load.
            if resp.conteudo:
                t0 = time.perf_counter()
                await cache.set_json(
                    key,
                    resp.model_dump(by_alias=True),
                    ttl=settings.cache_ttl_seconds,
                )
                out["cache_ms"] += (time.perf_counter() - t0) * 1000
            else:
                logger.info(
                    "SEFAZ empty response for %r (%r); no_data, not caching",
                    label,
                    search_term,
                )
        else:
            labels_fetch_ok.add(label)

        t0 = time.perf_counter()
        offers = [
            o for r in resp.conteudo if (o := normalize_offer(r)) is not None
        ]
        out["normalize_ms"] += (time.perf_counter() - t0) * 1000

        sefaz_ms += out["sefaz_ms"]
        cache_ms += out["cache_ms"]
        normalize_ms += out["normalize_ms"]
        provider_calls_acc.extend(out["provider_calls"])
        total_offers += len(offers)
        parsed_offers += sum(1 for o in offers if o.quantity_parsed)
        for o in offers:
            parse_methods[o.parse_method] = parse_methods.get(o.parse_method, 0) + 1
        if from_cache:
            logger.debug("SEFAZ cache hit for %r (%r)", label, search_term)
        return offers

    # Progressive partials: when a fetch finishes, re-rank whatever we have so far.
    async def _progress_bridge(ev: dict):
        if on_progress is None:
            return
        if ev.get("phase") == "fetch" and "offers_by_item" in ev:
            partial_parsed = ev.get("parsed") or []
            labels = [p.label for p in partial_parsed]
            qtys = {
                p.label: max(1, int(p.quantity or 1)) for p in partial_parsed
            }
            partial_offers = ev["offers_by_item"]
            # Only rank labels that already have a finished fetch key present.
            done_labels = [
                lbl
                for lbl in labels
                if lbl in partial_offers
            ]
            stores = build_store_results(
                item_queries=labels,
                offers_by_item={
                    k: partial_offers.get(k, []) for k in labels
                },
                origin=(lat, lon),
                top_n=settings.top_stores,
                excluded_cnpjs=set(req.excluded_cnpjs),
                quantities=qtys,
                favorite_cnpjs=favorite_cnpjs,
            )
            n = len(labels) or 1
            matched = sum(1 for lbl in labels if partial_offers.get(lbl))
            rewrites = [
                SearchRewrite(**r) if isinstance(r, dict) else r
                for r in (ev.get("rewrites") or [])
            ]
            await on_progress(
                {
                    **ev,
                    "partial_response": SearchResponse(
                        origin=Origin(latitude=lat, longitude=lon),
                        radius_km=radius,
                        days=days,
                        items_requested=len(labels),
                        data_source=sefaz.source_name,
                        list_id=None,
                        stores=stores,
                        metrics=SearchMetrics(
                            items_requested=len(labels),
                            stores_found=len(stores),
                            match_rate=round(matched / n, 3),
                            quantity_parse_rate=0.0,
                            search_rewrites=rewrites,
                            items_completed=ev.get("items_completed"),
                            status_message=ev.get("message"),
                            match_rules_version=MATCH_RULES_VERSION,
                        ),
                        partial=True,
                    ),
                }
            )
        else:
            await on_progress(ev)

    t0 = time.perf_counter()
    orch = await orchestrator.run(
        req.items, fetch_offers=fetch_offers, on_progress=_progress_bridge
    )
    llm_ms = (time.perf_counter() - t0) * 1000
    # llm_ms above includes SEFAZ on purpose for total wait; split: re-measure parse
    # is already inside orchestrator. For admin, attribute full orchestrator block to
    # "llm" only for the parse portion is hard without nested timers — keep sefaz_ms
    # accurate from fetch_offers and put residual orchestrator overhead on llm.
    # Correct: llm_ms should not include sefaz. Approximate by subtraction:
    llm_ms = max(0.0, llm_ms - sefaz_ms - cache_ms - normalize_ms)

    parsed = orch.parsed
    offers_by_item = orch.offers_by_item
    suggested_refinements = orch.suggestions
    usage = orch.usage

    if batch is not None:
        llm_ok = settings.use_mock_llm or usage is not None
        batch.provider_calls.append(
            {"provider": "llm", "duration_ms": llm_ms, "ok": llm_ok}
        )
        batch.provider_calls.extend(provider_calls_acc)
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

    # Unique labels (orchestrator already returns first-seen parse order)
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
    items_with_match = sum(1 for lbl in item_queries if offers_by_item.get(lbl))
    # Labels with no offers where every attempt raised/timed out (never a clean empty).
    # Successful empty → true no_data; exception-only → upstream_failed.
    fetch_failed = sorted(
        lbl
        for lbl in item_queries
        if not offers_by_item.get(lbl)
        and lbl in labels_fetch_error
        and lbl not in labels_fetch_ok
    )

    t0 = time.perf_counter()
    stores = build_store_results(
        item_queries=item_queries,
        offers_by_item=offers_by_item,
        origin=(lat, lon),
        top_n=settings.top_stores,
        excluded_cnpjs=set(req.excluded_cnpjs),
        quantities=desired_qtys,
        favorite_cnpjs=favorite_cnpjs,
    )
    rank_ms = (time.perf_counter() - t0) * 1000

    n = len(item_queries) or 1
    rewrites = [
        SearchRewrite(
            label=r["label"],
            original=r["original"],
            search_term=r["search_term"],
        )
        for r in (orch.rewrites or [])
        if r.get("search_term") and r.get("original")
    ]
    metrics = SearchMetrics(
        items_requested=len(item_queries),
        stores_found=len(stores),
        match_rate=round(items_with_match / n, 3),
        quantity_parse_rate=(
            round(parsed_offers / total_offers, 3) if total_offers else 0.0
        ),
        search_rewrites=rewrites,
        items_completed=len(item_queries),
        status_message="Pronto",
        items_fetch_failed=len(fetch_failed),
        fetch_failed_labels=fetch_failed,
        match_rules_version=MATCH_RULES_VERSION,
    )

    if batch is not None:
        notfound = [lbl for lbl in item_queries if not offers_by_item.get(lbl)]
        # no_data = missing after at least one successful upstream response (empty).
        no_data = [
            lbl
            for lbl in notfound
            if lbl in labels_fetch_ok or lbl not in labels_fetch_error
        ]
        batch.search = {
            "items_requested": len(item_queries),
            "items_with_match": items_with_match,
            "total_offers": total_offers,
            "parsed_offers": parsed_offers,
            "data_source": sefaz.source_name,
            "item_labels": item_queries,
            "notfound_labels": notfound,
            "fetch_failed_labels": fetch_failed,
            "no_data_labels": no_data,
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

    # Include verifier suggestions so the app can show "Did you mean..."
    # or pre-fill better terms for poor users who type vaguely.
    metrics.suggested_refinements = suggested_refinements

    # Matching outcome log (JSONL) — no-op unless MATCH_OUTCOME_LOG_PATH is set.
    # Item-level rows; never includes device_token / secrets. Failures are non-fatal.
    try:
        log_search_item_outcomes(
            items=unique_items,
            offers_by_item=offers_by_item,
            stores_found=len(stores),
            data_source=sefaz.source_name,
            fetch_failed_labels=fetch_failed,
            latency_ms=(time.perf_counter() - t_start) * 1000,
            list_id=list_id,
            analytics_id=analytics_id,
        )
    except Exception:  # noqa: BLE001 — never break search on logging
        logger.exception("match outcome log failed")

    return SearchResponse(
        origin=Origin(latitude=lat, longitude=lon),
        radius_km=radius,
        days=days,
        items_requested=len(item_queries),
        data_source=sefaz.source_name,
        list_id=list_id,
        stores=stores,
        metrics=metrics,
        partial=False,
    )
