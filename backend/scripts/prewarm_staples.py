#!/usr/bin/env python3
"""Prewarm Redis with staple RAG mappings + optional SEFAZ/web term cache.

Run against a live local/prod stack so the first user search for common items
is fast and already relevance-shaped.

  REDIS_URL=redis://127.0.0.1:6379/0 python scripts/prewarm_staples.py
  # also hit the API (optional):
  API_BASE=http://127.0.0.1:8000 python scripts/prewarm_staples.py --fetch
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.cache import Cache

# (user term, effective search term, weight)
STAPLES = [
    ("arroz", "arroz tipo 1", 30),
    ("arroz", "arroz branco", 20),
    ("leite", "leite uht", 30),
    ("leite", "leite integral", 15),
    ("feijao", "feijao carioca", 25),
    ("feijão", "feijao carioca", 25),
    ("pao", "pao frances", 20),
    ("pão", "pao frances", 20),
    ("acucar", "acucar cristal", 12),
    ("açúcar", "acucar cristal", 12),
    ("oleo", "oleo de soja", 12),
    ("óleo", "oleo de soja", 12),
    ("cafe", "cafe torrado", 12),
    ("café", "cafe torrado", 12),
    ("macarrao", "macarrao espaguete", 10),
    ("macarrão", "macarrao espaguete", 10),
    ("ovos", "ovos", 10),
    ("ovo", "ovos", 10),
    ("manteiga", "manteiga", 8),
    ("sabao", "sabao em po", 8),
    ("sabão", "sabao em po", 8),
]


async def main(fetch: bool) -> None:
    url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
    cache = Cache(redis_url=url)
    await cache.ping()
    for user, effective, w in STAPLES:
        await cache.record_successful_mapping(user, effective, w)
        print(f"RAG {user!r} -> {effective!r} (w={w})")
    print(f"Prewarmed {len(STAPLES)} RAG mappings on {url}")

    if fetch:
        import httpx

        base = os.environ.get("API_BASE", "http://127.0.0.1:8000").rstrip("/")
        items = ["leite", "arroz", "feijao", "pao", "acucar", "oleo"]
        async with httpx.AsyncClient(timeout=180.0) as client:
            # Warm in pairs to limit fan-out
            for i in range(0, len(items), 2):
                batch = items[i : i + 2]
                print(f"Fetching {batch}…")
                r = await client.post(
                    f"{base}/api/v1/search",
                    json={
                        "items": batch,
                        "latitude": -9.6633,
                        "longitude": -35.7089,
                        "radius_km": 8,
                        "days": 7,
                    },
                )
                print(f"  status={r.status_code} body_len={len(r.content)}")
        print("API term cache warm done.")

    await cache.aclose()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--fetch",
        action="store_true",
        help="Also call the local/prod search API to fill SEFAZ/web response cache",
    )
    args = ap.parse_args()
    asyncio.run(main(args.fetch))
