"""Schema contract guard between the backend search response and the Flutter app.

The frontend parses fixed JSON keys in lib/data/models.dart (fromJson). If the
backend ever renames/drops one of them the app silently breaks, so freeze the keys
the client depends on here and fail loudly on drift (#159).

Keep in sync with frontend/lib/data/models.dart.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app

# Keys read by each *.fromJson in frontend/lib/data/models.dart.
_RESPONSE_KEYS = {
    "origin", "radius_km", "days", "items_requested", "data_source",
    "list_id", "stores", "metrics",
}
_ORIGIN_KEYS = {"latitude", "longitude"}
_STORE_KEYS = {
    "cnpj", "name", "latitude", "longitude", "address", "bairro",
    "distance_km", "items_found", "items_total", "total", "items", "missing",
}
_ITEM_KEYS = {
    "query", "found", "description", "base_unit", "price", "unit_price",
    "quantity", "unit", "sale_date", "quantity_parsed", "requested_quantity",
    "line_total",
}
_METRICS_KEYS = {
    "items_requested", "stores_found", "match_rate", "quantity_parse_rate",
}


def test_search_response_matches_frontend_contract():
    with TestClient(create_app()) as c:
        body = c.post("/api/v1/search", json={"items": ["arroz", "leite"]}).json()

    def missing(required, actual, where):
        gap = required - set(actual)
        assert not gap, f"{where} missing keys the frontend reads: {sorted(gap)}"

    missing(_RESPONSE_KEYS, body, "SearchResponse")
    missing(_ORIGIN_KEYS, body["origin"], "Origin")
    missing(_METRICS_KEYS, body["metrics"], "SearchMetrics")
    assert body["stores"], "need at least one store to validate the store/item contract"
    store = body["stores"][0]
    missing(_STORE_KEYS, store, "StoreResult")
    assert store["items"], "need at least one item offer to validate the contract"
    missing(_ITEM_KEYS, store["items"][0], "ItemOffer")
