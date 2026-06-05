"""SEFAZ client interface.

The rest of the app depends only on this Protocol, so the mock and real HTTP clients
are interchangeable. The real client is the *only* place the secret ``AppToken`` is
used — clients of our API never see it.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import PesquisaResponse


@runtime_checkable
class SefazClient(Protocol):
    #: "mock" or "sefaz" — surfaced in the API response for transparency.
    source_name: str

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
        """Run ``produto/pesquisa`` with exactly one product criterion."""
        ...

    async def aclose(self) -> None:  # pragma: no cover - trivial
        ...
