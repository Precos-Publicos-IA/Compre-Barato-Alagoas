from app.cache import Cache
from app.main import create_app
from app.api.deps import _ip_is_whitelisted
from app.config import Settings

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


def test_ip_whitelist_exact_and_cidr():
    # Use RFC 5737 documentation addresses only — never real lab/ops IPs in git.
    s = Settings(
        environment="production",
        ratelimit_whitelist_ips="203.0.113.50,10.0.0.0/8",
    )
    assert _ip_is_whitelisted("203.0.113.50", s)
    assert _ip_is_whitelisted("10.1.2.3", s)
    assert not _ip_is_whitelisted("8.8.8.8", s)


def test_dev_auto_whitelist_private_and_loopback():
    s = Settings(environment="development", ratelimit_whitelist_ips="")
    assert _ip_is_whitelisted("127.0.0.1", s)
    assert _ip_is_whitelisted("192.168.1.10", s)
    # Public IP not auto-whitelisted even in dev (must be listed).
    assert not _ip_is_whitelisted("8.8.8.8", s)


def test_prod_does_not_auto_whitelist_private():
    s = Settings(environment="production", ratelimit_whitelist_ips="")
    assert not _ip_is_whitelisted("192.168.1.10", s)
    assert not _ip_is_whitelisted("127.0.0.1", s)


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
    old_env = os.environ.get("ENVIRONMENT")
    old_wl = os.environ.get("RATELIMIT_WHITELIST_IPS")
    # Production-like so TestClient's  testclient host is not auto-private-skipped
    # unless we leave environment=development — force production + empty whitelist.
    os.environ["DAILY_SEARCH_LIMIT"] = "1"
    os.environ["ENVIRONMENT"] = "production"
    os.environ["RATELIMIT_WHITELIST_IPS"] = ""
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
        if old_env is None:
            os.environ.pop("ENVIRONMENT", None)
        else:
            os.environ["ENVIRONMENT"] = old_env
        if old_wl is None:
            os.environ.pop("RATELIMIT_WHITELIST_IPS", None)
        else:
            os.environ["RATELIMIT_WHITELIST_IPS"] = old_wl


def test_whitelisted_ip_skips_daily_limit():
    """Lab egress IP in RATELIMIT_WHITELIST_IPS is never 429'd."""
    import os

    from app.config import get_settings

    get_settings.cache_clear()
    old_lim = os.environ.get("DAILY_SEARCH_LIMIT")
    old_env = os.environ.get("ENVIRONMENT")
    old_wl = os.environ.get("RATELIMIT_WHITELIST_IPS")
    os.environ["DAILY_SEARCH_LIMIT"] = "1"
    os.environ["ENVIRONMENT"] = "production"
    # TestClient peer is typically "testclient" — whitelist that string won't
    # parse as IP; instead we inject X-Forwarded-For like nginx does in prod.
    os.environ["RATELIMIT_WHITELIST_IPS"] = "203.0.113.50"
    try:
        with TestClient(create_app()) as c:
            headers = {"X-Forwarded-For": "203.0.113.50"}
            for _ in range(5):
                r = c.get("/api/v1/lists/does-not-matter", headers=headers)
                assert r.status_code in (200, 404), r.text
    finally:
        get_settings.cache_clear()
        for key, old in (
            ("DAILY_SEARCH_LIMIT", old_lim),
            ("ENVIRONMENT", old_env),
            ("RATELIMIT_WHITELIST_IPS", old_wl),
        ):
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
