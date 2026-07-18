"""Aggregate per-item offers into ranked store baskets.

For each (store, requested item) we keep the **best-value** offer (preferred
package class first for staples, then lowest price per base unit, then fresher
sale, then lower package price), then rank stores:

1. more of the user's list available (``items_found`` desc);
2. then cheaper basket total asc;
3. then closer (distance) asc when coordinates exist.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..schemas.search import ItemOffer, StoreResult
from .geo import haversine_km
from .normalization.matcher import NormalizedOffer
from .rag.relevance import offer_package_class_rank


def _sale_age_days(sale_date: str | None) -> float:
    """Lower is fresher. Missing dates sort as older."""
    if not sale_date:
        return 9999.0
    raw = sale_date.strip()
    try:
        # Accept ISO date or datetime.
        if "T" in raw:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(raw[:10]).replace(tzinfo=timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0)
    except ValueError:
        return 9999.0


def _best_offer(
    offers: list[NormalizedOffer],
    query: str = "",
) -> NormalizedOffer:
    """Pick best offer: package class first (D1), then unit_price, freshness, pack R$.

    Cooking-size packs must beat 15 ml sachets even when package price is lower
    or unit_price is unparsed (per-package fallback).
    """
    return min(
        offers,
        key=lambda o: (
            offer_package_class_rank(query, query, o),
            o.unit_price,
            _sale_age_days(o.sale_date),
            o.price,
        ),
    )


def _package_label(offer: NormalizedOffer) -> str | None:
    if not offer.quantity_parsed:
        return None
    q = offer.quantity
    u = (offer.unit or offer.base_unit or "").strip()
    if not u:
        return None
    # Nice display: 1 -> "1 kg", 0.35 -> "0.35 L"
    if abs(q - round(q)) < 1e-6:
        qs = str(int(round(q)))
    else:
        qs = f"{q:.2f}".rstrip("0").rstrip(".")
    return f"{qs} {u}"


def _rank_reason(store: StoreResult, best_total: float | None) -> str:
    n, t = store.items_found, store.items_total
    if n >= t and t > 0:
        if best_total is not None and abs(store.total - best_total) < 0.009:
            return f"Mais barato com {n}/{t} itens"
        return f"Tem tudo da lista ({n}/{t})"
    if n == 0:
        return "Nenhum item encontrado"
    missing = len(store.missing)
    if missing == 1:
        return f"Falta {store.missing[0]} · {n}/{t} itens"
    return f"Faltam {missing} itens · {n}/{t} na lista"


def build_store_results(
    item_queries: list[str],
    offers_by_item: dict[str, list[NormalizedOffer]],
    origin: tuple[float, float] | None,
    top_n: int,
    excluded_cnpjs: set[str] | None = None,
    quantities: dict[str, int] | None = None,
    favorite_cnpjs: set[str] | None = None,
) -> list[StoreResult]:
    excluded = excluded_cnpjs or set()
    favorites = favorite_cnpjs or set()
    qtys = quantities or {}
    by_store: dict[str, dict[str, NormalizedOffer]] = {}
    store_meta: dict[str, NormalizedOffer] = {}

    for query in item_queries:
        per_store: dict[str, list[NormalizedOffer]] = {}
        for offer in offers_by_item.get(query, []):
            if offer.cnpj in excluded:
                continue
            per_store.setdefault(offer.cnpj, []).append(offer)
        for cnpj, offers in per_store.items():
            best = _best_offer(offers, query)
            by_store.setdefault(cnpj, {})[query] = best
            store_meta.setdefault(cnpj, best)

    results: list[StoreResult] = []
    for cnpj, item_map in by_store.items():
        meta = store_meta[cnpj]
        distance = None
        # Only expose distance when both ends have coordinates (web scrape often null).
        if (
            origin
            and meta.latitude is not None
            and meta.longitude is not None
        ):
            distance = round(
                haversine_km(origin[0], origin[1], meta.latitude, meta.longitude), 2
            )

        item_offers: list[ItemOffer] = []
        total = 0.0
        for query in item_queries:
            offer = item_map.get(query)
            if offer is None:
                continue
            qty = max(1, qtys.get(query, 1))
            line_total = round(offer.price * qty, 2)
            total += line_total
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
                    requested_quantity=qty,
                    line_total=line_total,
                    package_label=_package_label(offer),
                    is_best_match=True,
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
                is_favorite=cnpj in favorites,
            )
        )

    # Favorites get a soft boost only when coverage is equal (habit > tiny price).
    results.sort(
        key=lambda s: (
            -s.items_found,
            0 if s.is_favorite else 1,
            s.total,
            s.distance_km if s.distance_km is not None else float("inf"),
        )
    )
    trimmed = results[:top_n]
    best_total = trimmed[0].total if trimmed else None
    for s in trimmed:
        s.rank_reason = _rank_reason(s, best_total)
    return trimmed
