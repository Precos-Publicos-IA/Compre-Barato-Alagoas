import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.rag.learn_policy import on_search_item_result
from app.services.rag.store import RAGStore


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


@pytest.mark.asyncio
async def test_wrong_item_feedback_demotes_rag_mapping(monkeypatch):
    """Phase 3: wrong_item on /feedback demotes via learn_policy (not analytics-only)."""
    monkeypatch.delenv("MATCH_LEARN", raising=False)
    with _client() as c:
        rag = RAGStore(redis=c.app.state.cache.redis)
        seed = await on_search_item_result(
            rag,
            user_term="pao",
            effective_search_term="pao frances",
            offers_found=5,
            fetch_failed=False,
            score=0.85,
            best_description="PAO FRANCES UN",
            package_class_ok=True,
        )
        assert seed.action == "success"
        assert await rag.lookup_effective_terms("pao", limit=1)

        r = c.post(
            "/api/v1/feedback",
            json={
                "kind": "wrong_item",
                "item": "pao",
                "note": "PAO DOCE",
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["recorded"] is True
        # Item-only feedback clears all learned rewrites for that query.
        assert await rag.lookup_effective_terms("pao", limit=3) == []
        miss = await rag.redis.zscore("rag:miss:pao", "pao frances")
        assert miss is not None and float(miss) >= 1.0
