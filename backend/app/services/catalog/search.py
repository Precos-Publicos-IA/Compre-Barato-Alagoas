"""Catalog-based search pipeline.

Replaces the old free-text → LLM parse → SEFAZ flow with:
1. Structured input: list of product selections from the catalog enum
2. Query transformation: catalog entries → SEFAZ queries
3. SEFAZ search with geo-based caching
4. LLM-based output validation with retry
5. Deterministic output organization
6. Training flag generation

This module is the new core search orchestrator for structured product input.
The old free-text flow (search_service.py) remains for backward compatibility
but delegates to this when the input is structured.
"""

from __future__ import annotations

import asyncio
import logging
import time
import unicodedata
from dataclasses import dataclass, field

from ...config import Settings
from ...schemas.search import Origin, SearchMetrics, SearchResponse, SearchRewrite, StoreResult
from ..normalization.matcher import NormalizedOffer, normalize_offer
from ..ranking import build_store_results
from ..sefaz.base import SefazClient
from ..sefaz.models import PesquisaResponse
from .manager import CatalogManager, ProductEntry
from .query_transform import ProductSelection, SefazQueryPlan, build_query_plan
from .sefaz_cache import SefazGeoCache
from .validation import (
    ValidationResult,
    build_validation_prompt,
    deterministic_validate,
    parse_validation_response,
)
from ..llm.guardrails import sanitize_for_llm
from ..training.flags import TrainingFlagStore

logger = logging.getLogger(__name__)


def _strip_accents(s: str) -> str:
    nk = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nk if not unicodedata.combining(c)).lower().strip()


@dataclass
class CatalogSearchResult:
    """Result of a catalog-based search."""

    stores: list[StoreResult] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    offers_by_product: dict[int, list[NormalizedOffer]] = field(default_factory=dict)
    validation_results: list[ValidationResult] = field(default_factory=list)
    training_flags_generated: int = 0


