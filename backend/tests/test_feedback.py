import inspect

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.feedback import FeedbackRequest
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


# --- Phase 6: wrong_item query + description wire-through (6-S1…6-S6) ---------


def test_s1_schema_accepts_query_and_description():
    """6-S1: FeedbackRequest validates query + description fields."""
    body = FeedbackRequest(
        kind="wrong_item",
        query="arroz",
        description="FEIJAO PRETO TIPO 1 1KG",
    )
    assert body.resolved_query() == "arroz"
    assert body.resolved_description() == "FEIJAO PRETO TIPO 1 1KG"
    # Legacy item/note still resolve
    legacy = FeedbackRequest(kind="wrong_item", item="pao", note="PAO DOCE")
    assert legacy.resolved_query() == "pao"
    assert legacy.resolved_description() == "PAO DOCE"
    # query preferred over item; description preferred over note
    both = FeedbackRequest(
        kind="wrong_item",
        item="legacy",
        query="preferido",
        note="nota livre",
        description="PRODUTO ERRADO",
    )
    assert both.resolved_query() == "preferido"
    assert both.resolved_description() == "PRODUTO ERRADO"


def test_s1_wrong_item_accepts_query_and_description_via_api():
    """6-S1: TestClient POST with query + description → 200 recorded."""
    with _client() as c:
        r = c.post(
            "/api/v1/feedback",
            json={
                "kind": "wrong_item",
                "query": "arroz",
                "description": "FEIJAO PRETO TIPO 1 1KG",
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["recorded"] is True


def test_s2_handler_invokes_on_user_feedback_with_query_description(monkeypatch):
    """6-S2: route calls learn_policy.on_user_feedback when fields present."""
    calls: list[dict] = []

    async def _spy(rag, **kwargs):
        calls.append(kwargs)
        from app.services.rag.learn_policy import LearnResult

        return LearnResult("demote", "wrong_item")

    monkeypatch.setattr(
        "app.api.routes.feedback.on_user_feedback",
        _spy,
    )
    with _client() as c:
        r = c.post(
            "/api/v1/feedback",
            json={
                "kind": "wrong_item",
                "query": "leite",
                "description": "SUCO DE UVA 1L",
                "list_id": "list-xyz",
            },
        )
        assert r.status_code == 200, r.text
    assert len(calls) == 1
    assert calls[0]["kind"] == "wrong_item"
    assert calls[0]["query"] == "leite"
    assert calls[0]["description"] == "SUCO DE UVA 1L"
    assert calls[0]["list_id"] == "list-xyz"
    assert "device_token" not in calls[0]


@pytest.mark.asyncio
async def test_wrong_item_feedback_demotes_rag_mapping(monkeypatch):
    """Phase 3 / 6-S4 (legacy item+note): wrong_item demotes via learn_policy."""
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


@pytest.mark.asyncio
async def test_s4_wrong_item_query_description_demotes_mapping(monkeypatch):
    """6-S4: seed RAG success → POST wrong_item(query,description) → demoted."""
    monkeypatch.delenv("MATCH_LEARN", raising=False)
    with _client() as c:
        rag = RAGStore(redis=c.app.state.cache.redis)
        seed = await on_search_item_result(
            rag,
            user_term="arroz",
            effective_search_term="arroz tipo 1",
            offers_found=4,
            fetch_failed=False,
            score=0.9,
            best_description="ARROZ TIPO 1 5KG",
            package_class_ok=True,
        )
        assert seed.action == "success"
        assert await rag.lookup_effective_terms("arroz", limit=1)

        r = c.post(
            "/api/v1/feedback",
            json={
                "kind": "wrong_item",
                "query": "arroz",
                "description": "FEIJAO CARIOCA 1KG",
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["recorded"] is True
        assert await rag.lookup_effective_terms("arroz", limit=3) == []
        miss = await rag.redis.zscore("rag:miss:arroz", "arroz tipo 1")
        assert miss is not None and float(miss) >= 1.0


def test_s5_feedback_200_when_learn_raises(monkeypatch):
    """6-S5: learn Redis / policy failure must not 500; feedback still ACK'd."""

    async def _boom(*_a, **_k):
        raise RuntimeError("redis learn down")

    monkeypatch.setattr("app.api.routes.feedback.on_user_feedback", _boom)
    with _client() as c:
        r = c.post(
            "/api/v1/feedback",
            json={
                "kind": "wrong_item",
                "query": "cafe",
                "description": "CHA MATE 250G",
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["recorded"] is True


def test_s5_feedback_200_when_rag_store_raises(monkeypatch):
    """6-S5: redis failure inside learn path still 200 (best-effort)."""
    from app.api.routes import feedback as fb_mod

    async def _learn_raises(rag, **kwargs):
        raise ConnectionError("redis demote failed")

    monkeypatch.setattr(fb_mod, "on_user_feedback", _learn_raises)
    with _client() as c:
        r = c.post(
            "/api/v1/feedback",
            json={"kind": "wrong_item", "query": "acucar", "description": "SAL"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["recorded"] is True


def test_s6_device_token_not_passed_to_learn_or_outcome():
    """6-S6: feedback route discards device_token; no outcome-log write here."""
    from app.api.routes import feedback as fb_mod

    src = inspect.getsource(fb_mod)
    assert "del device_token" in src
    assert "on_user_feedback" in src
    # Must not forward token into learn kwargs or analytics feedback stream.
    assert "device_token=" not in src.split("on_user_feedback")[1].split(")")[0]
    assert "outcome_log" not in src
    assert "append_outcome" not in src
    assert "log_search_item" not in src
