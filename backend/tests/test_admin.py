import json

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


def test_admin_brute_force_is_throttled(admin_env):
    # Repeated wrong tokens from one client lock out with 429 after the threshold (#163).
    with TestClient(create_app()) as c:
        codes = [
            c.get(
                "/admin/api/overview", headers={"Authorization": "Bearer nope"}
            ).status_code
            for _ in range(12)
        ]
        assert codes[0] == 401
        assert 429 in codes
        # A valid token still works (and clears the counter), so the operator isn't locked out.
        assert (
            c.get(
                "/admin/api/overview", headers={"Authorization": f"Bearer {TOKEN}"}
            ).status_code
            == 200
        )


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
        for path in ("/admin/api/growth", "/admin/api/quality", "/admin/api/costs",
                     "/admin/api/searches", "/admin/api/items",
                     "/admin/api/feedback", "/admin/api/timings",
                     "/admin/api/providers"):
            assert c.get(path, headers=headers).status_code == 200, path


def test_admin_growth_counts_anonymous_id(admin_env):
    """The always-sent X-Analytics-Id (independent of cloud-sync) drives DAU."""
    headers = {"Authorization": f"Bearer {TOKEN}"}
    with TestClient(create_app()) as c:
        c.post("/api/v1/search", json={"items": ["arroz"]},
               headers={"X-Analytics-Id": "b" * 40})
        g = c.get("/admin/api/growth", headers=headers).json()
        assert g["dau_today"] >= 1
        assert len(g["dau"]) == len(g["days"])
        assert len(g["hours"]) == 24 and len(g["weekday"]) == 7


def test_search_event_stream_omits_id_and_cnpjs(admin_env):
    """Privacy: the analytics id and excluded CNPJs must never land in any per-event
    row (the id only ever feeds the aggregate HLL; CNPJs are ephemeral filters)."""
    headers = {"Authorization": f"Bearer {TOKEN}"}
    with TestClient(create_app()) as c:
        c.post("/api/v1/search",
               json={"items": ["arroz"], "excluded_cnpjs": ["12345678000199"]},
               headers={"X-Analytics-Id": "c" * 40})
        blob = json.dumps(c.get("/admin/api/searches", headers=headers).json())
        assert "c" * 40 not in blob
        assert "12345678000199" not in blob


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
