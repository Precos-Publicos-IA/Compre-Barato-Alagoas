"""Input-hardening regressions: geo bounds, item-length cap, consent policy match,
control-char sanitization, oversized secrets and non-ASCII admin tokens.

Covers issues #334, #369, #344, #198, #394, #329.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app

DEVICE = "a" * 32  # well-formed hex device token


def _client() -> TestClient:
    return TestClient(create_app())


# --- #334: latitude/longitude must be inside a loose Brazil box -----------------
@pytest.mark.parametrize(
    "lat,lon",
    [(40.0, -74.0), (-9.65, 10.0), (90.0, -35.7), (-9.65, -120.0)],
)
def test_search_rejects_off_region_coords(lat, lon):
    with _client() as c:
        r = c.post(
            "/api/v1/search",
            json={"items": ["arroz"], "latitude": lat, "longitude": lon},
        )
        assert r.status_code == 422, r.text


def test_search_accepts_alagoas_coords():
    with _client() as c:
        r = c.post(
            "/api/v1/search",
            json={"items": ["arroz"], "latitude": -9.65, "longitude": -35.71},
        )
        assert r.status_code == 200, r.text


# --- #369: each basket item is capped, oversized lines can't reach SEFAZ/LLM ----
def test_search_caps_item_length():
    with _client() as c:
        huge = "x" * 5000
        r = c.post("/api/v1/search", json={"items": [huge, "arroz"]})
        assert r.status_code == 200, r.text
        # The huge label is truncated to the 120-char cap before any downstream use.
        assert r.json()["items_requested"] == 2


# --- #344: consent must match the server's current policy version ---------------
def test_consent_rejects_stale_policy_version():
    with _client() as c:
        r = c.post(
            "/api/v1/device/consent",
            headers={"X-Device-Token": DEVICE},
            json={"accepted": True, "policy_version": "1999-01-01"},
        )
        assert r.status_code == 422, r.text


def test_consent_accepts_current_policy_version():
    current = get_settings().policy_version
    with _client() as c:
        r = c.post(
            "/api/v1/device/consent",
            headers={"X-Device-Token": DEVICE},
            json={"accepted": True, "policy_version": current},
        )
        assert r.status_code == 200, r.text
        assert r.json()["consented"] is True


# --- #198: control characters are stripped from feedback free text --------------
def test_feedback_strips_control_chars():
    with _client() as c:
        r = c.post(
            "/api/v1/feedback",
            json={"kind": "other", "note": "ok\x00\x07\x1bevil", "item": "ar\x00roz"},
        )
        assert r.status_code == 200, r.text


# --- #394: oversized secret body is rejected ------------------------------------
def test_secret_rejects_oversized_value(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "tok-0123456789abcdef")
    monkeypatch.setenv(
        "SECRET_ENCRYPTION_KEY", "0" * 43 + "="  # any urlsafe-b64 32B placeholder
    )
    get_settings.cache_clear()
    try:
        with _client() as c:
            r = c.put(
                "/admin/api/secrets/sefaz_app_token",
                headers={"Authorization": "Bearer tok-0123456789abcdef"},
                json={"value": "x" * 5000},
            )
            assert r.status_code == 422, r.text
    finally:
        get_settings.cache_clear()


# --- #329: a non-ASCII admin token reads as 401, never a 500 --------------------
def test_admin_non_ascii_token_is_401(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "tok-0123456789abcdef")
    get_settings.cache_clear()
    try:
        with _client() as c:
            # Raw high bytes: Starlette decodes them latin-1 into a non-ASCII str,
            # which would make hmac.compare_digest raise (500) without the guard.
            r = c.get(
                "/admin/api/overview",
                headers={"Authorization": b"Bearer \xff\xfe\x80token"},
            )
            assert r.status_code == 401, r.text
    finally:
        get_settings.cache_clear()
