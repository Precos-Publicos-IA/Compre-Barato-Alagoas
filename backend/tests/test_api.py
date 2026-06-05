from fastapi.testclient import TestClient

from app.main import create_app


def _client() -> TestClient:
    # Context-managed so FastAPI lifespan (client wiring) runs.
    return TestClient(create_app())


def test_health():
    with _client() as c:
        r = c.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["data_source"] == "mock"
        assert body["use_mock_sefaz"] is True


def test_suggestions():
    with _client() as c:
        r = c.get("/api/v1/suggestions")
        assert r.status_code == 200
        labels = [i["label"] for i in r.json()["items"]]
        assert "Arroz" in labels and "Leite" in labels


def test_search_basic_basket():
    with _client() as c:
        r = c.post(
            "/api/v1/search",
            json={"items": ["arroz", "leite", "feijão"]},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["data_source"] == "mock"
        assert body["items_requested"] == 3
        assert body["stores"], "expected at least one store"

        top = body["stores"][0]
        assert top["items_found"] >= 1
        assert top["total"] > 0
        # Every found item exposes a fair per-base unit price.
        for item in top["items"]:
            assert item["found"] is True
            assert item["unit_price"] is not None
            assert item["base_unit"] in {"kg", "L", "un"}

        # Stores are sorted by items_found desc.
        found_counts = [s["items_found"] for s in body["stores"]]
        assert found_counts == sorted(found_counts, reverse=True)

        assert 0.0 <= body["metrics"]["match_rate"] <= 1.0
        assert 0.0 <= body["metrics"]["quantity_parse_rate"] <= 1.0


def test_search_radius_excludes_far_stores():
    # Every returned store must lie within the requested radius, and a tighter radius
    # must not return more stores than a wide one.
    with _client() as c:
        wide = c.post(
            "/api/v1/search",
            json={"items": ["arroz"], "radius_km": 15},
        ).json()
        narrow = c.post(
            "/api/v1/search",
            json={"items": ["arroz"], "radius_km": 2},
        ).json()
    for store in narrow["stores"]:
        assert store["distance_km"] is not None and store["distance_km"] <= 2.0
    assert len(narrow["stores"]) <= len(wide["stores"])


def test_search_validation_empty_items():
    with _client() as c:
        r = c.post("/api/v1/search", json={"items": []})
        assert r.status_code == 422


def test_search_caches_second_call():
    with _client() as c:
        first = c.post("/api/v1/search", json={"items": ["café"]})
        second = c.post("/api/v1/search", json={"items": ["café"]})
        assert first.status_code == second.status_code == 200
        # Same deterministic result from cache.
        assert first.json()["stores"] == second.json()["stores"]
