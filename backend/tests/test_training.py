"""Tests for the training system (flags + daily job)."""

from __future__ import annotations

import json

import pytest

from app.services.catalog.manager import CatalogManager
from app.services.training.flags import TrainingFlagStore
from app.services.training.daily_job import DailyTrainingJob


@pytest.fixture
def flag_store(tmp_path):
    return TrainingFlagStore(path=tmp_path / "flags.json")


@pytest.fixture
def catalog(tmp_path):
    data = {
        "version": 1,
        "products": [
            {
                "id": 1, "slug": "arroz", "display_name": "Arroz",
                "category": "staples",
                "search_queries": ["arroz tipo 1"],
                "brands": ["Camil"],
                "sizes": ["1 KG"],
                "sefaz_terms_positive": ["ARROZ BRANCO 1KG"],
                "sefaz_terms_negative": ["ARROZ P CAES"],
                "enabled": True,
            },
            {
                "id": 2, "slug": "leite", "display_name": "Leite",
                "category": "dairy",
                "search_queries": ["leite uht"],
                "brands": [],
                "sizes": [],
                "sefaz_terms_positive": [],
                "sefaz_terms_negative": ["LEITE CONDENSADO"],
                "enabled": True,
            },
        ],
    }
    path = tmp_path / "catalog.json"
    with open(path, "w") as f:
        json.dump(data, f)
    return CatalogManager(catalog_path=path)


class TestTrainingFlagStore:
    def test_add_flag(self, flag_store):
        flag = flag_store.add_flag(
            "product_not_found",
            product_id=1,
            product_slug="arroz",
            details={"search_terms_used": ["arroz tipo 1"]},
        )
        assert flag.flag_type == "product_not_found"
        assert flag.product_id == 1

    def test_pending_flags(self, flag_store):
        flag_store.add_flag("product_not_found", product_id=1, product_slug="arroz")
        flag_store.add_flag("validation_failure", product_id=2, product_slug="leite")
        pending = flag_store.pending_flags()
        assert len(pending) == 2

    def test_resolve_flag(self, flag_store):
        flag_store.add_flag("product_not_found", product_id=1, product_slug="arroz")
        flag_store.resolve_flag(0, "Added base query 'arroz'")
        pending = flag_store.pending_flags()
        assert len(pending) == 0

    def test_flag_product_not_found(self, flag_store):
        flag = flag_store.flag_product_not_found(
            product_id=1,
            product_slug="arroz",
            search_terms_used=["arroz tipo 1"],
            location=(-9.6633, -35.7089),
        )
        assert flag.details["location"] == [-9.6633, -35.7089]

    def test_flag_incomplete_coverage(self, flag_store):
        flag = flag_store.flag_incomplete_coverage(
            store_cnpj="12345",
            store_name="Test Store",
            products_found=["arroz", "feijao"],
            products_missing=["leite", "cafe"],
            coverage_ratio=0.5,
        )
        assert flag.flag_type == "incomplete_store_coverage"

    def test_flag_validation_failure(self, flag_store):
        flag = flag_store.flag_validation_failure(
            product_id=1,
            product_slug="arroz",
            search_term="arroz tipo 1",
            rejected_descriptions=["ARROZ P CAES 1KG"],
            reason="Dog food in results",
        )
        assert flag.flag_type == "validation_failure"

    def test_persistence(self, tmp_path):
        path = tmp_path / "flags.json"
        store1 = TrainingFlagStore(path=path)
        store1.add_flag("test", product_id=1, product_slug="arroz")

        # Reload from disk
        store2 = TrainingFlagStore(path=path)
        assert len(store2.pending_flags()) == 1

    def test_clear_resolved(self, flag_store):
        flag_store.add_flag("test1", product_id=1, product_slug="arroz")
        flag_store.add_flag("test2", product_id=2, product_slug="leite")
        flag_store.resolve_flag(0, "done")
        removed = flag_store.clear_resolved()
        assert removed == 1
        assert len(flag_store.all_flags()) == 1


class TestDailyTrainingJob:
    @pytest.mark.asyncio
    async def test_no_pending_flags(self, catalog, flag_store):
        job = DailyTrainingJob(catalog=catalog, flag_store=flag_store)
        result = await job.run()
        assert result.processed_flags == 0

    @pytest.mark.asyncio
    async def test_process_product_not_found(self, catalog, flag_store):
        flag_store.flag_product_not_found(
            product_id=1,
            product_slug="arroz",
            search_terms_used=["arroz tipo 1"],
        )
        job = DailyTrainingJob(catalog=catalog, flag_store=flag_store)
        result = await job.run()
        assert result.processed_flags == 1
        # Should have added base query "arroz"
        product = catalog.get(1)
        assert "arroz" in product.search_queries

    @pytest.mark.asyncio
    async def test_process_validation_failure(self, catalog, flag_store):
        flag_store.flag_validation_failure(
            product_id=2,
            product_slug="leite",
            search_term="leite uht",
            rejected_descriptions=["LEITE CONDENSADO MOCINHA"],
            reason="Wrong product type",
        )
        job = DailyTrainingJob(catalog=catalog, flag_store=flag_store)
        result = await job.run()
        assert result.processed_flags == 1
        # Should have added negative term
        product = catalog.get(2)
        assert "LEITE CONDENSADO MOCINHA" in product.sefaz_terms_negative

    @pytest.mark.asyncio
    async def test_process_new_product_request(self, catalog, flag_store):
        catalog.add_request("Pipoca")
        job = DailyTrainingJob(catalog=catalog, flag_store=flag_store)
        result = await job.run()
        assert result.new_products_added == 1
        # New product should be in catalog
        p = catalog.get_by_slug("pipoca")
        assert p is not None
        assert p.display_name == "Pipoca"

    @pytest.mark.asyncio
    async def test_reject_duplicate_request(self, catalog, flag_store):
        catalog.add_request("Arroz")  # Already exists
        job = DailyTrainingJob(catalog=catalog, flag_store=flag_store)
        result = await job.run()
        assert result.new_products_added == 0

    @pytest.mark.asyncio
    async def test_catalog_saved_after_training(self, catalog, flag_store):
        flag_store.flag_product_not_found(
            product_id=1,
            product_slug="arroz",
            search_terms_used=["arroz tipo 1"],
        )
        job = DailyTrainingJob(catalog=catalog, flag_store=flag_store)
        await job.run()

        # Reload catalog from disk and verify changes persisted
        catalog2 = CatalogManager(catalog_path=catalog._path)
        product = catalog2.get(1)
        assert "arroz" in product.search_queries

    @pytest.mark.asyncio
    async def test_flags_resolved_after_training(self, catalog, flag_store):
        flag_store.flag_product_not_found(
            product_id=1, product_slug="arroz", search_terms_used=["arroz tipo 1"],
        )
        job = DailyTrainingJob(catalog=catalog, flag_store=flag_store)
        await job.run()
        assert len(flag_store.pending_flags()) == 0
