"""Tests for the geo-aware SEFAZ cache."""

from __future__ import annotations

import pytest
import fakeredis.aioredis

from app.services.catalog.sefaz_cache import SefazGeoCache, _geo_cell


@pytest.fixture
async def redis():
    r = fakeredis.aioredis.FakeRedis()
    yield r
    await r.aclose()


@pytest.fixture
async def cache(redis):
    return SefazGeoCache(redis=redis, ttl=3600)


class TestGeoCell:
    def test_nearby_locations_same_cell(self):
        """Locations within ~1km should map to the same cell."""
        # Two points ~0.5km apart in Maceió
        cell1 = _geo_cell(-9.6633, -35.7089)
        cell2 = _geo_cell(-9.6638, -35.7085)
        assert cell1 == cell2

    def test_far_locations_different_cells(self):
        """Locations >1km apart should map to different cells."""
        cell1 = _geo_cell(-9.6633, -35.7089)
        cell2 = _geo_cell(-9.6833, -35.7089)  # ~2.2km away
        assert cell1 != cell2


class TestSefazGeoCache:
    @pytest.mark.asyncio
    async def test_set_and_get_product(self, cache):
        data = {"conteudo": [{"test": "data"}], "totalRegistros": 1}
        await cache.set_product(1, -9.6633, -35.7089, data)

        result = await cache.get_product(1, -9.6633, -35.7089)
        assert result is not None
        assert result["totalRegistros"] == 1

    @pytest.mark.asyncio
    async def test_nearby_cache_hit(self, cache):
        data = {"conteudo": [{"test": "data"}], "totalRegistros": 1}
        await cache.set_product(1, -9.6633, -35.7089, data)

        # Slightly different location (~300m away)
        result = await cache.get_product(1, -9.6636, -35.7086)
        assert result is not None  # cache hit!

    @pytest.mark.asyncio
    async def test_far_cache_miss(self, cache):
        data = {"conteudo": [{"test": "data"}], "totalRegistros": 1}
        await cache.set_product(1, -9.6633, -35.7089, data)

        # Far away location
        result = await cache.get_product(1, -9.7000, -35.7089)
        assert result is None

    @pytest.mark.asyncio
    async def test_different_product_cache_miss(self, cache):
        data = {"conteudo": [{"test": "data"}], "totalRegistros": 1}
        await cache.set_product(1, -9.6633, -35.7089, data)

        result = await cache.get_product(2, -9.6633, -35.7089)
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_response_not_cached(self, cache):
        data = {"conteudo": [], "totalRegistros": 0}
        await cache.set_product(1, -9.6633, -35.7089, data)

        result = await cache.get_product(1, -9.6633, -35.7089)
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_product(self, cache):
        data = {"conteudo": [{"test": "data"}], "totalRegistros": 1}
        await cache.set_product(1, -9.6633, -35.7089, data)
        await cache.invalidate_product(1, -9.6633, -35.7089)

        result = await cache.get_product(1, -9.6633, -35.7089)
        assert result is None

    @pytest.mark.asyncio
    async def test_query_cache(self, cache):
        data = {"conteudo": [{"test": "data"}], "totalRegistros": 1}
        await cache.set_query("arroz tipo 1", -9.6633, -35.7089, data)

        result = await cache.get_query("arroz tipo 1", -9.6633, -35.7089)
        assert result is not None

    @pytest.mark.asyncio
    async def test_query_cache_miss_different_term(self, cache):
        data = {"conteudo": [{"test": "data"}], "totalRegistros": 1}
        await cache.set_query("arroz tipo 1", -9.6633, -35.7089, data)

        result = await cache.get_query("feijao", -9.6633, -35.7089)
        assert result is None
