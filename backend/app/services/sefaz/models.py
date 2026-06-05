"""Pydantic models mirroring the SEFAZ ``produto/pesquisa`` response layout.

Field names follow the manual's JSON (camelCase / Portuguese) via aliases so the same
models work for the real HTTP client and the mock client. See manual section 6.1.2.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Camel(BaseModel):
    # Accept the API's camelCase keys but allow population by field name too.
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class Venda(_Camel):
    data_venda: str | None = Field(default=None, alias="dataVenda")
    valor_declarado: float | None = Field(default=None, alias="valorDeclarado")
    valor_venda: float = Field(alias="valorVenda")


class Endereco(_Camel):
    nome_logradouro: str | None = Field(default=None, alias="nomeLogradouro")
    numero_imovel: str | None = Field(default=None, alias="numeroImovel")
    bairro: str | None = None
    cep: str | None = None
    codigo_ibge: str | None = Field(default=None, alias="codigoIBGE")
    municipio: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class Estabelecimento(_Camel):
    cnpj: str
    razao_social: str | None = Field(default=None, alias="razaoSocial")
    nome_fantasia: str | None = Field(default=None, alias="nomeFantasia")
    telefone: str | None = None
    endereco: Endereco | None = None


class Produto(_Camel):
    codigo: str | None = None
    descricao: str
    descricao_sefaz: str | None = Field(default=None, alias="descricaoSefaz")
    gtin: str | None = None
    ncm: str | None = None
    gpc: int | str | None = None
    unidade_medida: str | None = Field(default=None, alias="unidadeMedida")
    # The manual nests the sale (`venda`) inside `produto` (section 8.1.8).
    venda: Venda | None = None


class Registro(_Camel):
    """One row of the ``conteudo`` list: a product sold at an establishment."""

    produto: Produto
    estabelecimento: Estabelecimento


class PesquisaResponse(_Camel):
    total_registros: int = Field(default=0, alias="totalRegistros")
    total_paginas: int = Field(default=1, alias="totalPaginas")
    pagina: int = 1
    registros_por_pagina: int = Field(default=0, alias="registrosPorPagina")
    registros_pagina: int = Field(default=0, alias="registrosPagina")
    primeira_pagina: bool = Field(default=True, alias="primeiraPagina")
    ultima_pagina: bool = Field(default=True, alias="ultimaPagina")
    conteudo: list[Registro] = Field(default_factory=list)
