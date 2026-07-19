"""Tests for the POST /api/v1/catalog/search endpoint and the training scheduler
entry point — the wiring that makes the catalog pipeline reachable in the app."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
import fakeredis.aioredis
from fastapi.testclient import TestClient

from app.api import deps
from app.config import Settings
from app.main import create_app
from app.services.catalog.manager import CatalogManager
from app.services.sefaz.mock_client import MockSefazClient
from app.services.training.flags import TrainingFlagStore
from app.services.training.scheduler import run_training_once


@pytest.fixture(autouse=True)
def reset_catalog_singleton():
    import app.services.catalog.manager as mgr
    old = mgr._catalog
    mgr._catalog = None
    yield
    mgr._catalog = old


def _catalog(tmp_path) -> CatalogManager:
    data = {
        "version": 1,
        "products": [
            {
                "id": 1, "slug": "arroz", "display_name": "Arroz",
                "category": "staples", "search_queries": ["arroz", "arroz tipo 1"],
                "brands": [], "sizes": [],
                "sefaz_terms_positive": ["ARROZ BRANCO 1KG"], "sefaz_terms_negative": [],
                "enabled": True,
            },
        ],
    }
    path = tmp_path / "catalog.json"
    with open(path, "w") as f:
        json.dump(data, f)
    return CatalogManager(catalog_path=path)


class _FakeCache:
    def __init__(self, redis):
        self.redis = redis


def _make_client(catalog, flag_store, redis, validation_llm=None):
    app = create_app()
    settings = Settings(use_mock_sefaz=True, use_mock_llm=True,
                        redis_url="redis://localhost:6379/0")
    app.dependency_overrides[deps.get_sefaz] = lambda: MockSefazClient()
    app.dependency_overrides[deps.get_cache] = lambda: _FakeCache(redis)
    app.dependency_overrides[deps.get_catalog_dep] = lambda: catalog
    app.dependency_overrides[deps.get_flag_store_dep] = lambda: flag_store
    app.dependency_overrides[deps.get_validation_llm] = lambda: validation_llm
    app.dependency_overrides[deps.get_settings_dep] = lambda: settings
    app.dependency_overrides[deps.enforce_rate_limit] = lambda: None
    return TestClient(app, raise_server_exceptions=False)


class TestCatalogSearchEndpoint:
    @pytest.fixture
    async def redis(self):
        r = fakeredis.aioredis.FakeRedis()
        yield r
        await r.aclose()

    def test_structured_search_returns_results(self, tmp_path, redis):
        catalog = _catalog(tmp_path)
        flags = TrainingFlagStore(path=tmp_path / "flags.json")
        client = _make_client(catalog, flags, redis)
        resp = client.post("/api/v1/catalog/search", json={
            "selections": [{"product_id": 1, "quantity": 2}],
            "latitude": -9.6633, "longitude": -35.7089,
        })
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["items_requested"] >= 1
        assert "stores" in body

    def test_missing_coords_rejected(self, tmp_path, redis):
        catalog = _catalog(tmp_path)
        flags = TrainingFlagStore(path=tmp_path / "flags.json")
        client = _make_client(catalog, flags, redis)
        resp = client.post("/api/v1/catalog/search", json={
            "selections": [{"product_id": 1, "quantity": 1}],
        })
        assert resp.status_code == 422

    def test_empty_selections_rejected(self, tmp_path, redis):
        catalog = _catalog(tmp_path)
        flags = TrainingFlagStore(path=tmp_path / "flags.json")
        client = _make_client(catalog, flags, redis)
        resp = client.post("/api/v1/catalog/search", json={
            "selections": [], "latitude": -9.66, "longitude": -35.7,
        })
        assert resp.status_code == 422  # pydantic min_length


class TestSchedulerEntryPoint:
    @pytest.mark.asyncio
    async def test_run_training_once_with_daylock(self, tmp_path):
        catalog = _catalog(tmp_path)
        flags = TrainingFlagStore(path=tmp_path / "flags.json")
        flags.flag_product_not_found(product_id=1, product_slug="arroz",
                                     search_terms_used=["arroz tipo 1"])
        redis = fakeredis.aioredis.FakeRedis()
        app = SimpleNamespace(state=SimpleNamespace(
            catalog=catalog, flag_store=flags, validation_llm=None,
            sefaz=MockSefazClient(),
            cache=SimpleNamespace(redis=redis),
            settings=Settings(training_interval_hours=24),
        ))
        # First run wins the day-lock and processes the flag.
        result = await run_training_once(app, use_lock=True)
        assert result is not None
        assert result.processed_flags == 1
        # Second run the same day is skipped (lock held).
        assert await run_training_once(app, use_lock=True) is None
        await redis.aclose()
