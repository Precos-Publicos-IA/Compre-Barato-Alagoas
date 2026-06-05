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
