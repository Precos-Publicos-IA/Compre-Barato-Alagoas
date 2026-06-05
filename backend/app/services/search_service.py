"""Orchestrates a basket search: parse -> fetch per item -> normalize -> rank.

Each item is an independent SEFAZ call (the API takes only one criterion per request),
so results are cached per (search_term, origin, radius, days) to keep repeat searches
fast and to limit load on SEFAZ once we're live.
"""

from __future__ import annotations

import hashlib
import logging

from ..config import MACEIO_LAT, MACEIO_LON, Settings
from ..schemas.search import (
    Origin,
    SearchMetrics,
    SearchRequest,
    SearchResponse,
)
from .llm.base import LLMClient
from .normalization.matcher import NormalizedOffer, normalize_offer
from .ranking import build_store_results
from .sefaz.base import SefazClient
from .sefaz.models import PesquisaResponse

logger = logging.getLogger(__name__)


def _cache_key(term: str, lat: float, lon: float, radius: int, days: int) -> str:
    raw = f"{term.lower()}|{lat:.4f}|{lon:.4f}|{radius}|{days}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"sefaz:search:{digest}"


async def run_search(
    req: SearchRequest,
    *,
    settings: Settings,
    sefaz: SefazClient,
    llm: LLMClient,
    cache,
) -> SearchResponse:
    lat = req.latitude if req.latitude is not None else MACEIO_LAT
    lon = req.longitude if req.longitude is not None else MACEIO_LON
    radius = req.radius_km or settings.default_radius_km
    days = req.days or settings.default_days

    parsed = await llm.parse_list(req.items)

    offers_by_item: dict[str, list[NormalizedOffer]] = {}
    item_queries: list[str] = []
    total_offers = 0
    parsed_offers = 0
    items_with_match = 0

    for item in parsed:
        if item.label in offers_by_item:
            continue
        item_queries.append(item.label)

        key = _cache_key(item.search_term, lat, lon, radius, days)
        cached = await cache.get_json(key)
        if cached is not None:
            resp = PesquisaResponse.model_validate(cached)
        else:
            resp = await sefaz.search_product(
                descricao=item.search_term,
                latitude=lat,
                longitude=lon,
                radius_km=radius,
                days=days,
                registros_por_pagina=settings.records_per_page,
            )
            await cache.set_json(
                key, resp.model_dump(by_alias=True), ttl=settings.cache_ttl_seconds
            )

        offers = [o for r in resp.conteudo if (o := normalize_offer(r)) is not None]
        offers_by_item[item.label] = offers
        if offers:
            items_with_match += 1
        total_offers += len(offers)
        parsed_offers += sum(1 for o in offers if o.quantity_parsed)

    stores = build_store_results(
        item_queries=item_queries,
        offers_by_item=offers_by_item,
        origin=(lat, lon),
        top_n=settings.top_stores,
    )

    n = len(item_queries) or 1
    metrics = SearchMetrics(
        items_requested=len(item_queries),
        stores_found=len(stores),
        match_rate=round(items_with_match / n, 3),
        quantity_parse_rate=(
            round(parsed_offers / total_offers, 3) if total_offers else 0.0
        ),
    )

    # Persist the list under a UUID so it can be shared via a short link and
    # reused on identical searches. Never blocks the search if storage fails.
    list_id = await cache.save_search_list(req.items)

    return SearchResponse(
        origin=Origin(latitude=lat, longitude=lon),
        radius_km=radius,
        days=days,
        items_requested=len(item_queries),
        data_source=sefaz.source_name,
        list_id=list_id,
        stores=stores,
        metrics=metrics,
    )
