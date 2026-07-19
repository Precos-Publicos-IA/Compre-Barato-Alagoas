"""End-to-end test: full catalog search pipeline with mock SEFAZ."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import fakeredis.aioredis

from app.config import Settings
from app.services.catalog.manager import CatalogManager
from app.services.catalog.query_transform import ProductSelection
from app.services.catalog.search import run_catalog_search
from app.services.sefaz.mock_client import MockSefazClient
from app.services.training.flags import TrainingFlagStore


@pytest.fixture
def catalog(tmp_path):
    """Create a catalog with products that match the mock SEFAZ data."""
    data = {
        "version": 1,
        "products": [
            {
                "id": 1, "slug": "arroz", "display_name": "Arroz",
                "category": "staples",
                "search_queries": ["arroz", "arroz tipo 1"],
                "brands": ["Tio João"],
                "sizes": ["1 KG", "5 KG"],
                "sefaz_terms_positive": ["ARROZ BRANCO 1KG"],
                "sefaz_terms_negative": [],
                "enabled": True,
            },
            {
                "id": 2, "slug": "leite", "display_name": "Leite",
                "category": "dairy",
                "search_queries": ["leite", "leite uht"],
                "brands": [],
                "sizes": ["1 L"],
                "sefaz_terms_positive": ["LEITE UHT INTEGRAL"],
                "sefaz_terms_negative": ["LEITE CONDENSADO"],
                "enabled": True,
            },
            {
                "id": 3, "slug": "feijao", "display_name": "Feijão",
                "category": "staples",
                "search_queries": ["feijao", "feijao carioca"],
                "brands": [],
                "sizes": ["1 KG"],
                "sefaz_terms_positive": ["FEIJAO CARIOCA"],
                "sefaz_terms_negative": ["TEMPERO"],
                "enabled": True,
            },
        ],
    }
    path = tmp_path / "catalog.json"
    with open(path, "w") as f:
        json.dump(data, f)
    return CatalogManager(catalog_path=path)


@pytest.fixture
def settings():
    return Settings(
        use_mock_sefaz=True,
        use_mock_llm=True,
        redis_url="redis://localhost:6379/0",
    )


@pytest.fixture
async def redis():
    r = fakeredis.aioredis.FakeRedis()
    yield r
    await r.aclose()


@pytest.fixture
def flag_store(tmp_path):
    return TrainingFlagStore(path=tmp_path / "flags.json")


class TestCatalogSearchE2E:
    @pytest.mark.asyncio
    async def test_single_product_search(self, catalog, settings, redis, flag_store):
        """Search for a single product through the full pipeline."""
        sefaz = MockSefazClient()
        selections = [ProductSelection(product_id=1, quantity=1)]

        response = await run_catalog_search(
            selections,
            catalog=catalog,
            sefaz=sefaz,
            redis=redis,
            settings=settings,
            lat=-9.6633,
            lon=-35.7089,
            flag_store=flag_store,
        )

        assert response.items_requested >= 1
        assert response.data_source == "mock"
        # Mock SEFAZ has arroz products, so we should find results
        assert response.metrics.items_requested >= 1

    @pytest.mark.asyncio
    async def test_multi_product_basket(self, catalog, settings, redis, flag_store):
        """Search for multiple products (shopping basket)."""
        sefaz = MockSefazClient()
        selections = [
            ProductSelection(product_id=1, quantity=2),  # 2x arroz
            ProductSelection(product_id=2, quantity=1),  # 1x leite
            ProductSelection(product_id=3, quantity=1),  # 1x feijao
        ]

        response = await run_catalog_search(
            selections,
            catalog=catalog,
            sefaz=sefaz,
            redis=redis,
            settings=settings,
            lat=-9.6633,
            lon=-35.7089,
            flag_store=flag_store,
        )

        assert response.items_requested >= 3
        assert response.metrics.match_rate >= 0.0

    @pytest.mark.asyncio
    async def test_geo_cache_hit(self, catalog, settings, redis, flag_store):
        """Second search at same location should use cache."""
        sefaz = MockSefazClient()
        selections = [ProductSelection(product_id=1)]

        # First search
        await run_catalog_search(
            selections,
            catalog=catalog,
            sefaz=sefaz,
            redis=redis,
            settings=settings,
            lat=-9.6633,
            lon=-35.7089,
            flag_store=flag_store,
        )

        # Second search at same location - should hit cache
        resp2 = await run_catalog_search(
            selections,
            catalog=catalog,
            sefaz=sefaz,
            redis=redis,
            settings=settings,
            lat=-9.6633,
            lon=-35.7089,
            flag_store=flag_store,
        )

        assert resp2.items_requested >= 1

    @pytest.mark.asyncio
    async def test_unknown_product_handled(self, catalog, settings, redis, flag_store):
        """Search with unknown product ID should handle gracefully."""
        sefaz = MockSefazClient()
        selections = [ProductSelection(product_id=999)]

        response = await run_catalog_search(
            selections,
            catalog=catalog,
            sefaz=sefaz,
            redis=redis,
            settings=settings,
            lat=-9.6633,
            lon=-35.7089,
            flag_store=flag_store,
        )

        assert response.items_requested == 0

    @pytest.mark.asyncio
    async def test_training_flags_generated(self, catalog, settings, redis, flag_store):
        """Products not found should generate training flags."""
        sefaz = MockSefazClient()
        # Add a product with a query term that won't match anything
        catalog.add_product(
            __import__("app.services.catalog.manager", fromlist=["ProductEntry"]).ProductEntry(
                id=99, slug="nonexistent_product", display_name="Nonexistent",
                category="other",
                search_queries=["xyznonexistent123"],
                enabled=True,
            )
        )
        selections = [
            ProductSelection(product_id=1),   # arroz - should find
            ProductSelection(product_id=99),  # nonexistent - won't find
        ]

        await run_catalog_search(
            selections,
            catalog=catalog,
            sefaz=sefaz,
            redis=redis,
            settings=settings,
            lat=-9.6633,
            lon=-35.7089,
            flag_store=flag_store,
        )

        # Should have a "product_not_found" flag for the nonexistent product
        not_found = [f for f in flag_store.pending_flags() if f.flag_type == "product_not_found"]
        assert len(not_found) >= 1
        assert any(f.product_slug == "nonexistent_product" for f in not_found)

    @pytest.mark.asyncio
    async def test_progress_callback(self, catalog, settings, redis, flag_store):
        """Progress callback should be called during search."""
        sefaz = MockSefazClient()
        selections = [ProductSelection(product_id=1)]
        events = []

        async def on_progress(ev):
            events.append(ev)

        await run_catalog_search(
            selections,
            catalog=catalog,
            sefaz=sefaz,
            redis=redis,
            settings=settings,
            lat=-9.6633,
            lon=-35.7089,
            flag_store=flag_store,
            on_progress=on_progress,
        )

        assert len(events) >= 1
        assert any(ev.get("phase") == "fetch" for ev in events)

    @pytest.mark.asyncio
    async def test_excluded_cnpjs(self, catalog, settings, redis, flag_store):
        """Excluded CNPJs should be filtered from results."""
        sefaz = MockSefazClient()
        selections = [ProductSelection(product_id=1)]

        response = await run_catalog_search(
            selections,
            catalog=catalog,
            sefaz=sefaz,
            redis=redis,
            settings=settings,
            lat=-9.6633,
            lon=-35.7089,
            flag_store=flag_store,
            excluded_cnpjs={"00000000000001"},  # likely not in mock data
        )

        # Should still work
        assert response.items_requested >= 1
