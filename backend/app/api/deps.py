"""FastAPI dependencies: shared clients and the daily rate limit."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status

from ..analytics import Analytics
from ..cache import Cache
from ..config import Settings, get_settings
from ..services.llm.base import LLMClient
from ..services.secrets import SecretStore
from ..services.sefaz.base import SefazClient


def get_settings_dep() -> Settings:
    return get_settings()


def get_cache(request: Request) -> Cache:
    return request.app.state.cache


def get_analytics(request: Request) -> Analytics:
    return request.app.state.analytics


def get_sefaz(request: Request) -> SefazClient:
    return request.app.state.sefaz


def get_llm(request: Request) -> LLMClient:
    return request.app.state.llm


def get_secrets(request: Request) -> SecretStore:
    return request.app.state.secrets


# Pseudo-anonymous device identity: the client sends a high-entropy opaque token
# (generated once, kept in the device's secure storage) as a bearer credential.
# Treated like a password — never logged.
_DEVICE_TOKEN_HEADER = "x-device-token"
_MIN_TOKEN_LEN = 32
_MAX_TOKEN_LEN = 128


def _valid_token(token: str) -> bool:
    return (
        _MIN_TOKEN_LEN <= len(token) <= _MAX_TOKEN_LEN
        and all(c in "0123456789abcdefABCDEF" for c in token)
    )


def get_device_token(request: Request) -> str | None:
    """Optional device token (e.g. on /search): returns it only if well-formed."""
    token = request.headers.get(_DEVICE_TOKEN_HEADER)
    return token if token and _valid_token(token) else None


def require_device_token(request: Request) -> str:
    """Mandatory device token for the /device endpoints."""
    token = get_device_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identificação do dispositivo ausente ou inválida.",
        )
    return token


# Anonymous usage-measurement id (LGPD: legítimo interesse, opt-out). Sent on every
# search unless the user turns off "Estatísticas anônimas de uso". Deliberately separate
# from the consent device token: it only ever feeds a salted-hash HyperLogLog (aggregate
# unique count), is never linked to lists/identity, and is never logged or stored as-is.
_ANALYTICS_ID_HEADER = "x-analytics-id"


def get_analytics_id(request: Request) -> str | None:
    """Optional anonymous analytics id (same hex shape as the device token)."""
    value = request.headers.get(_ANALYTICS_ID_HEADER)
    return value if value and _valid_token(value) else None


# Salt for the rate-limit client key. The IP is personal data (LGPD), so we never
# store it raw: the key holds only a salted hash. It still uniquely buckets a client
# for the 24h window, but a Redis dump reveals no addresses.
_RATELIMIT_SALT = "compre-barato-alagoas/ratelimit/v1"
_ADMIN_RATELIMIT_SALT = "compre-barato-alagoas/admin-ratelimit/v1"


def _peer_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _client_ip_for_rate_limit(request: Request, settings: Settings) -> str:
    """Resolve client IP for rate limiting without trusting XFF from untrusted peers (#264).

    Only when the direct peer is in ``settings.trusted_proxy_ip_set`` do we honour
    the left-most ``X-Forwarded-For`` hop (edge nginx should set/overwrite this).
    Otherwise we always use the TCP peer — blocking header spoofing on direct access.
    """
    peer = _peer_ip(request)
    trusted = settings.trusted_proxy_ip_set
    if peer in trusted:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            first = fwd.split(",")[0].strip()
            if first:
                return first
        real_ip = (request.headers.get("x-real-ip") or "").strip()
        if real_ip:
            return real_ip
    return peer


def _client_id(request: Request, settings: Settings | None = None) -> str:
    if settings is None:
        settings = get_settings()
    ip = _client_ip_for_rate_limit(request, settings)
    return hashlib.sha256((_RATELIMIT_SALT + ip).encode()).hexdigest()[:32]


async def enforce_rate_limit(
    request: Request,
    settings: Settings = Depends(get_settings_dep),
    cache: Cache = Depends(get_cache),
) -> None:
    if settings.daily_search_limit <= 0:
        return
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    key = f"ratelimit:{today}:{_client_id(request, settings)}"
    count = await cache.incr_with_ttl(key, ttl=24 * 60 * 60)
    if count > settings.daily_search_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite diário de buscas atingido. Tente novamente amanhã.",
        )


async def enforce_admin_rate_limit(
    request: Request,
    settings: Settings = Depends(get_settings_dep),
    cache: Cache = Depends(get_cache),
) -> None:
    """Throttle authenticated admin traffic per token+IP hour (#266).

    Runs only after ``require_admin`` succeeds (router dependency order). Does not
    replace failed-auth lockout (#163); only limits successful sessions/polling.
    """
    if settings.admin_hourly_request_limit <= 0:
        return
    auth = request.headers.get("authorization", "")
    presented = ""
    if auth.lower().startswith("bearer "):
        presented = auth[7:].strip()
    else:
        presented = request.headers.get("x-admin-token", "")
    token_fp = hashlib.sha256(
        (_ADMIN_RATELIMIT_SALT + (presented or "none")).encode()
    ).hexdigest()[:16]
    ip = _client_ip_for_rate_limit(request, settings)
    ip_fp = hashlib.sha256((_ADMIN_RATELIMIT_SALT + ip).encode()).hexdigest()[:16]
    hour = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    key = f"adminratelimit:{hour}:{token_fp}:{ip_fp}"
    count = await cache.incr_with_ttl(key, ttl=60 * 60)
    if count > settings.admin_hourly_request_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite horário do painel admin atingido. Aguarde e tente novamente.",
        )
