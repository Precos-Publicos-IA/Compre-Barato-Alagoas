from app.cache import Cache
from app.main import create_app

from fastapi.testclient import TestClient

import pytest


@pytest.mark.asyncio
async def test_rate_limit_counter():
    cache = Cache(redis_url="redis://test", default_ttl=60)
    counts = [await cache.incr_with_ttl("k", ttl=60) for _ in range(3)]
    assert counts == [1, 2, 3]


@pytest.mark.asyncio
async def test_json_roundtrip():
    cache = Cache(redis_url="redis://test", default_ttl=60)
    await cache.set_json("x", {"a": 1})
    assert await cache.get_json("x") == {"a": 1}
    assert await cache.get_json("missing") is None


def test_lists_endpoint_is_rate_limited_like_search():
    """Probe: the share-link GET /lists/{id} now has the same rate limit dep.
    A client that exhausts the daily quota is rejected on list opens too
    (prevents unbounded load from distributed share links)."""
    # Force a very low limit for this test process by clearing the settings cache
    # and setting the env var before the app reads it.
    import os

    from app.config import get_settings

    get_settings.cache_clear()
    old = os.environ.get("DAILY_SEARCH_LIMIT")
    os.environ["DAILY_SEARCH_LIMIT"] = "1"
    try:
        with TestClient(create_app()) as c:
            # First list open should succeed (and consume the 1 allowed).
            # We don't need a real list id; 404 is fine, the dep runs before handler.
            r1 = c.get("/api/v1/lists/does-not-matter")
            # Either 404 (no such list) or 200 if by chance, but not 429 yet.
            assert r1.status_code in (200, 404)

            # Second request from same client id (IP hash) must be limited.
            r2 = c.get("/api/v1/lists/does-not-matter-2")
            assert r2.status_code == 429
            assert "limite diário" in r2.text.lower() or "limite" in r2.text.lower()
    finally:
        get_settings.cache_clear()
        if old is None:
            os.environ.pop("DAILY_SEARCH_LIMIT", None)
        else:
            os.environ["DAILY_SEARCH_LIMIT"] = old
