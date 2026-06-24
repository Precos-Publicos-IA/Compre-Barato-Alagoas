"""Liveness / config introspection endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ...config import Settings
from ..deps import enforce_rate_limit, get_settings_dep

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    # Light IP-hash throttle so public edge probes cannot infinite-scrape (#364).
    # Compose healthcheck interval (30s) stays well under normal daily limits.
    dependencies=[Depends(enforce_rate_limit)],
)
async def health(
    request: Request, settings: Settings = Depends(get_settings_dep)
) -> dict:
    # Production: minimal liveness only — no mock/env recon on the public app host
    # (#144, #364). Non-production keeps full diagnostics for local/CI tests.
    if settings.environment.strip().lower() == "production":
        return {"status": "ok"}
    return {
        "status": "ok",
        "environment": settings.environment,
        "data_source": request.app.state.sefaz.source_name,
        "llm_source": request.app.state.llm.source_name,
        "cache_backend": request.app.state.cache.backend_name,
        "use_mock_sefaz": settings.use_mock_sefaz,
        "use_mock_llm": settings.use_mock_llm,
    }
