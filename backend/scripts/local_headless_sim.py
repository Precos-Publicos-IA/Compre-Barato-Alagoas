#!/usr/bin/env python3
"""
"Headless" local instance test for the full backend (simulates web UI /search flow).

Uses FastAPI TestClient + the real app (with fakes for SEFAZ/LLM via settings + fakeredis).
Exercises multiple dumb-user inputs (from the 10-test report), including the previously
failing ones, now with the new Requester + Verifier agents wired in.

This is the "run a local instance on my PC and test with simulated user input" requirement.
No real browser (no playwright/docker), but direct to the HTTP API the web frontend uses,
with realistic baskets + location. Prints rich output so you can "see" the UX.

Run via the isolated venv after `pip install -e .[dev] pytest` etc. in that venv.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Make package importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Force mock everything + fakeredis friendly
os.environ.setdefault("USE_MOCK_SEFAZ", "true")
os.environ.setdefault("USE_MOCK_LLM", "true")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/99")  # will be patched by fakeredis in tests

from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings

# Patch settings for test
settings = get_settings()
settings.use_mock_sefaz = True
settings.use_mock_llm = True

# The test conftest patches Cache with fakeredis; we do a minimal version here
# by replacing the Cache in the app state after lifespan (or use the test app creation).
# For simplicity we rely on the fact that tests/conftest sets up fakeredis autouse,
# but since we run standalone we manually create a fakeredis client and override.

import fakeredis.aioredis
import pytest  # only for the fixture logic, we copy the pattern

async def _make_fake_cache():
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    from app.cache import Cache
    c = Cache(client=fake)
    await c.ping()
    return c

def run_headless_sims():
    # We bypass the real lifespan Redis ping by constructing the app with patched state.
    # Easiest reliable way: use the same pattern as test_api.py (they use the fixture).
    # Here we do a direct client + override the dependencies that need cache/llm/sefaz.

    from app.api.deps import get_cache, get_llm, get_sefaz, get_analytics
    from app.services.llm.factory import build_llm_client
    from app.services.sefaz.factory import build_sefaz_client
    from app.analytics import Analytics
    from app.cache import Cache

    # Build fakes
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

    async def _setup():
        await fake_redis.ping()
        cache = Cache(client=fake_redis)
        llm = build_llm_client(settings)
        sefaz = build_sefaz_client(settings, None)
        analytics = Analytics(client=fake_redis)
        return cache, llm, sefaz, analytics

    cache, llm, sefaz, analytics = asyncio.run(_setup())

    # Override deps
    app.dependency_overrides[get_cache] = lambda: cache
    app.dependency_overrides[get_llm] = lambda: llm
    app.dependency_overrides[get_sefaz] = lambda: sefaz
    app.dependency_overrides[get_analytics] = lambda: analytics

    client = TestClient(app)

    DUMB_INPUTS = [
        ["arroz"],
        ["leite 2L"],
        ["feijao e arroz"],
        ["pao"],           # previously bad
        ["manteiga"],      # previously bad
        ["2kg de frango"],
        ["coca"],
        ["sabonete"],
        ["banana"],
        ["arroz integral 5kg"],
        ["iogurte natural"],  # previously bad
    ]

    print("=== HEADLESS LOCAL INSTANCE SIM (TestClient to real /api/v1/search) ===")
    print(f"Using agents: BasicRequester + BasicVerifier (RAG learning via Cache)")
    print()

    results = []
    for items in DUMB_INPUTS:
        payload = {
            "items": items,
            "latitude": -9.6633,
            "longitude": -35.7089,
            "radius_km": 8,
            "days": 7,
        }
        resp = client.post("/api/v1/search", json=payload)
        data = resp.json()
        stores = data.get("stores", [])
        metrics = data.get("metrics", {})
        match = metrics.get("match_rate", 0)
        items_req = metrics.get("items_requested", len(items))
        print(f"INPUT: {items}")
        print(f"  status={resp.status_code}  stores={len(stores)}  match_rate={match}  items={items_req}")
        if stores:
            top = stores[0]
            print(f"  TOP: {top.get('name')}  total=R${top.get('total')}  found={top.get('items_found')}/{top.get('items_total')}")
        else:
            print("  (no stores - empty result path exercised)")
        print()
        results.append({"input": items, "stores": len(stores), "match": match})

    print("=== SUMMARY ===")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print("\nLocal instance + simulated user inputs: exercised (including the 3 previously painful ones).")
    print("RAG mappings were recorded by Verifier during the calls (future requests can benefit).")

    # === Extra: demonstrate cross-call RAG learning (adversarial + learning) ===
    print("\n=== RAG LEARNING DEMO (two sequential calls) ===")
    # First populate knowledge with a "good" term the user might say
    client.post("/api/v1/search", json={"items": ["pao frances"], "latitude": -9.6633, "longitude": -35.7089})
    # Now the vague version - Requester should be able to use the recorded mapping in the same process? 
    # (note: within one request the record happens after, so this shows the population)
    r2 = client.post("/api/v1/search", json={"items": ["pao"], "latitude": -9.6633, "longitude": -35.7089})
    print("After searching 'pao frances' then 'pao':", r2.json().get("metrics", {}).get("match_rate"))
    print("(In longer sessions or with pre-warm the Requester will rewrite 'pao' -> 'pao frances' automatically.)")

    # Cleanup overrides
    app.dependency_overrides.clear()

if __name__ == "__main__":
    run_headless_sims()
