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
async def test_cache_save_and_get_roundtrip():
    cache = Cache(redis_url="redis://test")
    list_id = await cache.save_search_list(["  Pão ", "café", ""])
    assert list_id
    assert await cache.get_search_list(list_id) == ["Pão", "café"]
    assert await cache.get_search_list("missing") is None
    # Empty list isn't stored.
    assert await cache.save_search_list(["  ", ""]) is None


@pytest.mark.asyncio
async def test_get_search_list_refreshes_hash_ttl_for_dedup():
    """Probe for the hash-key refresh on get (prevents dedup breakage when
    share links are opened repeatedly without new saves)."""
    cache = Cache(redis_url="redis://test")
    # First search creates the list + listhash pointer.
    id1 = await cache.save_search_list(["arroz", "leite"])
    assert id1
    # Simulate a share-link open: get the list (should refresh both list and hash).
    got = await cache.get_search_list(id1)
    assert got == ["arroz", "leite"]
    # A semantically identical (case/padding diff) search must still reuse the id
    # because the hash pointer was kept alive by the get.
    id2 = await cache.save_search_list(["  Arroz", "LEITE"])
    assert id2 == id1
