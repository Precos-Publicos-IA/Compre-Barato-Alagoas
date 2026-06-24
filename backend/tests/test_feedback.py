from fastapi.testclient import TestClient

from app.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_feedback_recorded():
    with _client() as c:
        r = c.post(
            "/api/v1/feedback",
            json={"kind": "helpful", "helpful": True},
        )
        assert r.status_code == 200, r.text
        assert r.json()["recorded"] is True


def test_feedback_accepts_optional_device_and_analytics_headers():
    """Optional correlation headers must not 4xx; server stores fp/id only (#355)."""
    token = "a" * 64
    analytics = "b" * 40
    with _client() as c:
        r = c.post(
            "/api/v1/feedback",
            json={"kind": "helpful", "helpful": False, "list_id": "list-1"},
            headers={
                "X-Device-Token": token,
                "X-Analytics-Id": analytics,
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["recorded"] is True


def test_feedback_rejects_unknown_kind():
    with _client() as c:
        r = c.post("/api/v1/feedback", json={"kind": "bogus"})
        assert r.status_code == 422


def test_feedback_endpoint_is_rate_limited_like_search():
    """Unauthenticated feedback must share the daily IP rate limit (#137)."""
    import os

    from app.config import get_settings

    get_settings.cache_clear()
    old = os.environ.get("DAILY_SEARCH_LIMIT")
    os.environ["DAILY_SEARCH_LIMIT"] = "1"
    try:
        with _client() as c:
            r1 = c.post("/api/v1/feedback", json={"kind": "helpful", "helpful": True})
            assert r1.status_code == 200, r1.text
            r2 = c.post("/api/v1/feedback", json={"kind": "helpful", "helpful": False})
            assert r2.status_code == 429
            assert "limite" in r2.text.lower()
    finally:
        get_settings.cache_clear()
        if old is None:
            os.environ.pop("DAILY_SEARCH_LIMIT", None)
        else:
            os.environ["DAILY_SEARCH_LIMIT"] = old
