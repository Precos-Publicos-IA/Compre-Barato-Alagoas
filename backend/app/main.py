"""FastAPI application entrypoint.

Wires the pluggable clients (SEFAZ, LLM) and the cache into ``app.state`` at startup so
they're shared across requests, and exposes the public API. Everything degrades
gracefully: no token -> mock SEFAZ, no key -> mock LLM, no Redis -> in-memory cache,
no Sentry DSN -> Sentry disabled.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .cache import Cache
from .config import get_settings
from .services.llm.factory import build_llm_client
from .services.sefaz.factory import build_sefaz_client


def _init_sentry(settings) -> None:
    if not settings.sentry_dsn:
        return
    try:  # pragma: no cover - optional dependency
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment)
    except Exception:
        logging.getLogger(__name__).exception("Sentry init failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    _init_sentry(settings)

    app.state.settings = settings
    app.state.cache = Cache(settings.redis_url, settings.cache_ttl_seconds)
    app.state.sefaz = build_sefaz_client(settings)
    app.state.llm = build_llm_client(settings)
    try:
        yield
    finally:
        await app.state.cache.aclose()
        await app.state.sefaz.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Secure intermediary over SEFAZ-AL public NFC-e price data.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from .api.routes import health, search, suggestions

    app.include_router(health.router)
    app.include_router(search.router)
    app.include_router(suggestions.router)
    return app


app = create_app()
