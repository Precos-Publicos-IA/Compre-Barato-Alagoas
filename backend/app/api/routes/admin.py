"""Admin dashboard API — read-only product/AI metrics, guarded by a bearer token.

Served under /admin/api/* and proxied by nginx on the admin subdomain. All data
comes from the Redis-native Analytics store. The token is the single gate: if
``ADMIN_TOKEN`` is unset the whole namespace fails closed (401).
"""

from __future__ import annotations

import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator

from ...analytics import Analytics
from ...cache import Cache
from ...config import Settings
from ...services.secrets import MANAGED_SECRETS, SecretStore, SecretStoreUnavailable
from ..deps import _client_id, get_analytics, get_cache, get_secrets, get_settings_dep

router = APIRouter(prefix="/admin/api", tags=["admin"])

# Failed admin auths per client IP per hour before further bad attempts are locked
# out (429). A valid token always succeeds and clears the counter, so a legitimate
# operator is never blocked — only brute-forcing of the static bearer token (#163).
_ADMIN_MAX_FAILS = 10
_ADMIN_FAIL_TTL = 3600


async def require_admin(
    request: Request,
    settings: Settings = Depends(get_settings_dep),
    cache: Cache = Depends(get_cache),
) -> None:
    """Constant-time bearer-token check with per-IP brute-force throttling.
    Fails closed when no token is configured."""
    configured = settings.admin_token
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        presented = auth[7:].strip()
    else:
        presented = request.headers.get("x-admin-token", "")

    today = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    fail_key = f"adminfail:{today}:{_client_id(request, settings.ratelimit_salt)}"

    # hmac.compare_digest raises TypeError on non-ASCII str input; a token with
    # accented/emoji bytes must read as a clean 401, never a 500 (issue #329).
    valid = bool(
        configured
        and presented
        and presented.isascii()
        and hmac.compare_digest(presented, configured)
    )
    if valid:
        await cache.delete(fail_key)  # legit operator: reset the brute-force counter
        return

    fails = await cache.incr_with_ttl(fail_key, ttl=_ADMIN_FAIL_TTL)
    if fails > _ADMIN_MAX_FAILS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Tente novamente mais tarde.",
        )
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


@router.get("/growth", dependencies=[Depends(require_admin)])
async def growth(
    days: int = Query(14, ge=1, le=90),
    analytics: Analytics = Depends(get_analytics),
) -> dict:
    """User-growth metrics: DAU/WAU/MAU, new-vs-returning, activity by hour & weekday."""
    return await analytics.growth(days)


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


class SecretIn(BaseModel):
    # Managed secrets are short (API tokens, a Fernet key). Bound the body so an
    # oversized PUT can't be used to bloat Redis/memory (issue #394).
    value: str = Field(..., max_length=4096)

    @field_validator("value")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("valor vazio")
        return v


async def _secrets_payload(secrets: SecretStore) -> dict:
    return {
        "encryption_enabled": secrets.enabled,
        "secrets": [await secrets.status(name) for name in MANAGED_SECRETS],
    }


@router.get("/secrets", dependencies=[Depends(require_admin)])
async def list_secrets(secrets: SecretStore = Depends(get_secrets)) -> dict:
    """Status of operator-managed secrets — never the values, only a fingerprint."""
    return await _secrets_payload(secrets)


@router.put("/secrets/{name}", dependencies=[Depends(require_admin)])
async def set_secret(
    name: str,
    body: SecretIn,
    secrets: SecretStore = Depends(get_secrets),
) -> dict:
    """Store/rotate a managed secret. Encrypted at rest; the value is never echoed back."""
    if name not in MANAGED_SECRETS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segredo desconhecido.")
    try:
        await secrets.set_secret(name, body.value)
    except SecretStoreUnavailable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Criptografia de segredos desativada (defina SECRET_ENCRYPTION_KEY).",
        )
    return await _secrets_payload(secrets)


@router.delete("/secrets/{name}", dependencies=[Depends(require_admin)])
async def delete_secret(
    name: str,
    secrets: SecretStore = Depends(get_secrets),
) -> dict:
    if name not in MANAGED_SECRETS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segredo desconhecido.")
    await secrets.delete_secret(name)
    return await _secrets_payload(secrets)


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
