"""FastAPI application entrypoint.

Wires the pluggable clients (SEFAZ, LLM) and the cache into ``app.state`` at startup so
they're shared across requests, and exposes the public API. Externals degrade
gracefully: no token -> mock SEFAZ, no key -> mock LLM, no Sentry DSN -> disabled.
Redis is the one hard dependency: startup fails fast if it's unreachable.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .analytics import Analytics
from .cache import Cache
from .config import get_settings
from .services.llm.factory import build_llm_client
from .services.secrets import SecretStore
from .services.sefaz.factory import build_sefaz_client

# Propagated into log records so operators can grep one id across workers (#174).
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class _RequestIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get()  # type: ignore[attr-defined]
        return True


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a short request id (propagated from ``X-Request-ID`` or generated) to
    every request/response. Lets us correlate a user-facing error reference with the
    server logs without pulling in a heavy tracing stack."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request.state.request_id = rid
        token = _request_id_ctx.set(rid)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            _request_id_ctx.reset(token)
        response.headers["x-request-id"] = rid
        # Light access line with id + duration (no PII/body) for support correlation.
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logging.getLogger("app.access").info(
            "%s %s -> %s (%sms) request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            rid,
        )
        try:
            import sentry_sdk

            sentry_sdk.set_tag("request_id", rid)
        except Exception:
            pass
        return response


def _init_sentry(settings) -> None:
    if not settings.sentry_dsn:
        return
    try:  # pragma: no cover - optional dependency
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment)
    except Exception:
        logging.getLogger(__name__).exception("Sentry init failed")


def _configure_logging(level: str) -> None:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(levelname)s %(name)s [request_id=%(request_id)s] %(message)s",
        )
    else:
        root.setLevel(level)
    filt = _RequestIdLogFilter()
    for handler in root.handlers:
        handler.addFilter(filt)
        # Ensure format has request_id even if basicConfig ran earlier in tests.
        if handler.formatter is None or "%(request_id)" not in (
            handler.formatter._fmt or ""
        ):
            handler.setFormatter(
                logging.Formatter(
                    "%(levelname)s %(name)s [request_id=%(request_id)s] %(message)s"
                )
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _configure_logging(settings.log_level)
    _init_sentry(settings)

    app.state.settings = settings
    app.state.cache = Cache(settings.redis_url, settings.cache_ttl_seconds)
    await app.state.cache.ping()  # fail fast: Redis is mandatory
    app.state.analytics = Analytics(client=app.state.cache.redis)
    app.state.secrets = SecretStore(
        app.state.cache.redis, settings.secret_encryption_key
    )
    app.state.sefaz = build_sefaz_client(settings, app.state.secrets)
    app.state.llm = build_llm_client(settings)
    try:
        yield
    finally:
        await app.state.cache.aclose()
        await app.state.sefaz.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    # In production we disable Swagger/ReDoc/openapi.json by default. Open source
    # and a public *application* API are intentional; an interactive schema UI in
    # prod is not a security boundary and only helps automated scanners. See
    # docs/seguranca-postura.md. Override with EXPOSE_API_DOCS=true if needed.
    docs_url = "/docs" if settings.api_docs_enabled else None
    redoc_url = "/redoc" if settings.api_docs_enabled else None
    openapi_url = "/openapi.json" if settings.api_docs_enabled else None
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Secure intermediary over SEFAZ-AL public NFC-e price data.",
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )
    # Compress JSON/search payloads for mobile/cellular clients (#173).
    # Added first so it is outermost after Starlette reverses add order… actually
    # last-added runs first on the way in; GZip should wrap the response path.
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
        # So cross-origin clients (admin SPA, local dev) can read the request id
        # for support/correlation; same-origin prod calls are unaffected.
        expose_headers=["X-Request-ID", "Retry-After", "X-RateLimit-Limit",
                        "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    )
    app.add_middleware(RequestIdMiddleware)

    from .api.routes import admin, device, feedback, health, search, suggestions

    app.include_router(health.router)
    app.include_router(search.router)
    app.include_router(suggestions.router)
    app.include_router(device.router)
    app.include_router(feedback.router)
    app.include_router(admin.router)
    return app


app = create_app()
