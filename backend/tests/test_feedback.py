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


def test_feedback_rejects_unknown_kind():
    with _client() as c:
        r = c.post("/api/v1/feedback", json={"kind": "bogus"})
        assert r.status_code == 422
