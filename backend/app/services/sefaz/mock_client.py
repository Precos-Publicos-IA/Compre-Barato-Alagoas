"""Deterministic mock SEFAZ client.

Loads ``app/data/mock_sefaz.json`` and synthesizes ``produto/pesquisa`` responses so
the whole stack runs and is testable with no token and no network. Matching is by
accent-insensitive keyword; prices vary per store via ``price_factor`` plus a small
deterministic jitter so rankings are non-trivial.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from ..geo import haversine_km
from .models import (
    Endereco,
    Estabelecimento,
    PesquisaResponse,
    Produto,
    Registro,
    Venda,
)

_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "mock_sefaz.json"


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


@lru_cache
def _load_catalog() -> dict:
    with _DATA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _jitter(cnpj: str, gtin: str) -> float:
    """Stable per (store, product) multiplier in roughly [0.98, 1.02]."""
    h = hashlib.sha256(f"{cnpj}:{gtin}".encode()).digest()[0]
    return 1.0 + ((h % 5) - 2) / 100.0


class MockSefazClient:
    source_name = "mock"

    def __init__(self) -> None:
        self._catalog = _load_catalog()

    async def search_product(
        self,
        *,
        descricao: str | None = None,
        gtin: str | None = None,
        latitude: float,
        longitude: float,
        radius_km: int,
        days: int,
        pagina: int = 1,
        registros_por_pagina: int = 500,
    ) -> PesquisaResponse:
        products = self._match_products(descricao=descricao, gtin=gtin)
        stores = self._stores_in_radius(latitude, longitude, radius_km)

        now = datetime.now(timezone.utc)
        registros: list[Registro] = []
        for prod in products:
            category = prod.get("category")
            for store in stores:
                # A store only sells product families in its categories
                # (so a pharmacy doesn't show up selling rice).
                store_cats = store.get("categories")
                if category and store_cats and category not in store_cats:
                    continue
                registros.append(self._build_registro(prod, store, days, now))

        return PesquisaResponse.model_validate(
            {
                "totalRegistros": len(registros),
                "totalPaginas": 1,
                "pagina": 1,
                "registrosPorPagina": registros_por_pagina,
                "registrosPagina": len(registros),
                "primeiraPagina": True,
                "ultimaPagina": True,
                "conteudo": [r.model_dump(by_alias=True) for r in registros],
            }
        )

    # --- internals ---
    def _match_products(
        self, *, descricao: str | None, gtin: str | None
    ) -> list[dict]:
        all_products = self._catalog["products"]
        if gtin:
            return [p for p in all_products if p.get("gtin") == gtin]
        if not descricao:
            return []
        query = _strip_accents(descricao)
        query_tokens = set(query.split())
        matches = []
        for p in all_products:
            keywords = {_strip_accents(k) for k in p.get("keywords", [])}
            desc = _strip_accents(p["descricao"])
            if (
                any(k in query or query in k for k in keywords)
                or query_tokens & {w for k in keywords for w in k.split()}
                or any(tok in desc for tok in query_tokens if len(tok) >= 3)
            ):
                matches.append(p)
        return matches

    def _stores_in_radius(
        self, lat: float, lon: float, radius_km: int
    ) -> list[dict]:
        out = []
        for store in self._catalog["stores"]:
            e = store["endereco"]
            dist = haversine_km(lat, lon, e["latitude"], e["longitude"])
            if dist <= radius_km:
                out.append(store)
        return out

    def _build_registro(
        self, prod: dict, store: dict, days: int, now: datetime
    ) -> Registro:
        gtin = prod.get("gtin") or ""
        factor = store["price_factor"] * _jitter(store["cnpj"], gtin)
        valor_venda = round(prod["base_price"] * factor, 2)
        valor_declarado = round(valor_venda * 1.03, 2)

        # Deterministic recent sale date within the requested window.
        h = hashlib.sha256(f"{store['cnpj']}:{gtin}:date".encode()).digest()[0]
        sale_dt = now - timedelta(
            days=h % max(days, 1), hours=h % 24, minutes=h % 60
        )
        data_venda = sale_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        e = store["endereco"]
        return Registro(
            produto=Produto(
                codigo=str(prod.get("gtin") or prod["descricao"][:10]),
                descricao=prod["descricao"],
                descricao_sefaz="",
                gtin=prod.get("gtin") or None,
                ncm=prod.get("ncm"),
                gpc=prod.get("gpc"),
                unidade_medida=prod.get("unidadeMedida"),
                venda=Venda(
                    data_venda=data_venda,
                    valor_declarado=valor_declarado,
                    valor_venda=valor_venda,
                ),
            ),
            estabelecimento=Estabelecimento(
                cnpj=store["cnpj"],
                razao_social=store.get("razaoSocial"),
                nome_fantasia=store.get("nomeFantasia"),
                telefone=store.get("telefone"),
                endereco=Endereco(
                    nome_logradouro=e.get("nomeLogradouro"),
                    numero_imovel=e.get("numeroImovel"),
                    bairro=e.get("bairro"),
                    cep=e.get("cep"),
                    codigo_ibge=e.get("codigoIBGE"),
                    municipio=e.get("municipio"),
                    latitude=e.get("latitude"),
                    longitude=e.get("longitude"),
                ),
            ),
        )

    async def aclose(self) -> None:  # pragma: no cover - nothing to close
        return None
