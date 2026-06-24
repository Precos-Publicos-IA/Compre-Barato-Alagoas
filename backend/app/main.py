"""FastAPI application entrypoint.

Wires the pluggable clients (SEFAZ, LLM) and the cache into ``app.state`` at startup so
they're shared across requests, and exposes the public API. Externals degrade
gracefully: no token -> mock SEFAZ, no key -> mock LLM, no Sentry DSN -> disabled.
Redis is the one hard dependency: startup fails fast if it's unreachable.
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .analytics import Analytics
from .cache import Cache
from .config import get_settings
from .services.llm.factory import build_llm_client
from .services.secrets import SecretStore
from .services.sefaz.factory import build_sefaz_client


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a short request id (propagated from ``X-Request-ID`` or generated) to
    every request/response. Lets us correlate a user-facing error reference with the
    server logs without pulling in a heavy tracing stack."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["x-request-id"] = rid
        return response


# Header/body fragments we never want in Sentry (LGPD / credential hygiene — #267).
_SENTRY_SCRUB_KEYS = frozenset(
    {
        "authorization",
        "x-admin-token",
        "x-device-token",
        "x-analytics-id",
        "cookie",
        "set-cookie",
        "admin_token",
        "sefaz_app_token",
        "anthropic_api_key",
        "secret_encryption_key",
        "password",
        "token",
    }
)


def _sentry_scrub_event(event: dict, _hint: dict) -> dict | None:
    """Drop obvious secrets and truncate long request bodies before send."""
    try:
        req = event.get("request") or {}
        headers = req.get("headers")
        if isinstance(headers, dict):
            for k in list(headers.keys()):
                if str(k).lower() in _SENTRY_SCRUB_KEYS:
                    headers[k] = "[Filtered]"
        data = req.get("data")
        if isinstance(data, str) and len(data) > 512:
            req["data"] = data[:512] + "…[truncated]"
        elif isinstance(data, dict):
            for k in list(data.keys()):
                lk = str(k).lower()
                if lk in _SENTRY_SCRUB_KEYS or lk in {"items", "raw_items", "note"}:
                    data[k] = "[Filtered]"
        event["request"] = req
    except Exception:
        pass
    return event


def _init_sentry(settings) -> None:
    if not settings.sentry_dsn:
        return
    try:  # pragma: no cover - optional dependency
        import sentry_sdk

        init_kwargs: dict = {
            "dsn": settings.sentry_dsn,
            "environment": settings.environment,
            "send_default_pii": False,
            "traces_sample_rate": max(
                0.0, min(1.0, float(settings.sentry_traces_sample_rate or 0.0))
            ),
            "before_send": _sentry_scrub_event,
        }
        release = (settings.git_sha or "").strip()
        if release:
            init_kwargs["release"] = release
        sentry_sdk.init(**init_kwargs)
    except Exception:
        logging.getLogger(__name__).exception("Sentry init failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
        # So cross-origin clients (admin SPA, local dev) can read the request id
        # for support/correlation; same-origin prod calls are unaffected.
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestIdMiddleware)

    # Tag Sentry scope with request id when SDK is active (best-effort).
    class _SentryRequestIdMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            rid = getattr(request.state, "request_id", None)
            if rid:
                try:  # pragma: no cover
                    import sentry_sdk

                    sentry_sdk.set_tag("request_id", rid)
                except Exception:
                    pass
            return await call_next(request)

    app.add_middleware(_SentryRequestIdMiddleware)

    from .api.routes import admin, device, feedback, health, search, suggestions

    app.include_router(health.router)
    app.include_router(search.router)
    app.include_router(suggestions.router)
    app.include_router(device.router)
    app.include_router(feedback.router)
    app.include_router(admin.router)
    return app


app = create_app()
