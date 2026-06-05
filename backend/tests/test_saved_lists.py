import pytest
from fastapi.testclient import TestClient

from app.cache import Cache
from app.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_search_returns_list_id_resolvable_to_items():
    with _client() as c:
        body = c.post("/api/v1/search", json={"items": ["arroz", "leite"]}).json()
        list_id = body["list_id"]
        assert list_id, "search should return a shareable list_id"

        resolved = c.get(f"/api/v1/lists/{list_id}")
        assert resolved.status_code == 200, resolved.text
        assert resolved.json()["items"] == ["arroz", "leite"]


def test_identical_lists_reuse_same_id():
    with _client() as c:
        a = c.post("/api/v1/search", json={"items": ["Arroz", "Leite"]}).json()
        b = c.post("/api/v1/search", json={"items": ["arroz", "leite"]}).json()
        # Same items (case-insensitive) dedupe to the same UUID.
        assert a["list_id"] == b["list_id"]


def test_unknown_list_id_404():
    with _client() as c:
        r = c.get("/api/v1/lists/does-not-exist")
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_cache_save_and_get_roundtrip_memory():
    cache = Cache(redis_url="")  # in-memory backend
    list_id = await cache.save_search_list(["  Pão ", "café", ""])
    assert list_id
    assert await cache.get_search_list(list_id) == ["Pão", "café"]
    assert await cache.get_search_list("missing") is None
    # Empty list isn't stored.
    assert await cache.save_search_list(["  ", ""]) is None
