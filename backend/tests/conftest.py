from __future__ import annotations

import pytest

from app.services.sefaz.models import (
    Endereco,
    Estabelecimento,
    Produto,
    Registro,
    Venda,
)


def make_registro(
    *,
    descricao: str,
    valor_venda: float,
    unidade_medida: str = "UN",
    cnpj: str = "00000000000100",
    nome: str = "Loja Teste",
    lat: float = -9.65,
    lon: float = -35.71,
    gtin: str | None = "7890000000000",
) -> Registro:
    return Registro(
        produto=Produto(
            codigo="X",
            descricao=descricao,
            descricao_sefaz="",
            gtin=gtin,
            unidade_medida=unidade_medida,
            venda=Venda(
                data_venda="2026-06-01T10:00:00Z",
                valor_declarado=valor_venda,
                valor_venda=valor_venda,
            ),
        ),
        estabelecimento=Estabelecimento(
            cnpj=cnpj,
            razao_social=nome,
            nome_fantasia=nome,
            endereco=Endereco(bairro="Centro", latitude=lat, longitude=lon),
        ),
    )


@pytest.fixture
def registro_factory():
    return make_registro
