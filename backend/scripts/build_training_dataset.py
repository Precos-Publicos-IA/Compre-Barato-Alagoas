#!/usr/bin/env python3
"""Build a training dataset of search query → API response pairs across Alagoas.

Generates ~N unique (query, location) samples by calling POST /api/v1/search.
Locations are real Alagoas municipalities with small jitter so nearby origins
differ slightly (ranking/geo diversity) without leaving the state.

Designed for ops / whitelist egress against production. Resume-safe JSONL.

Usage (from repo root):
  python3 backend/scripts/build_training_dataset.py --target 10000

  API_BASE=https://alagoas.precospublicos.ia.br CONCURRENCY=4 \\
    python3 backend/scripts/build_training_dataset.py --target 10000 \\
    --out backend/data/training-datasets/alagoas_search_10k.jsonl

Env:
  API_BASE       default https://alagoas.precospublicos.ia.br
  CONCURRENCY    default 4
  TIMEOUT_S      default 120
  RADIUS_KM      default 8
  DAYS           default 7
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import random
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REPO = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = REPO / "backend/tests/fixtures/shopping_list_100.json"
DEFAULT_OUT = REPO / "backend/data/training-datasets/alagoas_search_10k.jsonl"
DEFAULT_MANIFEST = REPO / "backend/data/training-datasets/alagoas_search_10k.manifest.json"

# Major / mid Alagoas places (lat, lon). Jitter applied per sample keeps points
# inside the state for typical ±0.02° (~2 km) noise.
ALAGOAS_ANCHORS: list[tuple[str, float, float]] = [
    ("Maceió - Pajuçara", -9.6633, -35.7089),
    ("Maceió - Centro", -9.6658, -35.7350),
    ("Maceió - Farol", -9.6405, -35.7012),
    ("Maceió - Jatiúca", -9.6512, -35.6985),
    ("Maceió - Ponta Verde", -9.6668, -35.6975),
    ("Maceió - Benedito Bentes", -9.5480, -35.6380),
    ("Maceió - Tabuleiro", -9.5750, -35.7550),
    ("Maceió - Cruz das Almas", -9.6250, -35.7200),
    ("Rio Largo", -9.4781, -35.8532),
    ("Satuba", -9.5633, -35.8240),
    ("Santa Luzia do Norte", -9.6036, -35.8231),
    ("Coqueiro Seco", -9.6372, -35.7994),
    ("Marechal Deodoro", -9.7103, -35.8950),
    ("Barra de São Miguel", -9.8397, -35.9086),
    ("Arapiraca", -9.7525, -36.6611),
    ("Arapiraca - Centro", -9.7540, -36.6550),
    ("Palmeira dos Índios", -9.4056, -36.6328),
    ("União dos Palmares", -9.1628, -36.0319),
    ("São Miguel dos Campos", -9.7811, -36.0936),
    ("Pilar", -9.5972, -35.9567),
    ("Atalaia", -9.5019, -36.0228),
    ("Murici", -9.3067, -35.9428),
    ("Viçosa", -9.3714, -36.2408),
    ("Penedo", -10.2903, -36.5819),
    ("Coruripe", -10.1256, -36.1756),
    ("São Luís do Quitunde", -9.3181, -35.5608),
    ("Porto Calvo", -9.0450, -35.3986),
    ("Maragogi", -9.0122, -35.2225),
    ("Junqueiro", -9.9250, -36.4750),
    ("Teotônio Vilela", -9.9061, -36.3525),
    ("Girau do Ponciano", -9.8842, -36.8289),
    ("Santana do Ipanema", -9.3678, -37.2453),
    ("Delmiro Gouveia", -9.3856, -37.9989),
    ("Pão de Açúcar", -9.7486, -37.4367),
    ("Olho d'Água das Flores", -9.5361, -37.2942),
    ("Batalha", -9.6778, -37.1247),
    ("Campo Alegre", -9.7819, -36.3508),
    ("Igaci", -9.5369, -36.6336),
    ("Craíbas", -9.6178, -36.7697),
    ("Limoeiro de Anadia", -9.7408, -36.5028),
]


def strip_accents(s: str) -> str:
    nk = unicodedata.normalize("NFD", s)
    return "".join(c for c in nk if unicodedata.category(c) != "Mn")


def load_base_queries(fixture: Path) -> list[dict[str, Any]]:
    data = json.loads(fixture.read_text(encoding="utf-8"))
    items = data.get("items") or []
    out = []
    for it in items:
        q = (it.get("query") or "").strip()
        if q:
            out.append({"query": q, "category": it.get("category") or "unknown", "base_id": it.get("id")})
    if not out:
        raise SystemExit(f"no queries in {fixture}")
    return out


def query_variants(base: str) -> list[str]:
    """Slight natural variations people type (same item intent)."""
    bare = base.strip()
    no_acc = strip_accents(bare)
    variants = [
        bare,
        bare.lower(),
        no_acc.lower(),
        f"2 {bare}",
        f"1kg {bare}",
        f"{bare} 1kg",
        f"5kg {bare}" if " " not in bare else bare,
        f"{bare} barato",
        f"comprar {bare}",
    ]
    # Dedup preserve order
    seen: set[str] = set()
    out: list[str] = []
    for v in variants:
        v = " ".join(v.split())
        key = v.casefold()
        if key and key not in seen:
            seen.add(key)
            out.append(v)
    return out


def sample_id(query: str, lat: float, lon: float, radius_km: int, days: int) -> str:
    raw = f"{query.strip().casefold()}|{lat:.5f}|{lon:.5f}|{radius_km}|{days}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def build_plan(
    bases: list[dict[str, Any]],
    target: int,
    radius_km: int,
    days: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Deterministic plan of unique (query × location) samples."""
    rng = random.Random(seed)
    # Expand queries
    expanded: list[dict[str, Any]] = []
    for b in bases:
        for v in query_variants(b["query"]):
            expanded.append({
                "query": v,
                "base_query": b["query"],
                "category": b["category"],
                "base_id": b["base_id"],
            })

    plan: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    # Round-robin through queries × anchors with jitter until target
    qi = 0
    attempts = 0
    max_attempts = target * 20
    while len(plan) < target and attempts < max_attempts:
        attempts += 1
        eq = expanded[qi % len(expanded)]
        qi += 1
        place, alat, alon = ALAGOAS_ANCHORS[attempts % len(ALAGOAS_ANCHORS)]
        # Jitter ~±1.5 km; keeps Maceió/interior clusters distinct
        jlat = alat + rng.uniform(-0.015, 0.015)
        jlon = alon + rng.uniform(-0.015, 0.015)
        # Clamp loosely to AL-ish box
        jlat = max(-10.55, min(-8.80, jlat))
        jlon = max(-38.25, min(-35.10, jlon))
        sid = sample_id(eq["query"], jlat, jlon, radius_km, days)
        if sid in seen_ids:
            continue
        seen_ids.add(sid)
        plan.append({
            "id": sid,
            "query": eq["query"],
            "base_query": eq["base_query"],
            "category": eq["category"],
            "base_id": eq["base_id"],
            "place_hint": place,
            "latitude": round(jlat, 5),
            "longitude": round(jlon, 5),
            "radius_km": radius_km,
            "days": days,
        })
    if len(plan) < target:
        raise SystemExit(f"could only plan {len(plan)} unique samples (want {target})")
    return plan


