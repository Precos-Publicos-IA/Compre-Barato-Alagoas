"""Real SEFAZ HTTP client (used only when ``USE_MOCK_SEFAZ=false``).

This is the single place the secret ``AppToken`` is attached. It builds the
``produto/pesquisa`` body exactly as the manual (section 6.1.1) specifies: one product
criterion (gtin OR descricao) and a geolocation establishment criterion.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

import httpx

from .models import PesquisaResponse

logger = logging.getLogger(__name__)

# Returns the current SEFAZ AppToken (from the encrypted secret store, with an env
# fallback), or None if none is configured. Resolved per request so a token set or
# rotated via the admin panel takes effect without a restart.
TokenProvider = Callable[[], Awaitable[str | None]]


class SefazApiError(RuntimeError):
    """Raised when SEFAZ returns an error payload (timestamp + message)."""


class HttpSefazClient:
    source_name = "sefaz"
    cache_namespace = "sefaz"

    def __init__(
        self,
        base_url: str,
        token_provider: TokenProvider,
        timeout: float = 15.0,
    ) -> None:
        # The manual's base URL ends with a slash; endpoints are relative.
        self._endpoint = base_url.rstrip("/") + "/produto/pesquisa"
        self._token_provider = token_provider
        # The token is attached per request (never stored on the long-lived client),
        # so rotation takes effect immediately and it's not held in client state.
        # Explicit connect/read/write/pool timeouts and a bounded connection pool keep
        # a slow SEFAZ from exhausting sockets or stalling on connect (issue #225).
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=5.0, pool=5.0),
            # Higher pool so bulk/parallel searches (and multi-item baskets) are not
            # serialized on a tiny connection limit.
            limits=httpx.Limits(max_connections=64, max_keepalive_connections=32),
            headers={"Content-Type": "application/json"},
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

        token = await self._token_provider()
        if not token:
            raise SefazApiError(
                "SEFAZ token not configured. Set it in the admin panel."
            )

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

        resp = await self._client.post(
            self._endpoint, json=body, headers={"AppToken": token}
        )
        data = resp.json()

        # SEFAZ returns an error object {timestamp, message} on failure.
        if isinstance(data, dict) and "message" in data and "conteudo" not in data:
            raise SefazApiError(data.get("message", "SEFAZ error"))
        resp.raise_for_status()
        return PesquisaResponse.model_validate(data)

    async def aclose(self) -> None:
        await self._client.aclose()
