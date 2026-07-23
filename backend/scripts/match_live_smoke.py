#!/usr/bin/env python3
"""Serial post-deploy match smoke (Phase 4) — NOT for default unit CI.

Forces CONCURRENCY=1. Hits live (or local) search API with a fixed staple +
head-incident query list (≥12). Reports **separately**:

  fetch_fail_rate   items_fetch_failed / n
  found_rate        stores>0 with a usable top / n
  good_top_rate     auto_label==good among found
  weak_top_rate     auto_label==weak among found
  bad_top_rate      auto_label==bad among found

Runbook (post-deploy only):
  API_BASE=https://alagoas.precospublicos.ia.br \\
    PYTHONPATH=backend python3 backend/scripts/match_live_smoke.py \\
    --out .grok/status/match_live_smoke_$(date -u +%Y%m%d).json

  # Local mock SEFAZ (dev):
  USE_MOCK_SEFAZ=1 uvicorn ... &
  PYTHONPATH=backend python3 backend/scripts/match_live_smoke.py --api http://127.0.0.1:8000

Do **not** wire this into pytest or every-push CI — SEFAZ rate limits make it flake.
Use offline_rescore_match.py for CI/offline gates.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.rag.labeler import auto_label  # noqa: E402

DEFAULT_API = os.environ.get("API_BASE", "https://alagoas.precospublicos.ia.br")
DEFAULT_OUT = REPO / ".grok/status/match_live_smoke.json"
MACEIO = dict(latitude=-9.6658, longitude=-35.735, radius_km=8, days=7)

# Plan §4.2 default list (15 ≥ 12)
DEFAULT_QUERIES: list[str] = [
    "arroz",
    "feijão",
    "leite",
    "óleo",
    "ovo",
    "banana",
    "peito de frango",
    "queijo",
    "papel higiênico",
    "sabão em pó",
    "farinha de trigo",
    "salsicha",
    "alho",
    "café",
    "açúcar",
]

# Hard-forced serial — never parallel (SEFAZ web path).
CONCURRENCY = 1


def _extract_top_desc(body: dict[str, Any]) -> str | None:
    for store in body.get("stores") or []:
        for item in store.get("items") or []:
            if item.get("found"):
                d = (item.get("description") or "").strip()
                if d:
                    return d
    return None


def _extract_tops(body: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    seen: set[str] = set()
    for store in body.get("stores") or []:
        for item in store.get("items") or []:
            if not item.get("found"):
                continue
            d = (item.get("description") or "").strip()
            if not d or d.lower() in seen:
                continue
            seen.add(d.lower())
            lines.append(
                {
                    "store": store.get("name"),
                    "description": d,
                    "price": item.get("price"),
                }
            )
            if len(lines) >= limit:
                return lines
    return lines


def _fetch_failed_from_body(body: dict[str, Any]) -> bool:
    metrics = body.get("metrics") or {}
    # Prefer explicit count / flags
    iff = metrics.get("items_fetch_failed")
    if iff is not None:
        try:
            if int(iff) > 0:
                return True
        except (TypeError, ValueError):
            pass
    # Per-item status
    for store in body.get("stores") or []:
        for item in store.get("items") or []:
            if item.get("items_fetch_failed") or item.get("fetch_failed"):
                return True
            st = (item.get("status") or item.get("error") or "").lower()
            if "fetch_fail" in st or "timeout" in st:
                return True
    status_msg = (body.get("status_message") or metrics.get("status_message") or "").lower()
    if "fetch" in status_msg and "fail" in status_msg:
        return True
    labels = metrics.get("fetch_failed_labels") or body.get("fetch_failed_labels") or []
    if labels:
        return True
    return False


def _stores_found(body: dict[str, Any]) -> int:
    metrics = body.get("metrics") or {}
    if metrics.get("stores_found") is not None:
        try:
            return int(metrics["stores_found"])
        except (TypeError, ValueError):
            pass
    return len(body.get("stores") or [])


def classify_row(
    query: str,
    *,
    http_status: int | None,
    body: dict[str, Any] | None,
    error: str | None,
) -> dict[str, Any]:
    if error or http_status is None or http_status != 200 or body is None:
        return {
            "query": query,
            "http_status": http_status,
            "error": error,
            "fetch_failed": http_status == 429 or (error or "").startswith("timeout"),
            "found": False,
            "stores_found": 0,
            "top_description": None,
            "top_label": "empty_fetch" if (http_status == 429) else "unknown",
            "row_class": "upstream_error" if http_status and http_status != 200 else "error",
            "top_lines": [],
            "match_rate": None,
            "match_rules_version": None,
        }

    fetch_failed = _fetch_failed_from_body(body)
    stores = _stores_found(body)
    metrics = body.get("metrics") or {}
    match_rate = metrics.get("match_rate")
    tops = _extract_tops(body)
    top_desc = tops[0]["description"] if tops else _extract_top_desc(body)
    found = bool(top_desc) and stores > 0 and not fetch_failed
    if match_rate is not None:
        try:
            if float(match_rate) > 0 and top_desc:
                found = True and not fetch_failed
        except (TypeError, ValueError):
            pass

    if fetch_failed and not top_desc:
        label: str = "empty_fetch"
        row_class = "empty_fetch"
    elif not top_desc or stores <= 0:
        label = "empty_no_data"
        row_class = "empty_no_data"
    else:
        label = auto_label(
            query,
            top_desc,
            fetch_failed=False,
            stores_found=stores,
        )
        if label == "good":
            row_class = "good"
        elif label == "weak":
            row_class = "weak"
        elif label == "bad":
            row_class = "bad"
        else:
            row_class = label

    return {
        "query": query,
        "http_status": http_status,
        "error": None,
        "fetch_failed": fetch_failed,
        "found": found,
        "stores_found": stores,
        "top_description": top_desc,
        "top_label": label,
        "row_class": row_class,
        "top_lines": tops,
        "match_rate": match_rate,
        "match_rules_version": metrics.get("match_rules_version"),
        "latency_hint_ms": None,
    }


def post_search(
    client: httpx.Client,
    api: str,
    query: str,
    timeout_s: float,
) -> tuple[int | None, dict[str, Any] | None, str | None, int]:
    url = f"{api.rstrip('/')}/api/v1/search"
    payload = {"items": [query], **MACEIO}
    t0 = time.perf_counter()
    try:
        r = client.post(url, json=payload, timeout=timeout_s)
        lat = int((time.perf_counter() - t0) * 1000)
        if r.status_code != 200:
            return r.status_code, None, f"HTTP {r.status_code}: {r.text[:240]}", lat
        try:
            return r.status_code, r.json(), None, lat
        except Exception as e:
            return r.status_code, None, f"json_decode: {e}", lat
    except httpx.TimeoutException as e:
        lat = int((time.perf_counter() - t0) * 1000)
        return None, None, f"timeout: {e}", lat
    except Exception as e:
        lat = int((time.perf_counter() - t0) * 1000)
        return None, None, f"{type(e).__name__}: {e}", lat


def run_smoke(
    api: str,
    queries: list[str],
    *,
    timeout_s: float,
    pause_s: float,
) -> dict[str, Any]:
    assert CONCURRENCY == 1, "live smoke must be serial"
    results: list[dict[str, Any]] = []
    with httpx.Client() as client:
        for i, q in enumerate(queries):
            status, body, err, lat = post_search(client, api, q, timeout_s)
            row = classify_row(q, http_status=status, body=body, error=err)
            row["latency_ms"] = lat
            row["index"] = i
            results.append(row)
            print(
                f"[{i+1}/{len(queries)}] {q!r} → {row['row_class']} "
                f"found={row['found']} fetch_failed={row['fetch_failed']} "
                f"{lat}ms top={((row.get('top_description') or '')[:48])!r}"
            )
            if pause_s > 0 and i + 1 < len(queries):
                time.sleep(pause_s)

    n = len(results)
    n_fetch_fail = sum(1 for r in results if r.get("fetch_failed") or r.get("row_class") == "empty_fetch")
    n_found = sum(1 for r in results if r.get("found"))
    found_rows = [r for r in results if r.get("found")]
    n_good = sum(1 for r in found_rows if r.get("top_label") == "good")
    n_weak = sum(1 for r in found_rows if r.get("top_label") == "weak")
    n_bad = sum(1 for r in found_rows if r.get("top_label") == "bad")
    n_empty_no_data = sum(1 for r in results if r.get("row_class") == "empty_no_data")
    n_upstream = sum(1 for r in results if r.get("row_class") in {"upstream_error", "error"})

    def rate(num: int, den: int) -> float:
        return round(num / den, 4) if den else 0.0

    latencies = [r["latency_ms"] for r in results if r.get("latency_ms") is not None]
    latencies_sorted = sorted(latencies)

    def pct(p: float) -> float | None:
        if not latencies_sorted:
            return None
        k = int(round((p / 100.0) * (len(latencies_sorted) - 1)))
        return float(latencies_sorted[k])

    summary = {
        "n": n,
        "concurrency": CONCURRENCY,
        "fetch_fail_count": n_fetch_fail,
        "fetch_fail_rate": rate(n_fetch_fail, n),
        "found_count": n_found,
        "found_rate": rate(n_found, n),
        "empty_no_data_count": n_empty_no_data,
        "upstream_error_count": n_upstream,
        # among found (match track)
        "good_top_count": n_good,
        "weak_top_count": n_weak,
        "bad_top_count": n_bad,
        "good_top_rate": rate(n_good, n_found),
        "weak_top_rate": rate(n_weak, n_found),
        "bad_top_rate": rate(n_bad, n_found),
        "latency_ms": {
            "p50": pct(50),
            "p95": pct(95),
            "min": float(latencies_sorted[0]) if latencies_sorted else None,
            "max": float(latencies_sorted[-1]) if latencies_sorted else None,
            "mean": round(sum(latencies) / len(latencies), 1) if latencies else None,
        },
        "note": (
            "fetch_fail_rate is fetch track; good/weak/bad_top_rate are match track "
            "among found only. Post-deploy only — not unit CI."
        ),
    }

    return {
        "meta": {
            "mode": "match_live_smoke",
            "phase": "4",
            "api": api,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "concurrency": CONCURRENCY,
            "timeout_s": timeout_s,
            "queries_default_n": len(DEFAULT_QUERIES),
            "post_deploy_only": True,
            "not_in_unit_ci": True,
        },
        "summary": summary,
        "queries": queries,
        "results": results,
    }


def write_md(artifact: dict[str, Any], path: Path) -> None:
    s = artifact["summary"]
    lines = [
        "# Match live smoke (post-deploy)",
        "",
        f"- **API:** {artifact['meta'].get('api')}",
        f"- **When:** {artifact['meta'].get('evaluated_at')}",
        f"- **Concurrency:** {artifact['meta'].get('concurrency')} (forced)",
        "",
        "## Rates (fetch vs match split)",
        "",
        f"| metric | value |",
        f"|--------|------:|",
        f"| n | {s['n']} |",
        f"| fetch_fail_rate | {s['fetch_fail_rate']} |",
        f"| found_rate | {s['found_rate']} |",
        f"| good_top_rate (among found) | {s['good_top_rate']} |",
        f"| weak_top_rate (among found) | {s['weak_top_rate']} |",
        f"| bad_top_rate (among found) | {s['bad_top_rate']} |",
        "",
        "## Rows",
        "",
    ]
    for r in artifact["results"]:
        lines.append(
            f"- `{r['query']}` → **{r['row_class']}** "
            f"stores={r.get('stores_found')} top={((r.get('top_description') or '')[:60])!r} "
            f"{r.get('latency_ms')}ms"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Serial (CONCURRENCY=1) post-deploy match smoke. Reports fetch_fail_rate, "
            "found_rate, good_top_rate/weak_top_rate among found. NOT for unit CI."
        ),
        epilog=(
            "Runbook (post-deploy):\n"
            "  API_BASE=https://alagoas.precospublicos.ia.br \\\n"
            "    PYTHONPATH=backend python3 backend/scripts/match_live_smoke.py \\\n"
            "    --out .grok/status/match_live_smoke_YYYYMMDD.json --write-md\n"
            "\n"
            "Offline CI gate: use offline_rescore_match.py instead."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--api", default=DEFAULT_API, help=f"API base (default {DEFAULT_API})")
    p.add_argument(
        "--out",
        "-o",
        type=Path,
        default=DEFAULT_OUT,
        help="JSON output path",
    )
    p.add_argument(
        "--queries",
        type=str,
        default=None,
        help="comma-separated query override (default: 15 staples/incidents)",
    )
    p.add_argument("--timeout", type=float, default=float(os.environ.get("TIMEOUT_S", "120")))
    p.add_argument(
        "--pause",
        type=float,
        default=float(os.environ.get("SMOKE_PAUSE_S", "0.5")),
        help="pause between serial queries (default 0.5s)",
    )
    p.add_argument("--write-md", action="store_true", help="also write <out>.md summary")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="print query list and exit 0 without HTTP (for CI sanity)",
    )
    args = p.parse_args(argv)

    queries = (
        [q.strip() for q in args.queries.split(",") if q.strip()]
        if args.queries
        else list(DEFAULT_QUERIES)
    )
    if len(queries) < 12 and not args.queries:
        print("ERROR: default list must be ≥12", file=sys.stderr)
        return 2

    if args.dry_run:
        print(json.dumps({"concurrency": CONCURRENCY, "n": len(queries), "queries": queries}, indent=2))
        return 0

    out_path = args.out if args.out.is_absolute() else REPO / args.out
    artifact = run_smoke(args.api, queries, timeout_s=args.timeout, pause_s=args.pause)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write_md:
        write_md(artifact, out_path.with_suffix(".md"))

    s = artifact["summary"]
    print(
        f"match_live_smoke: n={s['n']} fetch_fail_rate={s['fetch_fail_rate']} "
        f"found_rate={s['found_rate']} good_top_rate={s['good_top_rate']} "
        f"weak_top_rate={s['weak_top_rate']} → {out_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