def load_done_ids(path: Path) -> set[str]:
    done: set[str] = set()
    if not path.exists():
        return done
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            rid = obj.get("id")
            if rid and obj.get("http_status") == 200 and obj.get("response") is not None:
                done.add(rid)
    return done


async def fetch_one(
    client: httpx.AsyncClient,
    url: str,
    sample: dict[str, Any],
    timeout_s: float,
    sem: asyncio.Semaphore,
) -> dict[str, Any]:
    payload = {
        "items": [sample["query"]],
        "latitude": sample["latitude"],
        "longitude": sample["longitude"],
        "radius_km": sample["radius_km"],
        "days": sample["days"],
    }
    t0 = time.perf_counter()
    status: int | None = None
    body: dict[str, Any] | None = None
    err: str | None = None
    async with sem:
        try:
            r = await client.post(url, json=payload, timeout=timeout_s)
            status = r.status_code
            try:
                body = r.json()
            except Exception:
                err = (r.text or "")[:400]
                body = None
            if status != 200:
                err = err or (r.text or "")[:400]
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
    latency_ms = int((time.perf_counter() - t0) * 1000)

    # Compact training record: request + full API response (or error)
    rec: dict[str, Any] = {
        "id": sample["id"],
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "latency_ms": latency_ms,
        "http_status": status,
        "error": err,
        "request": {
            "items": payload["items"],
            "latitude": payload["latitude"],
            "longitude": payload["longitude"],
            "radius_km": payload["radius_km"],
            "days": payload["days"],
        },
        "meta": {
            "base_query": sample["base_query"],
            "category": sample["category"],
            "base_id": sample["base_id"],
            "place_hint": sample["place_hint"],
        },
        "response": body if status == 200 else None,
    }
    if body and status == 200:
        metrics = body.get("metrics") or {}
        stores = body.get("stores") or []
        rec["summary"] = {
            "data_source": body.get("data_source"),
            "stores_found": len(stores),
            "match_rate": metrics.get("match_rate"),
            "items_fetch_failed": metrics.get("items_fetch_failed"),
            "top_store": (stores[0].get("name") if stores else None),
            "top_description": None,
        }
        for st in stores:
            for it in st.get("items") or []:
                if it.get("found") and it.get("description"):
                    rec["summary"]["top_description"] = it.get("description")
                    break
            if rec["summary"]["top_description"]:
                break
    return rec


