"""Admin dashboard API — read-only product/AI metrics, guarded by a bearer token.

Served under /admin/api/* and proxied by nginx on the admin subdomain. All data
comes from the Redis-native Analytics store. The token is the single gate: if
``ADMIN_TOKEN`` is unset the whole namespace fails closed (401).
"""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from ...analytics import Analytics
from ...config import Settings
from ..deps import get_analytics, get_settings_dep

router = APIRouter(prefix="/admin/api", tags=["admin"])


def require_admin(
    request: Request,
    settings: Settings = Depends(get_settings_dep),
) -> None:
    """Constant-time bearer-token check. Fails closed when no token is configured."""
    configured = settings.admin_token
    auth = request.headers.get("authorization", "")
    presented = ""
    if auth.lower().startswith("bearer "):
        presented = auth[7:].strip()
    else:
        presented = request.headers.get("x-admin-token", "")
    if not configured or not presented or not hmac.compare_digest(presented, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso negado.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/overview", dependencies=[Depends(require_admin)])
async def overview(
    analytics: Analytics = Depends(get_analytics),
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    data = await analytics.overview()
    # Surface mode so the UI can badge "custo estimado" while in mock mode.
    data["use_mock_sefaz"] = settings.use_mock_sefaz
    data["use_mock_llm"] = settings.use_mock_llm
    data["llm_model"] = settings.llm_model
    data["policy_version"] = settings.policy_version
    return data


@router.get("/quality", dependencies=[Depends(require_admin)])
async def quality(
    days: int = Query(14, ge=1, le=90),
    analytics: Analytics = Depends(get_analytics),
) -> dict:
    return await analytics.quality(days)


@router.get("/costs", dependencies=[Depends(require_admin)])
async def costs(
    days: int = Query(14, ge=1, le=90),
    analytics: Analytics = Depends(get_analytics),
) -> dict:
    return await analytics.costs(days)


@router.get("/searches", dependencies=[Depends(require_admin)])
async def searches(
    limit: int = Query(50, ge=1, le=200),
    analytics: Analytics = Depends(get_analytics),
) -> dict:
    return {"items": await analytics.recent_searches(limit)}


@router.get("/items", dependencies=[Depends(require_admin)])
async def items(
    days: int = Query(14, ge=1, le=90),
    analytics: Analytics = Depends(get_analytics),
) -> dict:
    return await analytics.items(days)


@router.get("/feedback", dependencies=[Depends(require_admin)])
async def feedback(
    limit: int = Query(50, ge=1, le=200),
    kind: str | None = Query(None),
    analytics: Analytics = Depends(get_analytics),
) -> dict:
    return await analytics.feedback(limit, kind)


@router.get("/timings", dependencies=[Depends(require_admin)])
async def timings(
    days: int = Query(14, ge=1, le=90),
    analytics: Analytics = Depends(get_analytics),
) -> dict:
    """Response-time distribution/trend + per-subsystem latency."""
    return await analytics.timings(days)


@router.get("/providers", dependencies=[Depends(require_admin)])
async def providers(
    days: int = Query(14, ge=1, le=90),
    analytics: Analytics = Depends(get_analytics),
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    """Latency + error rate per third party (AI, SEFAZ). Echoes mock flags so the
    UI can badge mock providers (which never error and are ~0ms)."""
    data = await analytics.providers(days)
    data["use_mock_sefaz"] = settings.use_mock_sefaz
    data["use_mock_llm"] = settings.use_mock_llm
    data["llm_model"] = settings.llm_model
    return data
