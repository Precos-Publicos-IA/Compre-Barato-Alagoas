"""App-level hardening: scoped CORS, trusted hosts, trimmed /health and a
configurable rate-limit salt. Covers issues #317, #150, #364, #421.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


# --- #364: production /health returns only status, no runtime-config recon ------
def test_health_trims_config_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()
    try:
        with _client() as c:
            body = c.get("/health").json()
            assert body == {"status": "ok"}
    finally:
        get_settings.cache_clear()


def test_health_verbose_outside_production():
    get_settings.cache_clear()
    with _client() as c:
        body = c.get("/health").json()
        assert body["status"] == "ok"
        assert "data_source" in body and "use_mock_llm" in body


# --- #317: restricted CORS advertises explicit methods/headers, not "*" ---------
def test_cors_scoped_when_origins_restricted(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://alagoas.example.br")
    get_settings.cache_clear()
    try:
        with _client() as c:
            r = c.options(
                "/api/v1/search",
                headers={
                    "Origin": "https://alagoas.example.br",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
            )
            allow = r.headers.get("access-control-allow-methods", "")
            assert "*" not in allow
            assert "POST" in allow
    finally:
        get_settings.cache_clear()


# --- #150: TrustedHostMiddleware rejects an unexpected Host when pinned ----------
def test_trusted_host_rejects_unknown_host(monkeypatch):
    monkeypatch.setenv("ALLOWED_HOSTS", "alagoas.example.br")
    get_settings.cache_clear()
    try:
        with _client() as c:
            ok = c.get("/health", headers={"Host": "alagoas.example.br"})
            assert ok.status_code == 200
            bad = c.get("/health", headers={"Host": "evil.example.com"})
            assert bad.status_code == 400
    finally:
        get_settings.cache_clear()


def test_trusted_host_disabled_by_default():
    get_settings.cache_clear()
    with _client() as c:
        assert c.get("/health", headers={"Host": "anything.example"}).status_code == 200


# --- #421: rate-limit salt is configurable and changes the bucket hash ----------
def test_ratelimit_salt_is_configurable():
    from app.api import deps

    # Direct hash check: different salts must yield different bucket ids.
    class _Req:
        headers = {"x-forwarded-for": "203.0.113.9"}
        client = None

    h1 = deps._client_id(_Req(), "salt-one")
    h2 = deps._client_id(_Req(), "salt-two")
    assert h1 != h2 and len(h1) == 32
