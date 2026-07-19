"""Product catalog manager — loads, queries, and persists the product enum.

The catalog lives in ``data/product_catalog.json`` so the daily training job can
update it at runtime without touching Python source files.  The manager exposes:

- Fast in-memory search (prefix / fuzzy for the device selector)
- Structured product entries with SEFAZ term lists, brands, sizes
- Thread-safe hot-reload when the JSON file changes
- New-product request queue (not immediately added to enum)
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CATALOG_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "product_catalog.json"


def _strip_accents(s: str) -> str:
    nk = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nk if not unicodedata.combining(c)).lower().strip()


@dataclass
class ProductEntry:
    """One item in the product enum."""

    id: int
    slug: str
    display_name: str
    category: str
    image_url: str | None = None
    # SEFAZ NFC-e descriptions that ARE this product (positive examples)
    sefaz_terms_positive: list[str] = field(default_factory=list)
    # SEFAZ NFC-e descriptions that are NOT this product but share keywords
    sefaz_terms_negative: list[str] = field(default_factory=list)
    # The actual SEFAZ API query strings to use (e.g. "arroz tipo 1")
    search_queries: list[str] = field(default_factory=list)
    # Known brands for this product
    brands: list[str] = field(default_factory=list)
    # Known sizes/packages for this product
    sizes: list[str] = field(default_factory=list)
    enabled: bool = True

    @classmethod
    def from_dict(cls, d: dict) -> "ProductEntry":
        return cls(
            id=d["id"],
            slug=d["slug"],
            display_name=d["display_name"],
            category=d["category"],
            image_url=d.get("image_url"),
            sefaz_terms_positive=d.get("sefaz_terms_positive", []),
            sefaz_terms_negative=d.get("sefaz_terms_negative", []),
            search_queries=d.get("search_queries", []),
            brands=d.get("brands", []),
            sizes=d.get("sizes", []),
            enabled=d.get("enabled", True),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "slug": self.slug,
            "display_name": self.display_name,
            "category": self.category,
            "image_url": self.image_url,
            "sefaz_terms_positive": self.sefaz_terms_positive,
            "sefaz_terms_negative": self.sefaz_terms_negative,
            "search_queries": self.search_queries,
            "brands": self.brands,
            "sizes": self.sizes,
            "enabled": self.enabled,
        }

    def search_text(self) -> str:
        """Flattened text for fuzzy search."""
        return _strip_accents(
            f"{self.display_name} {self.slug} {' '.join(self.brands)}"
        )


@dataclass
class ProductRequest:
    """A user-requested product not yet in the catalog."""

    name: str
    requested_at: str  # ISO-8601
    requested_by: str | None = None  # device token or analytics_id
    status: str = "pending"  # pending | approved | rejected | duplicate
    resolved_product_id: int | None = None  # if approved and mapped to catalog
    training_notes: str | None = None  # training job conclusion


class CatalogManager:
    """Thread-safe product catalog with hot-reload from JSON."""

    def __init__(self, catalog_path: Path | str | None = None):
        self._path = Path(catalog_path) if catalog_path else _CATALOG_PATH
        self._lock = threading.RLock()
        self._products: dict[int, ProductEntry] = {}
        self._by_slug: dict[str, ProductEntry] = {}
        self._search_index: list[tuple[str, int]] = []  # (normalized_text, product_id)
        self._last_mtime: float = 0.0
        self._requests: list[ProductRequest] = []
        self._requests_path = self._path.parent / "product_requests.json"
        self._load()
        self._load_requests()

    def _load(self) -> None:
        """Load or reload the catalog from disk."""
        if not self._path.exists():
            logger.warning("Catalog file not found: %s", self._path)
            return
        try:
            mtime = self._path.stat().st_mtime
            with self._lock:
                if mtime <= self._last_mtime:
                    return
                with open(self._path, encoding="utf-8") as f:
                    data = json.load(f)
                products = {}
                by_slug = {}
                search_index = []
                for pd in data.get("products", []):
                    entry = ProductEntry.from_dict(pd)
                    products[entry.id] = entry
                    by_slug[entry.slug] = entry
                    search_index.append((entry.search_text(), entry.id))
                self._products = products
                self._by_slug = by_slug
                self._search_index = search_index
                self._last_mtime = mtime
                logger.info("Loaded %d products from catalog", len(products))
        except Exception:
            logger.exception("Failed to load product catalog")

    def reload_if_changed(self) -> bool:
        """Hot-reload if the file changed. Returns True if reloaded."""
        if not self._path.exists():
            return False
        try:
            mtime = self._path.stat().st_mtime
            if mtime > self._last_mtime:
                self._load()
                return True
        except OSError:
            pass
        return False

    # --- Query methods ---

    def get(self, product_id: int) -> ProductEntry | None:
        with self._lock:
            return self._products.get(product_id)

    def get_by_slug(self, slug: str) -> ProductEntry | None:
        with self._lock:
            return self._by_slug.get(slug)

    def all_products(self, enabled_only: bool = True) -> list[ProductEntry]:
        with self._lock:
            if enabled_only:
                return [p for p in self._products.values() if p.enabled]
            return list(self._products.values())

    def search(self, query: str, limit: int = 20) -> list[ProductEntry]:
        """Fast prefix/substring search for the device product selector."""
        q = _strip_accents(query)
        if not q:
            return []
        with self._lock:
            scored: list[tuple[float, int]] = []
            for text, pid in self._search_index:
                product = self._products.get(pid)
                if not product or not product.enabled:
                    continue
                # Exact prefix match is best
                if text.startswith(q):
                    scored.append((0.0, pid))
                # Word-start match
                elif f" {q}" in f" {text}":
                    scored.append((1.0, pid))
                # Substring
                elif q in text:
                    scored.append((2.0, pid))
            scored.sort(key=lambda x: x[0])
            return [self._products[pid] for _, pid in scored[:limit]]

    def categories(self) -> list[str]:
        """All unique categories in the catalog."""
        with self._lock:
            return sorted({p.category for p in self._products.values() if p.enabled})

    def products_by_category(self, category: str) -> list[ProductEntry]:
        with self._lock:
            return [
                p
                for p in self._products.values()
                if p.enabled and p.category == category
            ]

    def next_id(self) -> int:
        with self._lock:
            if not self._products:
                return 1
            return max(self._products.keys()) + 1

    # --- Mutation methods (used by training job) ---

    def save(self) -> None:
        """Persist current catalog to disk."""
        with self._lock:
            data = {
                "version": 1,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "description": "Auto-improvable product catalog. Updated by daily training job.",
                "products": [
                    self._products[pid].to_dict()
                    for pid in sorted(self._products.keys())
                ],
            }
            # Atomic write: write to temp then rename
            tmp = self._path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tmp.rename(self._path)
            self._last_mtime = self._path.stat().st_mtime
            logger.info("Saved catalog with %d products", len(self._products))

    def update_product(self, product_id: int, updates: dict[str, Any]) -> bool:
        """Update specific fields of a product. Returns True if found."""
        with self._lock:
            product = self._products.get(product_id)
            if not product:
                return False
            for key, value in updates.items():
                if hasattr(product, key):
                    setattr(product, key, value)
            # Rebuild search index for this product
            self._search_index = [
                (entry.search_text(), pid)
                for pid, entry in self._products.items()
            ]
            return True

    def add_product(self, entry: ProductEntry) -> None:
        """Add a new product to the catalog."""
        with self._lock:
            self._products[entry.id] = entry
            self._by_slug[entry.slug] = entry
            self._search_index.append((entry.search_text(), entry.id))

    # --- Product requests ---

    def _load_requests(self) -> None:
        if not self._requests_path.exists():
            return
        try:
            with open(self._requests_path, encoding="utf-8") as f:
                data = json.load(f)
            self._requests = [
                ProductRequest(**r) for r in data.get("requests", [])
            ]
        except Exception:
            logger.exception("Failed to load product requests")

    def add_request(self, name: str, requested_by: str | None = None) -> ProductRequest:
        """Queue a new product request from a user."""
        req = ProductRequest(
            name=name.strip(),
            requested_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            requested_by=requested_by,
        )
        with self._lock:
            self._requests.append(req)
            self._save_requests()
        return req

    def pending_requests(self) -> list[ProductRequest]:
        with self._lock:
            return [r for r in self._requests if r.status == "pending"]

    def update_request(self, index: int, status: str, notes: str | None = None,
                       resolved_id: int | None = None) -> None:
        with self._lock:
            if 0 <= index < len(self._requests):
                self._requests[index].status = status
                self._requests[index].training_notes = notes
                self._requests[index].resolved_product_id = resolved_id
                self._save_requests()

    def _save_requests(self) -> None:
        data = {
            "requests": [
                {
                    "name": r.name,
                    "requested_at": r.requested_at,
                    "requested_by": r.requested_by,
                    "status": r.status,
                    "resolved_product_id": r.resolved_product_id,
                    "training_notes": r.training_notes,
                }
                for r in self._requests
            ]
        }
        tmp = self._requests_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.rename(self._requests_path)


# Singleton for app lifetime
_catalog: CatalogManager | None = None


def get_catalog(path: Path | str | None = None) -> CatalogManager:
    global _catalog
    if _catalog is None:
        _catalog = CatalogManager(catalog_path=path)
    return _catalog
