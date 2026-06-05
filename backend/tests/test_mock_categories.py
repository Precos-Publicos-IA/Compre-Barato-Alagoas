"""The mock catalog should respect per-store categories."""

import pytest

from app.services.sefaz.mock_client import MockSefazClient

MACEIO = dict(latitude=-9.6498, longitude=-35.7089, radius_km=15, days=7)


@pytest.mark.asyncio
async def test_pharmacy_absent_from_grocery_search():
    client = MockSefazClient()
    resp = await client.search_product(descricao="arroz", **MACEIO)
    names = {r.estabelecimento.nome_fantasia for r in resp.conteudo}
    assert names, "expected some stores for arroz"
    assert "Farmácia Saúde Total" not in names  # pharmacy doesn't sell rice


@pytest.mark.asyncio
async def test_pharmacy_present_for_medicine():
    client = MockSefazClient()
    resp = await client.search_product(descricao="dipirona", **MACEIO)
    names = {r.estabelecimento.nome_fantasia for r in resp.conteudo}
    assert names == {"Farmácia Saúde Total"}  # only the pharmacy sells dipirona


@pytest.mark.asyncio
async def test_uses_nome_fantasia_not_cnpj():
    client = MockSefazClient()
    resp = await client.search_product(descricao="leite", **MACEIO)
    for r in resp.conteudo:
        assert r.estabelecimento.nome_fantasia
        assert r.estabelecimento.nome_fantasia != r.estabelecimento.cnpj
