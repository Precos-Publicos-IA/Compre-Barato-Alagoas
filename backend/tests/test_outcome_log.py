"""Unit + API tests for match outcome log (Phase 1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.rag.intent import MATCH_RULES_VERSION
from app.services.rag.outcome_log import (
    ENV_LOG_PATH,
    ENV_LOG_SAMPLE,
    append_outcome,
    build_item_outcome,
    is_enabled,
    log_search_item_outcomes,
    outcome_log_path,
    outcome_log_sample_rate,
    should_sample,
)


REQUIRED_KEYS = {
    "ts",
    "match_rules_version",
    "query",
    "items_fetch_failed",
    "top_descriptions",
    "stores_found",
}


def test_match_rules_version_stable_nonempty():
    assert isinstance(MATCH_RULES_VERSION, str)
    assert MATCH_RULES_VERSION.strip()
    assert MATCH_RULES_VERSION == "2026-07-23-head-v1"


def test_build_item_outcome_schema_minimum():
    row = build_item_outcome(
        query="peito de frango",
        search_term="peito frango",
        top_descriptions=["SOPA VONO PEITO FRANGO C QUEIJO 17G"],
        top_scores=[0.42],
        items_fetch_failed=False,
        stores_found=5,
        data_source="mock",
        latency_ms=1234,
    )
    for k in REQUIRED_KEYS:
        assert k in row, f"missing {k}"
    assert row["match_rules_version"] == MATCH_RULES_VERSION
    assert row["query"] == "peito de frango"
    assert row["items_fetch_failed"] is False
    assert isinstance(row["top_descriptions"], list)
    assert row["stores_found"] == 5
    assert "device_token" not in row
    assert "Authorization" not in row


def test_build_strips_forbidden_keys_if_smuggled():
    # build_item_outcome never accepts device_token; sanitize still guards append.
    row = build_item_outcome(query="arroz", stores_found=1)
    dirty = {**row, "device_token": "secret-token-value", "Authorization": "Bearer x"}
    written = append_outcome(dirty, path="")  # disabled path
    assert written is False


def test_append_and_noop(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_LOG_PATH, raising=False)
    assert is_enabled() is False
    assert outcome_log_path() is None
    assert append_outcome(build_item_outcome(query="x")) is False

    path = tmp_path / "outcomes.jsonl"
    monkeypatch.setenv(ENV_LOG_PATH, str(path))
    monkeypatch.setenv(ENV_LOG_SAMPLE, "1.0")
    assert is_enabled() is True

    row = build_item_outcome(
        query="arroz",
        top_descriptions=["ARROZ TIPO 1 5KG"],
        stores_found=3,
        items_fetch_failed=False,
    )
    assert append_outcome(row) is True
    assert path.exists()
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    for k in REQUIRED_KEYS:
        assert k in parsed
    assert "device_token" not in parsed
    blob = lines[0].lower()
    assert "device_token" not in blob
    assert "authorization" not in blob
    assert "sefaz_app_token" not in blob


def test_sample_rate_zero_writes_nothing(tmp_path, monkeypatch):
    path = tmp_path / "out.jsonl"
    monkeypatch.setenv(ENV_LOG_PATH, str(path))
    monkeypatch.setenv(ENV_LOG_SAMPLE, "0.0")
    assert outcome_log_sample_rate() == 0.0
    assert should_sample() is False
    n = log_search_item_outcomes(
        items=["arroz", "feijão", "leite"],
        offers_by_item={},
        stores_found=0,
    )
    assert n == 0
    assert not path.exists()


def test_log_search_item_outcomes_one_line_per_item(tmp_path, monkeypatch):
    path = tmp_path / "out.jsonl"
    monkeypatch.setenv(ENV_LOG_PATH, str(path))
    monkeypatch.setenv(ENV_LOG_SAMPLE, "1.0")

    class _Offer:
        def __init__(self, description: str):
            self.description = description

    n = log_search_item_outcomes(
        items=[
            {"label": "arroz", "search_term": "arroz"},
            {"label": "leite", "search_term": "leite"},
        ],
        offers_by_item={
            "arroz": [_Offer("ARROZ CAMIL 5KG"), _Offer("ARROZ TIO JOAO")],
            "leite": [_Offer("LEITE INTEGRAL 1L")],
        },
        stores_found=4,
        data_source="mock",
        fetch_failed_labels=[],
        latency_ms=50,
        list_id="list-abc",
        analytics_id="anon-hash",
    )
    assert n == 2
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    rows = [json.loads(l) for l in lines]
    queries = {r["query"] for r in rows}
    assert queries == {"arroz", "leite"}
    for r in rows:
        for k in REQUIRED_KEYS:
            assert k in r
        assert r["match_rules_version"] == MATCH_RULES_VERSION
        assert r["list_id"] == "list-abc"
        assert r["analytics_id"] == "anon-hash"
        assert "device_token" not in r
        assert len(r["top_descriptions"]) <= 3
    arroz = next(r for r in rows if r["query"] == "arroz")
    assert arroz["top_descriptions"][0].startswith("ARROZ")


def test_log_marks_fetch_failed(tmp_path, monkeypatch):
    path = tmp_path / "out.jsonl"
    monkeypatch.setenv(ENV_LOG_PATH, str(path))
    monkeypatch.setenv(ENV_LOG_SAMPLE, "1.0")
    n = log_search_item_outcomes(
        items=["feijão"],
        offers_by_item={},
        stores_found=0,
        fetch_failed_labels=["feijão"],
    )
    assert n == 1
    row = json.loads(path.read_text(encoding="utf-8").strip())
    assert row["items_fetch_failed"] is True
    assert row["top_descriptions"] == []


def test_refuse_row_with_device_token_in_blob(tmp_path, monkeypatch):
    path = tmp_path / "out.jsonl"
    monkeypatch.setenv(ENV_LOG_PATH, str(path))
    row = build_item_outcome(query="x")
    # Inject after sanitize path by calling append with a poisoned string field
    row["note"] = "device_token=abc"
    assert append_outcome(row, path=str(path)) is False
    assert not path.exists() or path.read_text() == ""


def test_search_api_exposes_match_rules_version():
    with TestClient(create_app()) as c:
        r = c.post("/api/v1/search", json={"items": ["arroz"]})
    assert r.status_code == 200
    body = r.json()
    metrics = body["metrics"]
    assert "match_rules_version" in metrics
    assert metrics["match_rules_version"] == MATCH_RULES_VERSION
    assert metrics["match_rules_version"].strip()


def test_search_api_appends_outcome_when_path_set(tmp_path, monkeypatch):
    path = tmp_path / "api_outcomes.jsonl"
    monkeypatch.setenv(ENV_LOG_PATH, str(path))
    monkeypatch.setenv(ENV_LOG_SAMPLE, "1.0")
    with TestClient(create_app()) as c:
        r = c.post("/api/v1/search", json={"items": ["arroz", "leite"]})
    assert r.status_code == 200
    assert path.exists(), "expected outcome log on real search path"
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 2, f"expected ≥1 line per item, got {len(lines)}"
    for ln in lines:
        row = json.loads(ln)
        for k in REQUIRED_KEYS:
            assert k in row
        assert row["match_rules_version"] == MATCH_RULES_VERSION
        low = ln.lower()
        assert "device_token" not in low
        assert "authorization" not in low
        assert "sefaz_app_token" not in low


def test_search_api_noop_when_path_unset(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_LOG_PATH, raising=False)
    # Ensure we don't accidentally write under tmp if something else sets path.
    before = list(tmp_path.iterdir()) if tmp_path.exists() else []
    with TestClient(create_app()) as c:
        r = c.post("/api/v1/search", json={"items": ["arroz"]})
    assert r.status_code == 200
    assert outcome_log_path() is None
    # No new jsonl created in tmp_path by us; global cwd may have none either.
    assert list(tmp_path.iterdir()) == before


def test_search_api_sample_zero_no_lines(tmp_path, monkeypatch):
    path = tmp_path / "sampled.jsonl"
    monkeypatch.setenv(ENV_LOG_PATH, str(path))
    monkeypatch.setenv(ENV_LOG_SAMPLE, "0.0")
    with TestClient(create_app()) as c:
        for _ in range(5):
            r = c.post("/api/v1/search", json={"items": ["arroz"]})
            assert r.status_code == 200
    assert not path.exists() or path.read_text().strip() == ""


def test_env_example_documents_outcome_log():
    # Repo root .env.example (two parents up from backend/tests → backend → root)
    root = Path(__file__).resolve().parents[2]
    env_ex = root / ".env.example"
    text = env_ex.read_text(encoding="utf-8")
    assert "MATCH_OUTCOME_LOG_PATH" in text
    assert "MATCH_OUTCOME_LOG_SAMPLE" in text
