"""Staple prewarm list + empty-cache policy guards for B2 reliability."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.sefaz.staples import (
    CORE_STAPLE_FETCH_SET,
    STAPLE_FETCH_TERMS,
    STAPLE_RAG_MAPPINGS,
    unique_fetch_terms,
)


def test_staple_rag_mappings_well_formed():
    assert len(STAPLE_RAG_MAPPINGS) >= 30
    for user, effective, weight in STAPLE_RAG_MAPPINGS:
        assert isinstance(user, str) and user.strip()
        assert isinstance(effective, str) and effective.strip()
        assert isinstance(weight, int) and weight > 0


def test_staple_fetch_terms_cover_core_basket():
    terms = {t.casefold() for t in unique_fetch_terms()}
    required = {
        "arroz",
        "feijao",
        "leite",
        "acucar",
        "oleo",
        "pao",
        "cafe",
        "ovos",
    }
    missing = required - terms
    assert not missing, f"core staples missing from fetch list: {missing}"
    # Every core token should appear in either fetch list or RAG mappings.
    rag_users = {u.casefold() for u, _, _ in STAPLE_RAG_MAPPINGS}
    for core in CORE_STAPLE_FETCH_SET:
        assert core.casefold() in terms or core.casefold() in rag_users


def test_unique_fetch_terms_dedupes_case():
    assert unique_fetch_terms(["Arroz", "arroz", "leite"]) == ["Arroz", "leite"]
    assert unique_fetch_terms([]) == []
    # Default list has no internal case-dups.
    base = unique_fetch_terms(STAPLE_FETCH_TERMS)
    assert len(base) == len(STAPLE_FETCH_TERMS)


def test_prewarm_script_exists_and_imports_shared_list():
    script = Path(__file__).resolve().parents[1] / "scripts" / "prewarm_staples.py"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "STAPLE_RAG_MAPPINGS" in text
    assert "STAPLE_FETCH_TERMS" in text
    assert "--fetch" in text
    assert "--skip-rag" in text


def test_deploy_prewarm_shell_lists_core_staples():
    shell = (
        Path(__file__).resolve().parents[2] / "deploy" / "prewarm-staples.sh"
    )
    assert shell.is_file(), "deploy/prewarm-staples.sh must ship for post-deploy warm"
    text = shell.read_text(encoding="utf-8")
    for term in ("arroz", "feijao", "leite", "acucar", "oleo", "pao"):
        assert term in text
    assert "api/v1/search" in text
    assert "PREWARM_STRICT" in text


@pytest.mark.asyncio
async def test_successful_staple_hit_is_cached_empty_is_not():
    """Regression: non-empty cache stick; empty never cached (B2 + empty-cache)."""
    from app.cache import Cache
    from app.config import Settings
    from app.schemas.search import SearchRequest
    from app.services.llm.mock_client import MockLLMClient
    from app.services.search_service import run_search
    from app.services.sefaz.models import PesquisaResponse

    from .conftest import make_registro

    class _Sefaz:
        source_name = "mock"
        cache_namespace = "mock"
        calls = 0

        async def search_product(self, *, descricao=None, **kwargs):
            self.calls += 1
            if descricao and "vazio" in (descricao or "").lower():
                return PesquisaResponse(conteudo=[], total_registros=0)
            return PesquisaResponse(
                conteudo=[
                    make_registro(descricao=f"{descricao or 'item'} 1KG", valor_venda=4.5)
                ],
                total_registros=1,
            )

        async def aclose(self):
            pass

    settings = Settings()
    cache = Cache(redis_url="redis://localhost:6379/0")
    sefaz = _Sefaz()

    r1 = await run_search(
        SearchRequest(items=["arroz"]),
        settings=settings,
        sefaz=sefaz,
        llm=MockLLMClient(),
        cache=cache,
    )
    assert r1.metrics.items_fetch_failed == 0
    assert await cache.redis.keys("sefaz:search:*")
    sefaz.calls = 0
    await run_search(
        SearchRequest(items=["arroz"]),
        settings=settings,
        sefaz=sefaz,
        llm=MockLLMClient(),
        cache=cache,
    )
    assert sefaz.calls == 0, "successful staple hit must stick in cache"

    # Wipe keys so empty path is isolated.
    for k in await cache.redis.keys("sefaz:search:*"):
        await cache.delete(k)
    sefaz.calls = 0
    r_empty = await run_search(
        SearchRequest(items=["vazio total"]),
        settings=settings,
        sefaz=sefaz,
        llm=MockLLMClient(),
        cache=cache,
    )
    assert r_empty.metrics.items_fetch_failed == 0
    assert not await cache.redis.keys("sefaz:search:*")
