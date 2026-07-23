#!/usr/bin/env python3
"""Prewarm Redis with staple RAG mappings + optional SEFAZ/web term cache.

Run against a live local/prod stack so the first user search for common items
is fast and already relevance-shaped.

  REDIS_URL=redis://127.0.0.1:6379/0 python scripts/prewarm_staples.py
  # also hit the API (fills sefaz:search:* for non-empty results):
  API_BASE=http://127.0.0.1:8000 python scripts/prewarm_staples.py --fetch

Post-deploy (VPS host after health check) prefers the shell helper:

  API_BASE=http://127.0.0.1:8000 bash deploy/prewarm-staples.sh

Which only needs curl (no Python/Redis from the host). This script is the
full path (RAG mappings + optional API fetch) for ops with Redis access.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.cache import Cache
from app.services.sefaz.staples import (
    STAPLE_FETCH_TERMS,
    STAPLE_RAG_MAPPINGS,
    unique_fetch_terms,
)

# Back-compat alias for anything that imported STAPLES from this script.
STAPLES = STAPLE_RAG_MAPPINGS

# Maceió default origin — must match config.MACEIO_LAT/LON.
_MACEIO_LAT = -9.6633
_MACEIO_LON = -35.7089


async def prewarm_rag(cache: Cache) -> int:
    for user, effective, w in STAPLE_RAG_MAPPINGS:
        await cache.record_successful_mapping(user, effective, w)
        print(f"RAG {user!r} -> {effective!r} (w={w})")
    return len(STAPLE_RAG_MAPPINGS)


async def prewarm_api_fetch(
    *,
    base: str,
    batch_size: int,
    delay_seconds: float,
    radius_km: int,
    days: int,
    timeout: float,
) -> tuple[int, int]:
    """POST small batches to /api/v1/search. Returns (ok_batches, fail_batches)."""
    import httpx

    items = unique_fetch_terms(STAPLE_FETCH_TERMS)
    batch_size = max(1, batch_size)
    ok = fail = 0
    async with httpx.AsyncClient(timeout=timeout) as client:
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            print(f"Fetching {batch}…")
            try:
                r = await client.post(
                    f"{base}/api/v1/search",
                    json={
                        "items": batch,
                        "latitude": _MACEIO_LAT,
                        "longitude": _MACEIO_LON,
                        "radius_km": radius_km,
                        "days": days,
                    },
                )
                print(f"  status={r.status_code} body_len={len(r.content)}")
                if 200 <= r.status_code < 300:
                    ok += 1
                else:
                    fail += 1
            except Exception as exc:  # noqa: BLE001 — best-effort warm
                fail += 1
                print(f"  ERROR: {exc}")
            if delay_seconds > 0 and i + batch_size < len(items):
                await asyncio.sleep(delay_seconds)
    return ok, fail


async def main(
    fetch: bool,
    *,
    batch_size: int,
    delay_seconds: float,
    skip_rag: bool,
) -> int:
    url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
    exit_code = 0

    if not skip_rag:
        cache = Cache(redis_url=url)
        try:
            await cache.ping()
            n = await prewarm_rag(cache)
            print(f"Prewarmed {n} RAG mappings on {url}")
        finally:
            await cache.aclose()
    else:
        print("Skipping RAG prewarm (--skip-rag)")

    if fetch:
        base = os.environ.get("API_BASE", "http://127.0.0.1:8000").rstrip("/")
        # Default batch=1 avoids multi-item SEFAZ stampede during warm itself.
        ok, fail = await prewarm_api_fetch(
            base=base,
            batch_size=batch_size,
            delay_seconds=delay_seconds,
            radius_km=int(os.environ.get("PREWARM_RADIUS_KM", "8")),
            days=int(os.environ.get("PREWARM_DAYS", "7")),
            timeout=float(os.environ.get("PREWARM_TIMEOUT", "180")),
        )
        print(f"API term cache warm done: ok_batches={ok} fail_batches={fail}")
        if fail and not ok:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--fetch",
        action="store_true",
        help="Also call the search API to fill SEFAZ response cache",
    )
    ap.add_argument(
        "--skip-rag",
        action="store_true",
        help="Only API fetch (no Redis RAG seed) — useful when only API_BASE is reachable",
    )
    ap.add_argument(
        "--batch-size",
        type=int,
        default=int(os.environ.get("PREWARM_BATCH_SIZE", "1")),
        help="Items per /search request (default 1 = safest for SEFAZ)",
    )
    ap.add_argument(
        "--delay",
        type=float,
        default=float(os.environ.get("PREWARM_DELAY", "1.5")),
        help="Seconds between batches (default 1.5)",
    )
    args = ap.parse_args()
    t0 = time.perf_counter()
    code = asyncio.run(
        main(
            args.fetch,
            batch_size=args.batch_size,
            delay_seconds=args.delay,
            skip_rag=args.skip_rag,
        )
    )
    print(f"prewarm_staples finished in {time.perf_counter() - t0:.1f}s exit={code}")
    raise SystemExit(code)