async def run_catalog_search(
    selections: list[ProductSelection],
    *,
    catalog: CatalogManager,
    sefaz: SefazClient,
    llm_client=None,
    redis=None,
    settings: Settings,
    lat: float,
    lon: float,
    radius_km: int | None = None,
    days: int | None = None,
    excluded_cnpjs: set[str] | None = None,
    favorite_cnpjs: set[str] | None = None,
    flag_store: TrainingFlagStore | None = None,
    on_progress=None,
) -> SearchResponse:
    """Execute a catalog-based search pipeline.

    Steps:
    1. Build query plan from selections
    2. Execute SEFAZ queries with geo-cache
    3. Validate results with LLM
    4. Re-query on validation failures
    5. Organize and return results
    6. Generate training flags
    """
    radius = radius_km or settings.default_radius_km
    days_val = days or settings.default_days

    # 1. Build query plan
    plan = build_query_plan(selections, catalog)
    if not plan.queries:
        return SearchResponse(
            origin=Origin(latitude=lat, longitude=lon),
            radius_km=radius,
            days=days_val,
            items_requested=0,
            data_source=sefaz.source_name,
            stores=[],
            metrics=SearchMetrics(
                items_requested=0,
                stores_found=0,
                match_rate=0.0,
                quantity_parse_rate=0.0,
            ),
        )

    # 2. Execute SEFAZ queries with geo-cache
    geo_cache = SefazGeoCache(
        redis=redis,
        ttl=settings.cache_ttl_seconds,
        source=getattr(sefaz, "cache_namespace", sefaz.source_name),
    ) if redis else None

    sem = asyncio.Semaphore(max(1, settings.sefaz_concurrency))
    offers_by_product: dict[int, list[NormalizedOffer]] = {}
    search_terms_used: dict[int, list[str]] = {}

    # Group the plan's queries by product so we can cache at the enum-item level
    # (spec: one cache entry per product, hit when a nearby search exists).
    queries_by_product: dict[int, list[SefazQueryPlan]] = {}
    for q in plan.queries:
        queries_by_product.setdefault(q.product_id, []).append(q)

    async def _run_one_query(query: SefazQueryPlan) -> list:
        """Fetch one SEFAZ query (with per-query geo-cache). Returns Registro rows."""
        if geo_cache:
            cached = await geo_cache.get_query(query.search_term, lat, lon)
            if cached is not None:
                return PesquisaResponse.model_validate(cached).conteudo
        try:
            async with sem:
                resp = await asyncio.wait_for(
                    sefaz.search_product(
                        descricao=query.search_term,
                        latitude=lat,
                        longitude=lon,
                        radius_km=radius,
                        days=days_val,
                    ),
                    timeout=settings.sefaz_item_deadline_seconds,
                )
        except Exception:
            logger.warning("SEFAZ fetch failed for %s (%s)", query.display_name, query.search_term)
            return []
        if geo_cache and resp.conteudo:
            await geo_cache.set_query(query.search_term, lat, lon, resp.model_dump(by_alias=True))
        return resp.conteudo

    async def fetch_product(pid: int, queries: list[SefazQueryPlan]) -> tuple[int, list[NormalizedOffer], bool]:
        """Resolve one product: product-level cache hit, else run + merge its queries."""
        search_terms_used[pid] = [q.search_term for q in queries]

        # Product-level geo cache: a nearby prior search for this enum item is a hit.
        if geo_cache:
            cached = await geo_cache.get_product(pid, lat, lon)
            if cached is not None:
                resp = PesquisaResponse.model_validate(cached)
                offers = [o for r in resp.conteudo if (o := normalize_offer(r)) is not None]
                return pid, offers, True

        registros: list = []
        for query in queries:
            registros.extend(await _run_one_query(query))

        # Cache the merged result at the product level for future nearby searches.
        if geo_cache and registros:
            merged = PesquisaResponse(conteudo=registros).model_dump(by_alias=True)
            await geo_cache.set_product(pid, lat, lon, merged)

        offers = [o for r in registros if (o := normalize_offer(r)) is not None]
        return pid, offers, False

    # Execute one task per product concurrently.
    tasks = [
        asyncio.create_task(fetch_product(pid, qs))
        for pid, qs in queries_by_product.items()
    ]
    completed = 0
    total = len(tasks)

    for coro in asyncio.as_completed(tasks):
        pid, offers, from_cache = await coro
        completed += 1
        offers_by_product.setdefault(pid, []).extend(offers)

        if on_progress:
            await on_progress({
                "phase": "fetch",
                "message": f"Buscando preços ({completed}/{total})…",
                "items_completed": completed,
                "items_total": total,
            })

    # Deduplicate offers per product (same store + description = duplicate)
    for pid in offers_by_product:
        seen = set()
        unique = []
        for o in offers_by_product[pid]:
            key = (o.cnpj, o.description, o.price)
            if key not in seen:
                seen.add(key)
                unique.append(o)
        offers_by_product[pid] = unique

    # 3. Validate results. Prefer the cheap LLM (one call for all products, with
    # sanitised descriptions); fall back to deterministic rules per product when
    # no client is configured or the call fails.
    validation_results = []
    retry_products = []

    llm_verdicts: dict[str, dict] = {}
    if llm_client is not None and hasattr(llm_client, "validate_sefaz_output"):
        payload = []
        for pid, offers in offers_by_product.items():
            product = catalog.get(pid)
            if not product:
                continue
            samples = [o.description for o in offers if o.description][:10]
            payload.append({
                "product_slug": product.slug,
                "display_name": product.display_name,
                "category": product.category,
                "search_terms_used": search_terms_used.get(pid, []),
                "sample_descriptions": [sanitize_for_llm(d, max_len=80) for d in samples],
                "known_positive": product.sefaz_terms_positive,
                "known_negative": product.sefaz_terms_negative,
            })
        if payload:
            try:
                raw = await llm_client.validate_sefaz_output(build_validation_prompt(payload))
                for item in parse_validation_response(raw or ""):
                    slug = item.get("product_slug")
                    if slug:
                        llm_verdicts[slug] = item
            except Exception:
                logger.warning("LLM validation failed; using deterministic", exc_info=True)

    for pid, offers in offers_by_product.items():
        product = catalog.get(pid)
        if not product:
            continue

        verdict = llm_verdicts.get(product.slug)
        if verdict is not None:
            vr = ValidationResult(
                product_id=pid,
                product_slug=product.slug,
                valid=bool(verdict.get("valid", True)),
                reason=str(verdict.get("reason", "llm"))[:200],
                rejected_descriptions=verdict.get("rejected_descriptions") or None,
                new_negative_terms=verdict.get("suggested_negative_terms") or None,
                corrected_search_terms=verdict.get("corrected_search_terms") or None,
            )
        else:
            descs = [o.description for o in offers if o.description][:15]
            vr = deterministic_validate(
                product_slug=product.slug,
                display_name=product.display_name,
                category=product.category,
                descriptions=descs,
                known_negative=product.sefaz_terms_negative,
            )
            vr.product_id = pid
        validation_results.append(vr)

        if not vr.valid:
            retry_products.append(pid)
            # Filter out rejected descriptions
            if vr.rejected_descriptions:
                rej_set = set(vr.rejected_descriptions)
                offers_by_product[pid] = [
                    o for o in offers if o.description not in rej_set
                ]

    # 4. Re-query on validation failures (one retry). Works with or without
    # Redis: cache invalidation is best-effort, the re-query always runs.
    for pid in retry_products:
        product = catalog.get(pid)
        if not product:
            continue

        # Invalidate the stale product cache so the retry isn't served from it.
        if geo_cache:
            await geo_cache.invalidate_product(pid, lat, lon)

        # Try alternative search terms we haven't already used.
        alt_terms = [q for q in product.search_queries if q not in search_terms_used.get(pid, [])]
        for term in alt_terms[:2]:
            query = SefazQueryPlan(
                product_id=pid,
                product_slug=product.slug,
                display_name=product.display_name,
                search_term=term,
            )
            registros = await _run_one_query(query)
            search_terms_used.setdefault(pid, []).append(term)
            offers_by_product[pid].extend(
                o for r in registros if (o := normalize_offer(r)) is not None
            )

    # 5. Build store results
    # Map product_id -> display_name for ranking
    product_labels = {}
    product_quantities = {}
    for sel in selections:
        product = catalog.get(sel.product_id)
        if product:
            product_labels[sel.product_id] = product.display_name
            product_quantities[sel.product_id] = sel.quantity

    # Convert to the label-based format expected by build_store_results
    offers_by_label: dict[str, list[NormalizedOffer]] = {}
    for pid, offers in offers_by_product.items():
        label = product_labels.get(pid, str(pid))
        offers_by_label[label] = offers

    item_queries = list(offers_by_label.keys())
    desired_qtys = {
        product_labels.get(sel.product_id, str(sel.product_id)): sel.quantity
        for sel in selections
        if catalog.get(sel.product_id)
    }

    stores = build_store_results(
        item_queries=item_queries,
        offers_by_item=offers_by_label,
        origin=(lat, lon),
        top_n=settings.top_stores,
        excluded_cnpjs=excluded_cnpjs or set(),
        quantities=desired_qtys,
        favorite_cnpjs=favorite_cnpjs,
    )

    # 6. Generate training flags
    training_flags_count = 0
    if flag_store:
        # Flag products not found
        for sel in selections:
            product = catalog.get(sel.product_id)
            if not product:
                continue
            label = product.display_name
            if not offers_by_label.get(label):
                flag_store.flag_product_not_found(
                    product_id=sel.product_id,
                    product_slug=product.slug,
                    search_terms_used=search_terms_used.get(sel.product_id, []),
                    location=(lat, lon),
                )
                training_flags_count += 1

        # Flag validation failures
        for vr in validation_results:
            if not vr.valid:
                flag_store.flag_validation_failure(
                    product_id=vr.product_id,
                    product_slug=vr.product_slug,
                    search_term=",".join(search_terms_used.get(vr.product_id, [])),
                    rejected_descriptions=vr.rejected_descriptions or [],
                    reason=vr.reason,
                )
                training_flags_count += 1

        # Analyze store coverage for training
        if len(selections) >= 3:
            store_products: dict[str, dict] = {}
            for store in stores:
                found_labels = [it.query for it in store.items if it.found]
                missing_labels = store.missing
                store_products[store.cnpj] = {
                    "name": store.name,
                    "found": found_labels,
                    "missing": missing_labels,
                }

            for cnpj, info in store_products.items():
                total_requested = len(selections)
                n_found = len(info["found"])
                ratio = n_found / total_requested if total_requested else 0
                if 0.20 < ratio < 0.80 and info["missing"]:
                    flag_store.flag_incomplete_coverage(
                        store_cnpj=cnpj,
                        store_name=info["name"],
                        products_found=info["found"],
                        products_missing=info["missing"],
                        coverage_ratio=ratio,
                    )
                    training_flags_count += 1

    # Build metrics
    items_with_match = sum(1 for label in item_queries if offers_by_label.get(label))
    n = len(item_queries) or 1
    total_offers = sum(len(v) for v in offers_by_label.values())
    parsed_offers = sum(
        sum(1 for o in offers if o.quantity_parsed)
        for offers in offers_by_label.values()
    )

    rewrites = [
        SearchRewrite(
            label=product_labels.get(pid, str(pid)),
            original=product_labels.get(pid, ""),
            search_term=", ".join(terms),
        )
        for pid, terms in search_terms_used.items()
        if terms
    ]

    metrics = SearchMetrics(
        items_requested=len(item_queries),
        stores_found=len(stores),
        match_rate=round(items_with_match / n, 3),
        quantity_parse_rate=round(parsed_offers / total_offers, 3) if total_offers else 0.0,
        search_rewrites=rewrites,
        items_completed=len(item_queries),
        status_message="Pronto",
    )

    return SearchResponse(
        origin=Origin(latitude=lat, longitude=lon),
        radius_km=radius,
        days=days_val,
        items_requested=len(item_queries),
        data_source=sefaz.source_name,
        stores=stores,
        metrics=metrics,
    )
