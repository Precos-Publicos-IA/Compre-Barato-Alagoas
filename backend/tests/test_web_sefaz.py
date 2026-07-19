"""Unit tests for the tokenless Economiza website client."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.sefaz.factory import RoutingSefazClient, build_sefaz_client  # Routing kept for unit tests only
from app.services.sefaz.web_client import (
    WebSefazClient,
    _filter_relevant,
    parse_cards,
    parse_categories,
    pick_category,
)
from app.services.sefaz.models import (
    Endereco,
    Estabelecimento,
    PesquisaResponse,
    Produto,
    Registro,
    Venda,
)
from app.config import Settings

FIX = Path(__file__).parent / "fixtures"


def test_parse_cards_fixture():
    html = (FIX / "economiza_web_cards.html").read_text(encoding="utf-8")
    rows = parse_cards(html)
    assert len(rows) == 2
    rice = rows[0]
    assert "ARROZ" in rice.produto.descricao.upper()
    assert rice.produto.venda.valor_venda == pytest.approx(24.90)
    assert rice.produto.gtin == "7893500018469"
    assert rice.estabelecimento.nome_fantasia == "MIX MATEUS"
    assert rice.estabelecimento.cnpj.startswith("web:")
    assert rice.estabelecimento.endereco is not None
    assert rice.estabelecimento.endereco.bairro

    milk = rows[1]
    assert milk.produto.venda.valor_venda == pytest.approx(4.59)
    assert "LEITE" in milk.produto.descricao.upper()


def test_parse_categories_and_pick():
    html = (FIX / "economiza_web_categories.html").read_text(encoding="utf-8")
    cats = parse_categories(html)
    assert cats == [(50_000_000, 165), (53_000_000, 3)]
    assert pick_category(cats) == 50_000_000
    assert pick_category([(1, 10), (2, 99)]) == 2
    assert pick_category([]) is None


def test_parse_cards_respects_max():
    html = (FIX / "economiza_web_cards.html").read_text(encoding="utf-8")
    assert len(parse_cards(html, max_cards=1)) == 1


def test_factory_forces_web():
    settings = Settings(use_mock_sefaz=False, use_web_sefaz=True, sefaz_app_token="")
    client = build_sefaz_client(settings, None)
    assert isinstance(client, WebSefazClient)
    assert client.source_name == "web"


def test_factory_official_api_without_web():
    """Default live path is the official JSON API only (no website scraper)."""
    from app.services.sefaz.http_client import HttpSefazClient

    settings = Settings(use_mock_sefaz=False, use_web_sefaz=False, sefaz_app_token="tok")
    client = build_sefaz_client(settings, None)
    assert isinstance(client, HttpSefazClient)
    assert client.source_name == "sefaz"
    assert client.cache_namespace == "sefaz"


def test_factory_mock_unchanged():
    settings = Settings(use_mock_sefaz=True)
    client = build_sefaz_client(settings, None)
    assert client.source_name == "mock"


@pytest.mark.asyncio
async def test_web_client_page_two_empty():
    client = WebSefazClient()
    resp = await client.search_product(
        descricao="arroz",
        latitude=-9.66,
        longitude=-35.7,
        radius_km=8,
        days=7,
        pagina=2,
    )
    assert resp.conteudo == []
    assert resp.pagina == 2


def _row(desc: str, price: float = 10.0) -> Registro:
    return Registro(
        produto=Produto(
            descricao=desc,
            unidade_medida="UN",
            venda=Venda(valor_venda=price, valor_declarado=price),
        ),
        estabelecimento=Estabelecimento(
            cnpj="web:1",
            nome_fantasia="Loja",
            endereco=Endereco(bairro="Centro"),
        ),
    )


def test_filter_relevant_rejects_pet_and_prefers_real_rice():
    rows = [
        _row("DOG CHOW CARNE ARROZ 15KG", 50),
        _row("ARROZ TIO JOAO TIPO 1 5KG", 25),
        _row("ARROZ CAMIL TIPO 1 1KG", 5),
        _row("ARROZ P CAES LUPPY 5KG", 15),
    ]
    kept = _filter_relevant(rows, "arroz 5kg")
    descs = " ".join(r.produto.descricao.upper() for r in kept)
    assert "TIO JOAO" in descs or "CAMIL" in descs
    assert "CAES" not in descs and "DOG CHOW" not in descs


def test_filter_relevant_drops_candy_keeps_milk():
    rows = [
        _row("BALA CARAMELO LEITE 660G"),
        _row("LEITE INTEGRAL ITALAC 1L"),
    ]
    kept = _filter_relevant(rows, "leite")
    assert len(kept) == 1
    assert "ITALAC" in kept[0].produto.descricao.upper()


@pytest.mark.asyncio
async def test_routing_falls_back_to_web_when_api_fails():
    """Token present but official API errors → website path, not empty basket."""

    class BoomHttp:
        source_name = "sefaz"
        cache_namespace = "sefaz"

        async def search_product(self, **kwargs):
            raise RuntimeError("upstream timeout")

        async def aclose(self):
            return None

    class StubWeb:
        source_name = "web"
        cache_namespace = "web"

        async def search_product(self, **kwargs):
            return PesquisaResponse(conteudo=[_row("ARROZ CAMIL 1KG")], total_paginas=1)

        async def aclose(self):
            return None

    async def token():
        return "dummy-token"

    client = RoutingSefazClient(http=BoomHttp(), web=StubWeb(), token_provider=token)
    resp = await client.search_product(
        descricao="arroz",
        latitude=-9.66,
        longitude=-35.7,
        radius_km=8,
        days=7,
    )
    assert client.source_name == "web"
    assert len(resp.conteudo) == 1
    assert "ARROZ" in resp.conteudo[0].produto.descricao.upper()


@pytest.mark.asyncio
async def test_routing_falls_back_to_web_when_api_returns_empty():
    """Token present but official API returns empty conteudo → website path."""

    class EmptyHttp:
        source_name = "sefaz"
        cache_namespace = "sefaz"

        async def search_product(self, **kwargs):
            return PesquisaResponse(conteudo=[], total_paginas=1)

        async def aclose(self):
            return None

    class StubWeb:
        source_name = "web"
        cache_namespace = "web"

        async def search_product(self, **kwargs):
            return PesquisaResponse(conteudo=[_row("ARROZ CAMIL 1KG")], total_paginas=1)

        async def aclose(self):
            return None

    async def token():
        return "dummy-token"

    client = RoutingSefazClient(http=EmptyHttp(), web=StubWeb(), token_provider=token)
    resp = await client.search_product(
        descricao="arroz",
        latitude=-9.66,
        longitude=-35.7,
        radius_km=8,
        days=7,
    )
    assert client.source_name == "web"
    assert len(resp.conteudo) == 1
