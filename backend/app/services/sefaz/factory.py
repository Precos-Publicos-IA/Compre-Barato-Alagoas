"""Pick the SEFAZ client implementation based on settings."""

from __future__ import annotations

from ...config import Settings
from ..secrets import SecretStore
from .base import SefazClient


def build_sefaz_client(
    settings: Settings, secrets: SecretStore | None = None
) -> SefazClient:
    if settings.use_mock_sefaz:
        from .mock_client import MockSefazClient

        return MockSefazClient()

    from .http_client import HttpSefazClient

    async def token_provider() -> str | None:
        # Prefer the encrypted, admin-managed token; fall back to the env var
        # (bootstrap/legacy). The token is never captured at startup so it can be
        # set or rotated from the admin panel without a restart.
        if secrets is not None:
            stored = await secrets.get_secret("sefaz_token")
            if stored:
                return stored
        return settings.sefaz_app_token or None

    return HttpSefazClient(
        base_url=settings.sefaz_base_url,
        token_provider=token_provider,
        timeout=settings.sefaz_timeout_seconds,
    )
