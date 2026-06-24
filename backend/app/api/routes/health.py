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
        "git_sha": (settings.git_sha or None) or None,
    }


@router.get("/api/v1/client-config")
async def client_config(settings: Settings = Depends(get_settings_dep)) -> dict:
    """Public policy for app/web clients (min versions, update copy) — #268.

    Enforcement is client-side once the Flutter/web gate lands; empty min versions
    mean "no force-update yet" while still giving a stable contract.
    """
    min_app = (settings.min_app_version or "").strip() or None
    min_web = (settings.min_web_build or "").strip() or None
    update_url = (settings.client_update_url or "").strip() or None
    if not update_url:
        # Sensible default: APK / web origin is the same host the API serves.
        update_url = None
    return {
        "policy_version": settings.policy_version,
        "min_app_version": min_app,
        "min_web_build": min_web,
        "update_message": settings.client_update_message,
        "update_url": update_url,
        "force_update": bool(min_app or min_web),
        "git_sha": (settings.git_sha or "").strip() or None,
    }
