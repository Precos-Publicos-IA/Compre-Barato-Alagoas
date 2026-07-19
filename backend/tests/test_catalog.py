"""Tests for the product catalog system."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from app.services.catalog.manager import CatalogManager, ProductEntry, get_catalog


@pytest.fixture
def catalog_path(tmp_path):
    """Create a temporary catalog file."""
    catalog_data = {
        "version": 1,
        "updated_at": "2026-07-19T00:00:00Z",
        "description": "Test catalog",
        "products": [
            {
                "id": 1,
                "slug": "arroz",
                "display_name": "Arroz",
                "category": "staples",
                "image_url": None,
                "sefaz_terms_positive": ["ARROZ BRANCO 1KG", "ARROZ TIPO 1"],
                "sefaz_terms_negative": ["ARROZ P CAES", "ARROZ DOCE"],
                "search_queries": ["arroz", "arroz tipo 1"],
                "brands": ["Camil", "Tio Vieira"],
                "sizes": ["1 KG", "5 KG"],
                "enabled": True,
            },
            {
                "id": 2,
                "slug": "leite",
                "display_name": "Leite",
                "category": "dairy",
                "image_url": None,
                "sefaz_terms_positive": ["LEITE UHT INTEGRAL 1L"],
                "sefaz_terms_negative": ["LEITE CONDENSADO", "CREME DE LEITE"],
                "search_queries": ["leite", "leite uht"],
                "brands": ["Italac", "Betania"],
                "sizes": ["1 L"],
                "enabled": True,
            },
            {
                "id": 3,
                "slug": "feijao",
                "display_name": "Feijão",
                "category": "staples",
                "image_url": None,
                "sefaz_terms_positive": ["FEIJAO CARIOCA 1KG"],
                "sefaz_terms_negative": ["TEMPERO PARA FEIJAO"],
                "search_queries": ["feijao", "feijao carioca"],
                "brands": ["Camil"],
                "sizes": ["1 KG"],
                "enabled": True,
            },
            {
                "id": 4,
                "slug": "cafe",
                "display_name": "Café",
                "category": "beverages",
                "image_url": None,
                "sefaz_terms_positive": [],
                "sefaz_terms_negative": [],
                "search_queries": ["cafe"],
                "brands": [],
                "sizes": [],
                "enabled": False,
            },
        ],
    }
    path = tmp_path / "product_catalog.json"
    with open(path, "w") as f:
        json.dump(catalog_data, f)
    return path


@pytest.fixture
def catalog(catalog_path):
    return CatalogManager(catalog_path=catalog_path)


class TestCatalogManager:
    def test_load_products(self, catalog):
        products = catalog.all_products(enabled_only=False)
        assert len(products) == 4

    def test_enabled_only(self, catalog):
        products = catalog.all_products(enabled_only=True)
        assert len(products) == 3
        assert all(p.enabled for p in products)

    def test_get_by_id(self, catalog):
        p = catalog.get(1)
        assert p is not None
        assert p.slug == "arroz"
        assert p.display_name == "Arroz"

    def test_get_by_slug(self, catalog):
        p = catalog.get_by_slug("leite")
        assert p is not None
        assert p.id == 2

    def test_get_missing(self, catalog):
        assert catalog.get(999) is None
        assert catalog.get_by_slug("nonexistent") is None

    def test_search_prefix(self, catalog):
        results = catalog.search("arr")
        assert len(results) >= 1
        assert results[0].slug == "arroz"

    def test_search_substring(self, catalog):
        results = catalog.search("eij")
        assert len(results) >= 1
        assert any(r.slug == "feijao" for r in results)

    def test_search_accent_insensitive(self, catalog):
        results = catalog.search("feijao")
        assert len(results) >= 1
        assert any(r.slug == "feijao" for r in results)

    def test_search_empty(self, catalog):
        results = catalog.search("")
        assert len(results) == 0

    def test_categories(self, catalog):
        cats = catalog.categories()
        assert "staples" in cats
        assert "dairy" in cats

    def test_products_by_category(self, catalog):
        staples = catalog.products_by_category("staples")
        assert len(staples) == 2  # arroz, feijao (cafe is disabled)

    def test_update_product(self, catalog):
        assert catalog.update_product(1, {"brands": ["Camil", "Tio Vieira", "Pindorama"]})
        p = catalog.get(1)
        assert "Pindorama" in p.brands

    def test_add_product(self, catalog):
        new = ProductEntry(
            id=5,
            slug="sal",
            display_name="Sal",
            category="staples",
            search_queries=["sal"],
        )
        catalog.add_product(new)
        assert catalog.get(5) is not None
        assert catalog.get_by_slug("sal") is not None

    def test_save_and_reload(self, catalog, catalog_path):
        catalog.update_product(1, {"brands": ["NewBrand"]})
        catalog.save()

        # Reload from disk
        catalog2 = CatalogManager(catalog_path=catalog_path)
        p = catalog2.get(1)
        assert "NewBrand" in p.brands

    def test_hot_reload(self, catalog, catalog_path):
        # Modify file directly
        with open(catalog_path) as f:
            data = json.load(f)
        data["products"].append({
            "id": 10,
            "slug": "sal",
            "display_name": "Sal",
            "category": "staples",
            "sefaz_terms_positive": [],
            "sefaz_terms_negative": [],
            "search_queries": ["sal"],
            "brands": [],
            "sizes": [],
            "enabled": True,
        })
        with open(catalog_path, "w") as f:
            json.dump(data, f)

        assert catalog.reload_if_changed()
        assert catalog.get(10) is not None


class TestProductEntry:
    def test_from_dict(self):
        d = {
            "id": 1,
            "slug": "arroz",
            "display_name": "Arroz",
            "category": "staples",
            "search_queries": ["arroz"],
        }
        p = ProductEntry.from_dict(d)
        assert p.id == 1
        assert p.slug == "arroz"
        assert p.sefaz_terms_positive == []
        assert p.enabled is True

    def test_to_dict_roundtrip(self):
        p = ProductEntry(
            id=1,
            slug="arroz",
            display_name="Arroz",
            category="staples",
            brands=["Camil"],
            sizes=["1 KG"],
            search_queries=["arroz tipo 1"],
        )
        d = p.to_dict()
        p2 = ProductEntry.from_dict(d)
        assert p2.id == p.id
        assert p2.brands == p.brands
        assert p2.search_queries == p.search_queries


class TestProductRequests:
    def test_add_request(self, catalog):
        req = catalog.add_request("Pipoca", requested_by="device123")
        assert req.status == "pending"
        assert req.name == "Pipoca"

    def test_pending_requests(self, catalog):
        catalog.add_request("Pipoca")
        catalog.add_request("Chocolate")
        pending = catalog.pending_requests()
        assert len(pending) == 2

    def test_update_request(self, catalog):
        catalog.add_request("Pipoca")
        catalog.update_request(0, "approved", notes="Added as id=10")
        pending = catalog.pending_requests()
        assert len(pending) == 0
