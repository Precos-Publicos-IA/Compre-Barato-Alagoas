"""Pick the SEFAZ client implementation based on settings."""

from __future__ import annotations

from ...config import Settings
from .base import SefazClient


def build_sefaz_client(settings: Settings) -> SefazClient:
    if settings.use_mock_sefaz:
        from .mock_client import MockSefazClient

        return MockSefazClient()

    from .http_client import HttpSefazClient

    return HttpSefazClient(
        base_url=settings.sefaz_base_url,
        app_token=settings.sefaz_app_token,
        timeout=settings.sefaz_timeout_seconds,
    )
