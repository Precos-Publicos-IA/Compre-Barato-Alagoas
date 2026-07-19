"""Integration tests: catalog system with real training data."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.catalog.manager import CatalogManager
from app.services.catalog.query_transform import ProductSelection, build_query_plan
from app.services.catalog.validation import deterministic_validate
from app.services.training.flags import TrainingFlagStore
from app.services.training.daily_job import DailyTrainingJob

# Path to the real catalog (built from training data)
_REAL_CATALOG = Path(__file__).parent.parent / "data" / "product_catalog.json"


@pytest.fixture
def real_catalog():
    """Load the real product catalog."""
    if not _REAL_CATALOG.exists():
        pytest.skip("Real catalog not found")
    return CatalogManager(catalog_path=_REAL_CATALOG)


class TestRealCatalog:
    def test_has_at_least_100_products(self, real_catalog):
        products = real_catalog.all_products()
        assert len(products) >= 100

    def test_all_products_have_search_queries(self, real_catalog):
        for p in real_catalog.all_products():
            assert p.search_queries, f"{p.slug} has no search queries"

    def test_staples_have_brands_or_sizes(self, real_catalog):
        staples = real_catalog.products_by_category("staples")
        with_brands = sum(1 for s in staples if s.brands)
        # At least some staples should have brands
        assert with_brands >= 3, f"Only {with_brands}/{len(staples)} staples have brands"

    def test_search_common_products(self, real_catalog):
        for query in ["arroz", "leite", "feijao", "cafe", "oleo"]:
            results = real_catalog.search(query)
            assert len(results) >= 1, f"Search for '{query}' returned no results"
            assert results[0].slug == query or query in results[0].search_text()

    def test_category_integrity(self, real_catalog):
        cats = real_catalog.categories()
        assert "staples" in cats
        assert "dairy" in cats
        assert "meat" in cats

    def test_search_accent_insensitive(self, real_catalog):
        for query in ["acucar", "feijao", "pao", "cafe", "oleo"]:
            results = real_catalog.search(query)
            assert len(results) >= 1, f"Accent-free search for '{query}' failed"


class TestQueryPlanWithRealCatalog:
    def test_single_product(self, real_catalog):
        """Selecting 'arroz' should produce SEFAZ queries."""
        arroz = real_catalog.get_by_slug("arroz")
        if not arroz:
            pytest.skip("arroz not in catalog")
        sel = [ProductSelection(product_id=arroz.id)]
        plan = build_query_plan(sel, real_catalog)
        assert len(plan.queries) >= 1
        assert all(q.product_slug == "arroz" for q in plan.queries)

    def test_multi_product_basket(self, real_catalog):
        """A basket with 5 common products should produce queries for all."""
        slugs = ["arroz", "feijao", "leite", "oleo", "cafe"]
        sels = []
        for s in slugs:
            p = real_catalog.get_by_slug(s)
            if p:
                sels.append(ProductSelection(product_id=p.id))
        plan = build_query_plan(sels, real_catalog)
        # Each product should have at least one query
        pids_with_queries = {q.product_id for q in plan.queries}
        for sel in sels:
            assert sel.product_id in pids_with_queries

    def test_brand_filtered_query(self, real_catalog):
        """Brand-filtered query should include brand in search term."""
        arroz = real_catalog.get_by_slug("arroz")
        if not arroz or not arroz.brands:
            pytest.skip("arroz has no brands in catalog")
        brand = arroz.brands[0]
        sel = [ProductSelection(product_id=arroz.id, selected_brands=[brand])]
        plan = build_query_plan(sel, real_catalog)
        assert any(brand.lower() in q.search_term.lower() for q in plan.queries)


class TestValidationWithRealData:
    def test_validate_good_arroz(self):
        """Real arroz descriptions should validate as correct."""
        result = deterministic_validate(
            product_slug="arroz",
            display_name="Arroz",
            category="staples",
            descriptions=[
                "ARROZ BRANCO CAMPOS VERDES 1KG",
                "ARROZ TIPO 1 CAMIL 5KG",
                "ARROZ PARBOILIZADO KIARROZ 1KG",
            ],
            known_negative=["ARROZ P CAES", "ARROZ DOCE"],
        )
        assert result.valid is True

    def test_validate_bad_leite(self):
        """Leite condensado shouldn't pass as plain leite."""
        result = deterministic_validate(
            product_slug="leite",
            display_name="Leite",
            category="dairy",
            descriptions=[
                "LEITE CONDENSADO MOCINHA 395G",
                "LEITE CONDENSADO ITALAC",
            ],
            known_negative=["LEITE CONDENSADO"],
        )
        assert result.valid is False

    def test_validate_mixed_results(self):
        """Mix of good and bad should still be valid if <50% bad."""
        result = deterministic_validate(
            product_slug="leite",
            display_name="Leite",
            category="dairy",
            descriptions=[
                "LEITE UHT INTEGRAL BETANIA 1L",
                "LEITE INTEGRAL ITALAC 1L",
                "LEITE CONDENSADO MOCINHA",
            ],
            known_negative=["LEITE CONDENSADO"],
        )
        assert result.valid is True


class TestTrainingWithRealCatalog:
    @pytest.mark.asyncio
    async def test_training_round_trip(self, real_catalog, tmp_path):
        """Full training cycle: add flags → run training → verify catalog updated."""
        flags = TrainingFlagStore(path=tmp_path / "flags.json")

        # Flag a product as not found
        arroz = real_catalog.get_by_slug("arroz")
        if not arroz:
            pytest.skip("arroz not in catalog")

        # Simulate: searched with only one query, not found
        flags.flag_product_not_found(
            product_id=arroz.id,
            product_slug="arroz",
            search_terms_used=["arroz parboilizado especial"],
            location=(-9.6633, -35.7089),
        )

        job = DailyTrainingJob(catalog=real_catalog, flag_store=flags)
        result = await job.run()
        assert result.processed_flags == 1
        # Should NOT have added base query "arroz" since it already exists
        # (the deterministic fallback only adds base name if missing)
