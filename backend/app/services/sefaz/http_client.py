"""Real SEFAZ HTTP client (used only when ``USE_MOCK_SEFAZ=false``).

This is the single place the secret ``AppToken`` is attached. It builds the
``produto/pesquisa`` body exactly as the manual (section 6.1.1) specifies: one product
criterion (gtin OR descricao) and a geolocation establishment criterion.
"""

from __future__ import annotations

import logging

import httpx

from .models import PesquisaResponse

logger = logging.getLogger(__name__)


class SefazApiError(RuntimeError):
    """Raised when SEFAZ returns an error payload (timestamp + message)."""


class HttpSefazClient:
    source_name = "sefaz"

    def __init__(
        self, base_url: str, app_token: str, timeout: float = 15.0
    ) -> None:
        if not app_token:
            raise ValueError("SEFAZ AppToken is required for the real client")
        # The manual's base URL ends with a slash; endpoints are relative.
        self._endpoint = base_url.rstrip("/") + "/produto/pesquisa"
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"AppToken": app_token, "Content-Type": "application/json"},
        )

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
        if bool(descricao) == bool(gtin):
            raise ValueError("provide exactly one of descricao or gtin")

        produto: dict = {"gtin": gtin} if gtin else {"descricao": descricao}
        body = {
            "produto": produto,
            "estabelecimento": {
                "geolocalizacao": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "raio": radius_km,
                }
            },
            "dias": days,
            "pagina": pagina,
            "registrosPorPagina": registros_por_pagina,
        }

        resp = await self._client.post(self._endpoint, json=body)
        data = resp.json()

        # SEFAZ returns an error object {timestamp, message} on failure.
        if isinstance(data, dict) and "message" in data and "conteudo" not in data:
            raise SefazApiError(data.get("message", "SEFAZ error"))
        resp.raise_for_status()
        return PesquisaResponse.model_validate(data)

    async def aclose(self) -> None:
        await self._client.aclose()
