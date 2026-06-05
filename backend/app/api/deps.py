"""FastAPI dependencies: shared clients and the daily rate limit."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status

from ..cache import Cache
from ..config import Settings, get_settings
from ..services.llm.base import LLMClient
from ..services.sefaz.base import SefazClient


def get_settings_dep() -> Settings:
    return get_settings()


def get_cache(request: Request) -> Cache:
    return request.app.state.cache


def get_sefaz(request: Request) -> SefazClient:
    return request.app.state.sefaz


def get_llm(request: Request) -> LLMClient:
    return request.app.state.llm


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


def _client_id(request: Request) -> str:
    # Honour a proxy header (Caddy sets X-Forwarded-For), else peer address.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


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