async def run(args: argparse.Namespace) -> int:
    bases = load_base_queries(Path(args.fixture))
    plan = build_plan(bases, args.target, args.radius_km, args.days, args.seed)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.manifest) if args.manifest else out_path.with_suffix(".manifest.json")

    done = load_done_ids(out_path)
    todo = [s for s in plan if s["id"] not in done]
    print(
        f"plan={len(plan)} done={len(done)} todo={len(todo)} "
        f"base={args.api_base} concurrency={args.concurrency}",
        flush=True,
    )

    url = f"{args.api_base.rstrip('/')}/api/v1/search"
    sem = asyncio.Semaphore(args.concurrency)
    ok = fail = 0
    t_start = time.perf_counter()

    headers = {
        "User-Agent": "CBA-training-dataset/1.0",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # Append-only writer with simple lock
    write_lock = asyncio.Lock()

    async def write_rec(rec: dict[str, Any]) -> None:
        line = json.dumps(rec, ensure_ascii=False, default=str) + "\n"
        async with write_lock:
            with out_path.open("a", encoding="utf-8") as f:
                f.write(line)

    async with httpx.AsyncClient(headers=headers, http2=False) as client:
        # Optional probe
        if args.probe_first:
            probe = await fetch_one(
                client,
                url,
                {
                    "id": "probe",
                    "query": "arroz",
                    "base_query": "arroz",
                    "category": "staples",
                    "base_id": 0,
                    "place_hint": "Maceió - Pajuçara",
                    "latitude": -9.6633,
                    "longitude": -35.7089,
                    "radius_km": args.radius_km,
                    "days": args.days,
                },
                args.timeout_s,
                sem,
            )
            print(
                f"probe status={probe.get('http_status')} "
                f"err={probe.get('error')!r} summary={probe.get('summary')}",
                flush=True,
            )
            if probe.get("http_status") != 200:
                print("ABORT: probe failed", flush=True)
                return 2

        # Worker pool: write each record as it completes (resume-safe, live progress).
        q: asyncio.Queue = asyncio.Queue()
        for s in todo:
            q.put_nowait(s)

        async def worker(wid: int) -> None:
            nonlocal ok, fail
            while True:
                try:
                    sample = q.get_nowait()
                except asyncio.QueueEmpty:
                    return
                rec = await fetch_one(client, url, sample, args.timeout_s, sem)
                await write_rec(rec)
                if rec.get("http_status") == 200 and rec.get("response") is not None:
                    ok += 1
                else:
                    fail += 1
                finished = ok + fail
                if finished % 10 == 0 or finished <= 5 or finished == len(todo):
                    elapsed = time.perf_counter() - t_start
                    rate = finished / elapsed if elapsed > 0 else 0
                    print(
                        f"progress ok={ok} fail={fail} total={finished}/{len(todo)} "
                        f"disk_target≈{len(done)+ok}/{args.target} "
                        f"rate={rate:.2f}/s elapsed={elapsed:.0f}s w={wid}",
                        flush=True,
                    )
                if args.sleep_between_batches > 0:
                    await asyncio.sleep(args.sleep_between_batches)

        n_workers = max(1, args.concurrency)
        await asyncio.gather(*[worker(i) for i in range(n_workers)])

    # Recount successes on disk
    final_done = load_done_ids(out_path)
    # Retry failures once if under target
    if len(final_done) < args.target and not args.no_retry:
        remaining = [s for s in plan if s["id"] not in final_done]
        print(f"retry pass: {len(remaining)} remaining", flush=True)
        async with httpx.AsyncClient(headers=headers, http2=False) as client:
            q: asyncio.Queue = asyncio.Queue()
            for s in remaining:
                q.put_nowait(s)

            async def retry_worker(wid: int) -> None:
                nonlocal ok, fail
                while True:
                    try:
                        sample = q.get_nowait()
                    except asyncio.QueueEmpty:
                        return
                    rec = await fetch_one(client, url, sample, args.timeout_s, sem)
                    await write_rec(rec)
                    if rec.get("http_status") == 200 and rec.get("response") is not None:
                        ok += 1
                    else:
                        fail += 1
                    if (ok + fail) % 10 == 0:
                        print(
                            f"retry progress disk_ok={len(load_done_ids(out_path))}/{args.target} w={wid}",
                            flush=True,
                        )

            await asyncio.gather(*[retry_worker(i) for i in range(max(1, args.concurrency))])

    final_done = load_done_ids(out_path)
    # Build compact index stats by streaming file
    n_lines = 0
    n_200 = 0
    sources: dict[str, int] = {}
    places: dict[str, int] = {}
    with out_path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            n_lines += 1
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("http_status") == 200 and obj.get("response") is not None:
                n_200 += 1
                ds = (obj.get("summary") or {}).get("data_source") or "unknown"
                sources[ds] = sources.get(ds, 0) + 1
                ph = (obj.get("meta") or {}).get("place_hint") or "?"
                places[ph] = places.get(ph, 0) + 1

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "api_base": args.api_base,
        "target": args.target,
        "unique_success_ids": len(final_done),
        "jsonl_lines": n_lines,
        "http_200_with_response": n_200,
        "out": str(out_path),
        "fixture": str(args.fixture),
        "radius_km": args.radius_km,
        "days": args.days,
        "seed": args.seed,
        "concurrency": args.concurrency,
        "anchors": len(ALAGOAS_ANCHORS),
        "data_sources": sources,
        "top_places": dict(sorted(places.items(), key=lambda kv: -kv[1])[:15]),
        "reached_target": len(final_done) >= args.target,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)
    return 0 if len(final_done) >= args.target else 1


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", type=int, default=10000)
    p.add_argument("--out", default=str(DEFAULT_OUT))
    p.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    p.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    p.add_argument("--api-base", default=os.environ.get("API_BASE", "https://alagoas.precospublicos.ia.br"))
    p.add_argument("--concurrency", type=int, default=int(os.environ.get("CONCURRENCY", "32")))
    p.add_argument("--timeout-s", type=float, default=float(os.environ.get("TIMEOUT_S", "120")))
    p.add_argument("--radius-km", type=int, default=int(os.environ.get("RADIUS_KM", "8")))
    p.add_argument("--days", type=int, default=int(os.environ.get("DAYS", "7")))
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--probe-first", action="store_true", default=True)
    p.add_argument("--no-probe", action="store_true")
    p.add_argument("--no-retry", action="store_true")
    p.add_argument("--sleep-between-batches", type=float, default=0.0)
    p.add_argument("--plan-only", action="store_true", help="Write plan JSON and exit")
    args = p.parse_args()
    if args.no_probe:
        args.probe_first = False
    if args.plan_only:
        bases = load_base_queries(Path(args.fixture))
        plan = build_plan(bases, args.target, args.radius_km, args.days, args.seed)
        plan_path = Path(args.out).with_suffix(".plan.json")
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps({"count": len(plan), "samples": plan}, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {plan_path} count={len(plan)}")
        return
    # Cap concurrency hard so we don't stampede SEFAZ web
    args.concurrency = max(1, min(args.concurrency, 64))
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
