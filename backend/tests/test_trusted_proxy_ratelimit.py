"""Trusted-proxy / X-Forwarded-For behaviour for rate limiting (#264)."""

from __future__ import annotations

import os

from app.api.deps import _client_ip_for_rate_limit
from app.config import Settings, get_settings
from app.main import create_app

from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.datastructures import Headers


def _make_request(peer: str, headers: dict[str, str] | None = None) -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": Headers(headers or {}).raw,
        "client": (peer, 12345),
        "server": ("test", 80),
    }
    return Request(scope)


def test_xff_ignored_from_untrusted_peer():
    settings = Settings(trusted_proxy_ips="127.0.0.1,::1")
    req = _make_request("203.0.113.9", {"x-forwarded-for": "1.2.3.4"})
    assert _client_ip_for_rate_limit(req, settings) == "203.0.113.9"


def test_xff_honoured_from_trusted_peer():
    settings = Settings(trusted_proxy_ips="127.0.0.1,::1")
    req = _make_request("127.0.0.1", {"x-forwarded-for": "198.51.100.7, 10.0.0.1"})
    assert _client_ip_for_rate_limit(req, settings) == "198.51.100.7"


def test_client_config_endpoint_public():
    get_settings.cache_clear()
    old_min = os.environ.get("MIN_APP_VERSION")
    os.environ["MIN_APP_VERSION"] = "1.2.3"
    try:
        get_settings.cache_clear()
        with TestClient(create_app()) as c:
            r = c.get("/api/v1/client-config")
            assert r.status_code == 200
            body = r.json()
            assert body["min_app_version"] == "1.2.3"
            assert body["force_update"] is True
            assert "policy_version" in body
    finally:
        get_settings.cache_clear()
        if old_min is None:
            os.environ.pop("MIN_APP_VERSION", None)
        else:
            os.environ["MIN_APP_VERSION"] = old_min
        get_settings.cache_clear()


def test_sentry_scrub_filters_authorization():
    from app.main import _sentry_scrub_event

    event = {
        "request": {
            "headers": {"Authorization": "Bearer secret", "X-Request-ID": "abc"},
            "data": {"items": ["leite", "pao"], "note": "x" * 20},
        }
    }
    out = _sentry_scrub_event(event, {})
    assert out["request"]["headers"]["Authorization"] == "[Filtered]"
    assert out["request"]["headers"]["X-Request-ID"] == "abc"
    assert out["request"]["data"]["items"] == "[Filtered]"
