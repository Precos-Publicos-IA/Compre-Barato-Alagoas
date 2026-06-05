from app.cache import Cache


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
