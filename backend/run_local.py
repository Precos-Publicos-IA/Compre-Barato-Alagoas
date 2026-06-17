#!/usr/bin/env python3
"""Run the backend locally with no external dependencies.

Backs the (mandatory) Redis with in-process fakeredis and forces mock SEFAZ + mock
LLM, so the full app — real Cache/analytics/search code paths included — runs with a
single command and nothing to install or start. Handy for headless smoke tests,
Puppeteer/e2e runs and quick manual pokes at the API.

    python run_local.py            # serves http://127.0.0.1:8000

Never use this in production: state is in-memory and lost on exit.
"""

from __future__ import annotations

import os

# Force mock mode + permissive dev settings before any app import reads them.
os.environ.setdefault("USE_MOCK_SEFAZ", "true")
os.environ.setdefault("USE_MOCK_LLM", "true")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("CORS_ORIGINS", "*")
os.environ.setdefault("DAILY_SEARCH_LIMIT", "0")  # no rate limit while testing
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")  # faked below

# --- Patch redis.asyncio BEFORE the app imports Cache, so a single shared
#     fakeredis instance backs every connection (one process = one store). ---
import fakeredis.aioredis as _fr  # noqa: E402
import redis.asyncio as _aioredis  # noqa: E402

_fake = _fr.FakeRedis(decode_responses=True)
_aioredis.from_url = lambda *a, **k: _fake  # type: ignore[assignment]
print("[run_local] redis.asyncio.from_url -> in-memory FakeRedis")

import uvicorn  # noqa: E402

from app.main import app  # noqa: E402

if __name__ == "__main__":
    host = os.environ.get("LOCAL_HOST", "127.0.0.1")
    port = int(os.environ.get("LOCAL_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, log_level="info")
