"""Empty SEFAZ responses and failed fetches must not poison the search cache.

Under load, web SEFAZ can return empty or raise/timeout. Caching those as full-TTL
hits made ~200ms empty repeats look like "product has no rows" for hours.
"""

from __future__ import annotations

import pytest

from app.cache import Cache
from app.config import MACEIO_LAT, MACEIO_LON, Settings
from app.schemas.search import SearchRequest
from app.services.llm.mock_client import MockLLMClient
from app.services.search_service import _cache_key, run_search
from app.services.sefaz.models import PesquisaResponse

from .conftest import make_registro


class _CountingSefaz:
    source_name = "mock"
    cache_namespace = "mock"

    def __init__(self) -> None:
        self.calls = 0

    async def aclose(self) -> None:  # pragma: no cover
        pass


class _AlwaysEmptySefaz(_CountingSefaz):
    async def search_product(self, *, descricao=None, **kwargs) -> PesquisaResponse:
        self.calls += 1
        return PesquisaResponse(conteudo=[], total_registros=0)


class _FailingSefaz(_CountingSefaz):
    async def search_product(self, *, descricao=None, **kwargs) -> PesquisaResponse:
        self.calls += 1
        raise TimeoutError("upstream timeout")


class _FullSefaz(_CountingSefaz):
    async def search_product(self, *, descricao=None, **kwargs) -> PesquisaResponse:
        self.calls += 1
        return PesquisaResponse(
            conteudo=[
                make_registro(descricao=f"{descricao or 'item'} 1KG", valor_venda=3.0)
            ],
            total_registros=1,
        )


async def _assert_no_empty_sefaz_cache(cache: Cache) -> None:
    for k in await cache.redis.keys("sefaz:search:*"):
        val = await cache.get_json(k)
        assert isinstance(val, dict), k
        rows = val.get("conteudo")
        assert rows is not None, k
        assert len(rows) > 0, f"empty response must not be cached (key={k})"


@pytest.mark.asyncio
async def test_empty_sefaz_response_is_not_cached():
    settings = Settings()
    cache = Cache(redis_url="redis://localhost:6379/0")
    sefaz = _AlwaysEmptySefaz()
    req = SearchRequest(items=["arroz"])

    resp1 = await run_search(
        req, settings=settings, sefaz=sefaz, llm=MockLLMClient(), cache=cache
    )
    assert sefaz.calls >= 1
    assert resp1.metrics.items_fetch_failed == 0
    await _assert_no_empty_sefaz_cache(cache)
    assert not await cache.redis.keys("sefaz:search:*")

    # Second search with a healthy SEFAZ must re-hit upstream (empty was not cached).
    full = _FullSefaz()
    resp2 = await run_search(
        req, settings=settings, sefaz=full, llm=MockLLMClient(), cache=cache
    )
    assert full.calls >= 1, "must re-fetch when prior empty was not cached"
    assert resp2.metrics.items_fetch_failed == 0
    assert any(s.items_found >= 1 for s in resp2.stores), "fresh non-empty should rank"
    await _assert_no_empty_sefaz_cache(cache)


@pytest.mark.asyncio
async def test_failed_fetch_is_not_cached_and_signals_upstream_failed():
    settings = Settings()
    cache = Cache(redis_url="redis://localhost:6379/0")
    sefaz = _FailingSefaz()
    req = SearchRequest(items=["feijao"])

    resp = await run_search(
        req, settings=settings, sefaz=sefaz, llm=MockLLMClient(), cache=cache
    )

    assert sefaz.calls >= 1
    assert resp.metrics.items_fetch_failed >= 1
    assert resp.metrics.fetch_failed_labels, "must expose failed labels for eval honesty"
    assert not await cache.redis.keys("sefaz:search:*")

    # Retry with a healthy SEFAZ must hit upstream (failure not cached).
    full = _FullSefaz()
    resp2 = await run_search(
        req, settings=settings, sefaz=full, llm=MockLLMClient(), cache=cache
    )
    assert full.calls >= 1
    assert resp2.metrics.items_fetch_failed == 0
    assert any(s.items_found >= 1 for s in resp2.stores)


@pytest.mark.asyncio
async def test_non_empty_response_is_cached():
    settings = Settings()
    cache = Cache(redis_url="redis://localhost:6379/0")
    sefaz = _FullSefaz()
    req = SearchRequest(items=["leite"])

    await run_search(
        req, settings=settings, sefaz=sefaz, llm=MockLLMClient(), cache=cache
    )
    assert sefaz.calls >= 1
    assert await cache.redis.keys("sefaz:search:*"), "non-empty must be cached"
    await _assert_no_empty_sefaz_cache(cache)

    # Same SEFAZ instance: second search should be a cache hit (no extra SEFAZ calls).
    sefaz.calls = 0
    resp2 = await run_search(
        req, settings=settings, sefaz=sefaz, llm=MockLLMClient(), cache=cache
    )
    assert sefaz.calls == 0, "non-empty cache hit must skip SEFAZ"
    assert any(s.items_found >= 1 for s in resp2.stores)


@pytest.mark.asyncio
async def test_poisoned_empty_cache_entry_is_ignored_and_purged():
    """Read-side guard: already-poisoned empty Redis entries must not stick."""
    settings = Settings()
    cache = Cache(redis_url="redis://localhost:6379/0")
    # MockLLM expands "arroz" → "arroz tipo 1" (see mock_client._TERM_EXPAND).
    key = _cache_key(
        "arroz tipo 1",
        MACEIO_LAT,
        MACEIO_LON,
        settings.default_radius_km,
        settings.default_days,
        source="mock",
    )
    empty_payload = PesquisaResponse(conteudo=[], total_registros=0).model_dump(
        by_alias=True
    )
    await cache.set_json(key, empty_payload, ttl=settings.cache_ttl_seconds)
    assert await cache.get_json(key) is not None

    sefaz = _FullSefaz()
    resp = await run_search(
        SearchRequest(items=["arroz"]),
        settings=settings,
        sefaz=sefaz,
        llm=MockLLMClient(),
        cache=cache,
    )
    assert sefaz.calls >= 1, "must re-fetch after ignoring empty cache"
    assert any(s.items_found >= 1 for s in resp.stores)
    cached_after = await cache.get_json(key)
    assert cached_after is not None, "successful re-fetch should re-populate cache"
    assert cached_after.get("conteudo"), "empty poison must be replaced with non-empty"


@pytest.mark.asyncio
async def test_true_empty_is_no_data_not_fetch_failed():
    settings = Settings()
    cache = Cache(redis_url="redis://localhost:6379/0")
    sefaz = _AlwaysEmptySefaz()
    resp = await run_search(
        SearchRequest(items=["xyzzy-unobtainium-99"]),
        settings=settings,
        sefaz=sefaz,
        llm=MockLLMClient(),
        cache=cache,
    )
    assert sefaz.calls >= 1
    assert resp.metrics.items_fetch_failed == 0
    assert resp.metrics.fetch_failed_labels == []
