"""Interactive OpenAPI UI is off in production; on by default in development."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


def _fresh_app(monkeypatch, **env: str):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    return create_app()


def test_docs_enabled_in_development(monkeypatch):
    app = _fresh_app(monkeypatch, ENVIRONMENT="development")
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/redoc").status_code == 200
        assert client.get("/openapi.json").status_code == 200


def test_docs_disabled_in_production(monkeypatch):
    app = _fresh_app(monkeypatch, ENVIRONMENT="production")
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        # Application API remains reachable (security is auth/limits, not obscurity).
        assert client.get("/health").status_code == 200


def test_expose_api_docs_override_on_in_production(monkeypatch):
    app = _fresh_app(
        monkeypatch, ENVIRONMENT="production", EXPOSE_API_DOCS="true"
    )
    with TestClient(app) as client:
        assert client.get("/openapi.json").status_code == 200


def test_expose_api_docs_override_off_in_development(monkeypatch):
    app = _fresh_app(
        monkeypatch, ENVIRONMENT="development", EXPOSE_API_DOCS="false"
    )
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
