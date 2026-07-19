"""Geo-aware SEFAZ result cache.

Per-product-enum-item caching with location proximity:
- For each product ID, if a search was done from a location within 1 km
  of the current request, that's a cache hit.
- Results are stored with their origin coordinates and TTL.
- Cache keys: sefaz:product:{product_id}:{geo_cell}
  where geo_cell is a truncated lat/lon (0.01 degree ≈ 1.1 km).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 0.01 degree ≈ 1.1 km at the equator; at Maceió latitude (~-9.6°) it's ~1.1 km
# This gives us a grid-based proximity cache without computing actual distances.
_GEO_PRECISION = 2  # decimal places for lat/lon rounding


def _geo_cell(lat: float, lon: float) -> str:
    """Round coordinates to create a geo-cell key."""
    return f"{lat:.{_GEO_PRECISION}f},{lon:.{_GEO_PRECISION}f}"


def _cache_key(product_id: int, geo_cell: str, source: str = "") -> str:
    """Cache key for a product search at a geo-cell."""
    raw = f"sefaz:catalog:{product_id}:{geo_cell}:{source}"
    return raw


def _query_cache_key(search_term: str, geo_cell: str, source: str = "") -> str:
    """Cache key for a raw query term search at a geo-cell."""
    digest = hashlib.sha256(
        f"{search_term.lower()}:{geo_cell}:{source}".encode()
    ).hexdigest()[:16]
    return f"sefaz:query:{digest}"


@dataclass
class CachedResult:
    """A cached SEFAZ response."""

    product_id: int
    search_term: str
    data: dict  # PesquisaResponse as dict
    cached_at: float  # time.time()
    origin_lat: float
    origin_lon: float


class SefazGeoCache:
    """Geo-aware cache layer on top of the app's Redis cache.

    Two cache levels:
    1. Product-level: keyed by (product_id, geo_cell) — cache hit when same
       product is searched from a nearby location
    2. Query-level: keyed by (search_term, geo_cell) — cache hit when the
       exact same SEFAZ query runs from a nearby location (covers cases where
       different products share the same search term)
    """

    def __init__(self, redis, ttl: int = 6 * 60 * 60, source: str = ""):
        self._redis = redis
        self._ttl = ttl
        self._source = source

    async def get_product(
        self, product_id: int, lat: float, lon: float
    ) -> dict | None:
        """Check cache for a product at a nearby location."""
        cell = _geo_cell(lat, lon)
        key = _cache_key(product_id, cell, self._source)
        try:
            raw = await self._redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            logger.debug("SefazGeoCache.get_product error", exc_info=True)
        return None

    async def set_product(
        self,
        product_id: int,
        lat: float,
        lon: float,
        data: dict,
    ) -> None:
        """Cache a SEFAZ response for a product at a location."""
        if not data.get("conteudo"):
            # Don't cache empty results (no-data or errors)
            return
        cell = _geo_cell(lat, lon)
        key = _cache_key(product_id, cell, self._source)
        try:
            payload = json.dumps(data, ensure_ascii=False, default=str)
            await self._redis.set(key, payload, ex=self._ttl)
        except Exception:
            logger.debug("SefazGeoCache.set_product error", exc_info=True)

    async def get_query(
        self, search_term: str, lat: float, lon: float
    ) -> dict | None:
        """Check cache for a specific query term at a nearby location."""
        cell = _geo_cell(lat, lon)
        key = _query_cache_key(search_term, cell, self._source)
        try:
            raw = await self._redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            logger.debug("SefazGeoCache.get_query error", exc_info=True)
        return None

    async def set_query(
        self,
        search_term: str,
        lat: float,
        lon: float,
        data: dict,
    ) -> None:
        """Cache a SEFAZ response for a query term at a location."""
        if not data.get("conteudo"):
            return
        cell = _geo_cell(lat, lon)
        key = _query_cache_key(search_term, cell, self._source)
        try:
            payload = json.dumps(data, ensure_ascii=False, default=str)
            await self._redis.set(key, payload, ex=self._ttl)
        except Exception:
            logger.debug("SefazGeoCache.set_query error", exc_info=True)

    async def invalidate_product(
        self, product_id: int, lat: float, lon: float
    ) -> None:
        """Invalidate cache for a product at a location (after validation failure)."""
        cell = _geo_cell(lat, lon)
        key = _cache_key(product_id, cell, self._source)
        try:
            await self._redis.delete(key)
        except Exception:
            logger.debug("SefazGeoCache.invalidate_product error", exc_info=True)

    async def invalidate_query(
        self, search_term: str, lat: float, lon: float
    ) -> None:
        """Invalidate cache for a query at a location."""
        cell = _geo_cell(lat, lon)
        key = _query_cache_key(search_term, cell, self._source)
        try:
            await self._redis.delete(key)
        except Exception:
            logger.debug("SefazGeoCache.invalidate_query error", exc_info=True)
