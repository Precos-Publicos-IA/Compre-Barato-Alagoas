import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app

TOKEN = "test-admin-token-0123456789"


@pytest.fixture
def admin_env(monkeypatch):
    """Configure an admin token and reset the cached settings around the test."""
    monkeypatch.setenv("ADMIN_TOKEN", TOKEN)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_admin_requires_token():
    # No ADMIN_TOKEN configured (default) → fail closed even without a header.
    get_settings.cache_clear()
    with TestClient(create_app()) as c:
        assert c.get("/admin/api/overview").status_code == 401
    get_settings.cache_clear()


def test_admin_rejects_wrong_token(admin_env):
    with TestClient(create_app()) as c:
        r = c.get("/admin/api/overview", headers={"Authorization": "Bearer nope"})
        assert r.status_code == 401


def test_admin_overview_with_token(admin_env):
    with TestClient(create_app()) as c:
        # Generate some data first.
        c.post("/api/v1/search", json={"items": ["arroz", "leite"]})
        r = c.get("/admin/api/overview", headers={"Authorization": f"Bearer {TOKEN}"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total_searches"] >= 1
        assert body["use_mock_llm"] is True
        assert "total_llm_cost_usd" in body


def test_admin_endpoints_smoke(admin_env):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    with TestClient(create_app()) as c:
        c.post("/api/v1/search", json={"items": ["café"]})
        c.post("/api/v1/feedback", json={"kind": "helpful", "helpful": True})
        for path in ("/admin/api/quality", "/admin/api/costs",
                     "/admin/api/searches", "/admin/api/items",
                     "/admin/api/feedback", "/admin/api/timings",
                     "/admin/api/providers"):
            assert c.get(path, headers=headers).status_code == 200, path


def test_admin_timings_and_providers_populated(admin_env):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    with TestClient(create_app()) as c:
        c.post("/api/v1/search", json={"items": ["arroz", "leite"]})
        t = c.get("/admin/api/timings", headers=headers).json()
        stages = {s["stage"] for s in t["stages"]}
        assert {"total", "llm", "sefaz", "cache", "normalize", "rank"} <= stages
        total = next(s for s in t["stages"] if s["stage"] == "total")
        assert total["count"] >= 1
        p = c.get("/admin/api/providers", headers=headers).json()
        names = {x["name"] for x in p["providers"]}
        # Mock mode still records provider calls (badged mock in the UI).
        assert {"sefaz", "llm"} <= names
        assert p["use_mock_llm"] is True
