"""Aggregate per-item offers into ranked store baskets.

For each (store, requested item) we keep the **best-value** offer (lowest price per
base unit), then rank stores so the most useful one is first:

1. more of the user's list available (``items_found`` desc) — a cheap store missing
   half your list isn't actually helpful;
2. then cheaper basket total (sum of package prices) asc;
3. then closer (distance) asc.
"""

from __future__ import annotations

from ..schemas.search import ItemOffer, StoreResult
from .geo import haversine_km
from .normalization.matcher import NormalizedOffer


def _best_offer(offers: list[NormalizedOffer]) -> NormalizedOffer:
    # Best value first; tie-break on lower package price.
    return min(offers, key=lambda o: (o.unit_price, o.price))


def build_store_results(
    item_queries: list[str],
    offers_by_item: dict[str, list[NormalizedOffer]],
    origin: tuple[float, float] | None,
    top_n: int,
    excluded_cnpjs: set[str] | None = None,
) -> list[StoreResult]:
    excluded = excluded_cnpjs or set()
    # store cnpj -> {item_query -> best offer at that store}
    by_store: dict[str, dict[str, NormalizedOffer]] = {}
    store_meta: dict[str, NormalizedOffer] = {}

    for query in item_queries:
        # group this item's offers by store, keep best per store. Drop hidden stores
        # here — *before* ranking/truncation — so they free their slot for a real result.
        per_store: dict[str, list[NormalizedOffer]] = {}
        for offer in offers_by_item.get(query, []):
            if offer.cnpj in excluded:
                continue
            per_store.setdefault(offer.cnpj, []).append(offer)
        for cnpj, offers in per_store.items():
            best = _best_offer(offers)
            by_store.setdefault(cnpj, {})[query] = best
            store_meta.setdefault(cnpj, best)

    results: list[StoreResult] = []
    for cnpj, item_map in by_store.items():
        meta = store_meta[cnpj]
        distance = None
        if origin and meta.latitude is not None and meta.longitude is not None:
            distance = round(
                haversine_km(origin[0], origin[1], meta.latitude, meta.longitude), 2
            )

        item_offers: list[ItemOffer] = []
        total = 0.0
        for query in item_queries:
            offer = item_map.get(query)
            if offer is None:
                continue
            total += offer.price
            item_offers.append(
                ItemOffer(
                    query=query,
                    found=True,
                    description=offer.description,
                    gtin=offer.gtin,
                    price=offer.price,
                    unit_price=offer.unit_price,
                    base_unit=offer.base_unit,
                    quantity=offer.quantity,
                    unit=offer.unit,
                    unidade_medida=offer.unidade_medida,
                    sale_date=offer.sale_date,
                    quantity_parsed=offer.quantity_parsed,
                )
            )

        missing = [q for q in item_queries if q not in item_map]
        results.append(
            StoreResult(
                cnpj=cnpj,
                name=meta.store_name,
                latitude=meta.latitude,
                longitude=meta.longitude,
                address=meta.address,
                bairro=meta.bairro,
                distance_km=distance,
                items_found=len(item_offers),
                items_total=len(item_queries),
                total=round(total, 2),
                items=item_offers,
                missing=missing,
            )
        )

    results.sort(
        key=lambda s: (
            -s.items_found,
            s.total,
            s.distance_km if s.distance_km is not None else float("inf"),
        )
    )
    return results[:top_n]
