"""Pick the SEFAZ client implementation based on settings."""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from ...config import Settings
from ..secrets import SecretStore
from .base import SefazClient
from .models import PesquisaResponse

logger = logging.getLogger(__name__)


TokenProvider = Callable[[], Awaitable[str | None]]


class RoutingSefazClient:
    """Use the official API when an AppToken is available; otherwise the website.

    Token is resolved **per request** so an admin-panel rotation takes effect without
    restart, and so we can live without a token (web scrape) until SEFAZ issues one.

    If a token is present but the official API errors/times out (upstream outage,
    bad TLS, invalid token), fall back to the public website so searches stay useful
    instead of returning empty baskets.
    """

    # Stable cache namespace (must not flip between "web"/"sefaz" mid-basket).
    cache_namespace = "auto"

    def __init__(
        self,
        *,
        http: SefazClient,
        web: SefazClient,
        token_provider: TokenProvider,
    ) -> None:
        self._http = http
        self._web = web
        self._token_provider = token_provider
        self._last_source = "auto"

    @property
    def source_name(self) -> str:
        # Surface the source of the most recent call (health/admin friendliness).
        return self._last_source

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
        token = await self._token_provider()
        if token:
            try:
                resp = await self._http.search_product(
                    descricao=descricao,
                    gtin=gtin,
                    latitude=latitude,
                    longitude=longitude,
                    radius_km=radius_km,
                    days=days,
                    pagina=pagina,
                    registros_por_pagina=registros_por_pagina,
                )
                # Dead official host sometimes returns 200 with empty conteudo while
                # the public website still has rows. Prefer web over a false no_data.
                if resp.conteudo:
                    self._last_source = self._http.source_name
                    return resp
                logger.warning(
                    "Official SEFAZ API returned empty for %r; falling back to website",
                    (descricao or gtin or "")[:80],
                )
            except Exception as exc:
                # Keep the message short; never log the token.
                logger.warning(
                    "Official SEFAZ API failed (%s: %s); falling back to website",
                    type(exc).__name__,
                    exc,
                )
        self._last_source = self._web.source_name
        return await self._web.search_product(
            descricao=descricao,
            gtin=gtin,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            days=days,
            pagina=pagina,
            registros_por_pagina=registros_por_pagina,
        )

    async def aclose(self) -> None:
        await self._http.aclose()
        await self._web.aclose()


def _token_provider(
    settings: Settings, secrets: SecretStore | None
) -> TokenProvider:
    async def provider() -> str | None:
        if secrets is not None:
            stored = await secrets.get_secret("sefaz_token")
            if stored:
                return stored
        return settings.resolved_sefaz_app_token or None

    return provider


def build_sefaz_client(
    settings: Settings, secrets: SecretStore | None = None
) -> SefazClient:
    if settings.use_mock_sefaz:
        from .mock_client import MockSefazClient

        return MockSefazClient()

    from .http_client import HttpSefazClient
    from .web_client import WebSefazClient

    token_provider = _token_provider(settings, secrets)
    web = WebSefazClient(
        base_url=settings.sefaz_web_base_url,
        timeout=settings.sefaz_web_timeout_seconds,
        max_cards=settings.sefaz_web_max_cards,
        max_bytes=settings.sefaz_web_max_bytes,
        concurrency=settings.sefaz_web_concurrency,
    )

    # Force website even if a token exists (debug / token broken).
    if settings.use_web_sefaz:
        return web

    http = HttpSefazClient(
        base_url=settings.sefaz_base_url,
        token_provider=token_provider,
        timeout=settings.sefaz_timeout_seconds,
    )
    # Auto: API when token is present, website otherwise (no token from SEFAZ yet).
    return RoutingSefazClient(http=http, web=web, token_provider=token_provider)
