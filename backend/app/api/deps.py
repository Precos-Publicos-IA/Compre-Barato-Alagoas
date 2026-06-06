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


def _client_id(request: Request) -> str:
    # Honour a proxy header (Caddy sets X-Forwarded-For), else peer address.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        ip = fwd.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    return hashlib.sha256((_RATELIMIT_SALT + ip).encode()).hexdigest()[:32]


async def enforce_rate_limit(
    request: Request,
    settings: Settings = Depends(get_settings_dep),
    cache: Cache = Depends(get_cache),
) -> None:
    if settings.daily_search_limit <= 0:
        return
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    key = f"ratelimit:{today}:{_client_id(request)}"
    count = await cache.incr_with_ttl(key, ttl=24 * 60 * 60)
    if count > settings.daily_search_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite diário de buscas atingido. Tente novamente amanhã.",
        )
