"""Product catalog: the auto-improvable product enum.

All mutable product data lives in ``data/product_catalog.json`` (never hardcoded
in Python files). The catalog is loaded at startup and hot-reloaded when the
training job updates it.
"""

from .manager import CatalogManager, ProductEntry

__all__ = ["CatalogManager", "ProductEntry"]
