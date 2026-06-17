"""A failing SEFAZ fetch for one item must not fail the whole basket search.

This guards the concurrent + resilient per-item fetch in search_service: one item
raising should yield *partial* results (the other items still rank) instead of a 502.
"""

from __future__ import annotations

import pytest

from app.cache import Cache
from app.config import Settings
from app.schemas.search import SearchRequest
from app.services.llm.mock_client import MockLLMClient
from app.services.search_service import run_search
from app.services.sefaz.models import PesquisaResponse

from .conftest import make_registro


class _FlakySefaz:
    """Returns offers for every term except 'feijao', for which it raises."""

    source_name = "mock"

    async def search_product(self, *, descricao=None, **kwargs) -> PesquisaResponse:
        if descricao and "feijao" in descricao.lower():
            raise RuntimeError("SEFAZ exploded for feijao")
        return PesquisaResponse(
            conteudo=[make_registro(descricao=f"{descricao} 1KG", valor_venda=8.0)]
        )

    async def aclose(self) -> None:  # pragma: no cover - trivial
        pass


@pytest.mark.asyncio
async def test_partial_results_when_one_item_fails():
    settings = Settings()
    cache = Cache(redis_url="redis://localhost:6379/0")
    req = SearchRequest(items=["arroz", "feijao"])

    resp = await run_search(
        req,
        settings=settings,
        sefaz=_FlakySefaz(),
        llm=MockLLMClient(),
        cache=cache,
    )

    # arroz still produced a store; feijao is simply missing — no exception, no 502.
    assert resp.stores, "expected partial results from the surviving item"
    assert any(s.items_found >= 1 for s in resp.stores)
    assert "feijao" in resp.stores[0].missing or all(
        i.query != "feijao" for s in resp.stores for i in s.items
    )
