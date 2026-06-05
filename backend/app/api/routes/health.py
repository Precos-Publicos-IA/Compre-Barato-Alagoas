"""Liveness / config introspection endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ...config import Settings
from ..deps import get_settings_dep

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    request: Request, settings: Settings = Depends(get_settings_dep)
) -> dict:
    return {
        "status": "ok",
        "environment": settings.environment,
        "data_source": request.app.state.sefaz.source_name,
        "llm_source": request.app.state.llm.source_name,
        "cache_backend": request.app.state.cache.backend_name,
        "use_mock_sefaz": settings.use_mock_sefaz,
        "use_mock_llm": settings.use_mock_llm,
    }
