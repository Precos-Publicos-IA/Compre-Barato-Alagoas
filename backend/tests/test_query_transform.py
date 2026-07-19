"""Tests for input-to-query transformation."""

from __future__ import annotations

import json

import pytest

from app.services.catalog.manager import CatalogManager, ProductEntry
from app.services.catalog.query_transform import (
    ProductSelection,
    build_query_plan,
)


@pytest.fixture
def catalog(tmp_path):
    data = {
        "version": 1,
        "products": [
            {
                "id": 1, "slug": "arroz", "display_name": "Arroz",
                "category": "staples",
                "search_queries": ["arroz", "arroz tipo 1"],
                "brands": ["Camil", "Tio Vieira"],
                "sizes": ["1 KG", "5 KG"],
                "enabled": True,
                "sefaz_terms_positive": [], "sefaz_terms_negative": [],
            },
            {
                "id": 2, "slug": "leite", "display_name": "Leite",
                "category": "dairy",
                "search_queries": ["leite", "leite uht"],
                "brands": ["Italac"],
                "sizes": ["1 L"],
                "enabled": True,
                "sefaz_terms_positive": [], "sefaz_terms_negative": [],
            },
        ],
    }
    path = tmp_path / "catalog.json"
    with open(path, "w") as f:
        json.dump(data, f)
    return CatalogManager(catalog_path=path)


class TestBuildQueryPlan:
    def test_basic_selection(self, catalog):
        sels = [ProductSelection(product_id=1, quantity=2)]
        plan = build_query_plan(sels, catalog)
        assert len(plan.queries) >= 1
        assert plan.queries[0].product_id == 1
        assert plan.queries[0].display_name == "Arroz"
        assert plan.queries[0].quantity == 2
        # Uses all search queries (up to 3)
        terms = {q.search_term for q in plan.queries}
        assert "arroz" in terms
        assert "arroz tipo 1" in terms

    def test_brand_filter(self, catalog):
        sels = [ProductSelection(product_id=1, selected_brands=["Camil"])]
        plan = build_query_plan(sels, catalog)
        assert len(plan.queries) == 1
        assert "camil" in plan.queries[0].search_term
        assert plan.queries[0].brand_filter == "Camil"

    def test_size_filter(self, catalog):
        sels = [ProductSelection(product_id=1, selected_sizes=["5 KG"])]
        plan = build_query_plan(sels, catalog)
        assert all(q.size_filter == "5 KG" for q in plan.queries)

    def test_unknown_product(self, catalog):
        sels = [ProductSelection(product_id=999)]
        plan = build_query_plan(sels, catalog)
        assert len(plan.queries) == 0
        assert 999 in plan.unresolved

    def test_multiple_products(self, catalog):
        sels = [
            ProductSelection(product_id=1),
            ProductSelection(product_id=2),
        ]
        plan = build_query_plan(sels, catalog)
        # Both products should have queries
        pids = {q.product_id for q in plan.queries}
        assert 1 in pids
        assert 2 in pids

    def test_multiple_brands(self, catalog):
        sels = [ProductSelection(product_id=1, selected_brands=["Camil", "Tio Vieira"])]
        plan = build_query_plan(sels, catalog)
        assert len(plan.queries) == 2
        brands = {q.brand_filter for q in plan.queries}
        assert brands == {"Camil", "Tio Vieira"}
