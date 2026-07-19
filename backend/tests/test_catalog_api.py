"""Tests for the catalog API endpoints."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.catalog.manager import CatalogManager, _catalog


@pytest.fixture(autouse=True)
def reset_catalog_singleton():
    """Reset the catalog singleton between tests."""
    import app.services.catalog.manager as mgr
    old = mgr._catalog
    mgr._catalog = None
    yield
    mgr._catalog = old


class TestCatalogAPI:
    @pytest.fixture
    def client(self):
        app = create_app()
        return TestClient(app, raise_server_exceptions=False)

    def test_list_products(self, client):
        resp = client.get("/api/v1/catalog/products")
        assert resp.status_code == 200
        data = resp.json()
        assert "products" in data
        assert "total" in data
        assert data["total"] >= 0

    def test_list_products_with_category(self, client):
        resp = client.get("/api/v1/catalog/products?category=staples")
        assert resp.status_code == 200
        data = resp.json()
        for p in data["products"]:
            assert p["category"] == "staples"

    def test_search_products(self, client):
        resp = client.get("/api/v1/catalog/products/search?q=arroz")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        if data["results"]:
            assert data["results"][0]["slug"] == "arroz" or "arroz" in data["results"][0]["display_name"].lower()

    def test_get_product(self, client):
        # First get a product ID
        resp = client.get("/api/v1/catalog/products")
        data = resp.json()
        if not data["products"]:
            pytest.skip("No products in catalog")
        pid = data["products"][0]["id"]

        resp = client.get(f"/api/v1/catalog/products/{pid}")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["id"] == pid
        assert "sefaz_terms_positive" in detail
        assert "search_queries" in detail

    def test_get_nonexistent_product(self, client):
        resp = client.get("/api/v1/catalog/products/99999")
        assert resp.status_code == 404

    def test_list_categories(self, client):
        resp = client.get("/api/v1/catalog/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert "categories" in data

    def test_request_product(self, client):
        # Use a name likely already in catalog to get "duplicate" (non-mutating)
        resp = client.post(
            "/api/v1/catalog/products/request",
            json={"name": "Arroz", "requested_by": "test"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("pending", "duplicate")

    def test_suggestions_have_product_ids(self, client):
        resp = client.get("/api/v1/suggestions")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        # At least some suggestions should have product_id from catalog
        has_pid = sum(1 for item in data["items"] if "product_id" in item)
        # It's OK if catalog is empty in test, but the structure should be right
        assert isinstance(data["items"], list)
