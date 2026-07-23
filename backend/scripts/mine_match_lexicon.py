#!/usr/bin/env python3
"""Mine product heads + synonym *candidates* from training/outcome data (Phase 5).

Writes a **versioned** lexicon JSON under ``backend/data/matching/`` (or ``--out``).

Safety (non-negotiable):
- Emits ``synonym_candidates`` only — never auto-merges into production
  ``_SYN_GROUPS`` / ``promoted_synonym_groups``.
- Drops any pair that fails ``heads_compatible`` (queijo↔pao etc.).
- Does not learn from fetch_failed / empty_no_data rows.

Schema (documented; 5-S1):
  schema_version, version, generated_at, source, heads[],
  synonym_candidates[], brand_skip_hints[], promoted_synonym_groups[] (always []),
  meta{}

Usage (from repo root):
  PYTHONPATH=backend python3 backend/scripts/mine_match_lexicon.py
  PYTHONPATH=backend python3 backend/scripts/mine_match_lexicon.py \\
    --input backend/tests/fixtures/match_lexicon_mine_sample.jsonl \\
    --out /tmp/heads_lexicon.dry.json --dry-run

  # Full 10k:
  PYTHONPATH=backend python3 backend/scripts/mine_match_lexicon.py \\
    --input backend/data/training-datasets/alagoas_search_10k.jsonl \\
    --out backend/data/matching/heads_lexicon.v1.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.rag.intent import (  # noqa: E402
    expand_synonyms,
    extract_intent,
    heads_compatible,
    token_list,
    token_matches,
    _is_head_candidate,
    _content_tokens_ordered,
)

DEFAULT_INPUT = BACKEND / "data/training-datasets/alagoas_search_10k.jsonl"
DEFAULT_FIXTURE = BACKEND / "tests/fixtures/match_lexicon_mine_sample.jsonl"
DEFAULT_OUT = BACKEND / "data/matching/heads_lexicon.v1.json"
SCHEMA_VERSION = 1
LEXICON_VERSION = "v1"


# ---------------------------------------------------------------------------
# Pure filters (unit-tested)
# ---------------------------------------------------------------------------


def synonym_pair_safe(a: str, b: str) -> bool:
    """Stricter than bare heads_compatible for *candidate emission*.

    Requires heads_compatible **and** one of:
    - shared expand_synonyms group / hypernym
    - simple plural (s / es)
    - token_matches with lengths close (avoids maca⊂macarrao false friends)

    Never allows queijo↔pao (fails heads_compatible).
    """
    a = (a or "").strip().lower()
    b = (b or "").strip().lower()
    if not a or not b or a == b:
        return False
    if not heads_compatible(a, b):
        return False
    ea = expand_synonyms({a})
    eb = expand_synonyms({b})
    if ea & eb:
        return True
    if a == b + "s" or b == a + "s" or a == b + "es" or b == a + "es":
        return True
    # Close stems only (drop long-prefix false friends)
    if abs(len(a) - len(b)) <= 2 and token_matches(a, b):
        return True
    return False


def filter_synonym_pairs(
    pairs: Iterable[tuple[str, str] | dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep only pairs that pass synonym_pair_safe; drop cross-head poison.

    Accepts (a, b) tuples or dicts with keys a/b or head_a/head_b.
    Never emits queijo↔pao style incompatibles (5-S3).
    """
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for p in pairs:
        if isinstance(p, dict):
            a = (p.get("a") or p.get("head_a") or "").strip().lower()
            b = (p.get("b") or p.get("head_b") or "").strip().lower()
            extra = {
                k: v
                for k, v in p.items()
                if k not in ("a", "b", "head_a", "head_b", "heads_compatible")
            }
        else:
            a, b = p[0], p[1]
            a = (a or "").strip().lower()
            b = (b or "").strip().lower()
            extra = {}
        if not synonym_pair_safe(a, b):
            continue
        key = tuple(sorted((a, b)))
        if key in seen:
            for prev in out:
                if tuple(sorted((prev["a"], prev["b"]))) == key:
                    if "co_success" in extra:
                        prev["co_success"] = int(prev.get("co_success") or 0) + int(
                            extra.get("co_success") or 0
                        )
                    break
            continue
        seen.add(key)
        row = {"a": key[0], "b": key[1], "heads_compatible": True}
        row.update(extra)
        row["heads_compatible"] = True
        out.append(row)
    return out


def is_usable_match_row(
    *,
    stores_found: int | None,
    items_fetch_failed: bool | int | None,
    description: str | None,
) -> bool:
    """True when the row is on the match track (not fetch/empty)."""
    if items_fetch_failed:
        return False
    if stores_found is not None and int(stores_found) <= 0:
        return False
    if not (description or "").strip():
        return False
    return True


# ---------------------------------------------------------------------------
# Record parsing (10k training + outcome-log-ish)
# ---------------------------------------------------------------------------


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit(f"{path}:{line_no}: invalid JSON: {e}") from e
            if isinstance(obj, dict):
                yield obj


def _queries_from_record(rec: dict[str, Any]) -> list[str]:
    out: list[str] = []
    req = rec.get("request") or {}
    items = req.get("items")
    if isinstance(items, list):
        for it in items:
            if isinstance(it, str) and it.strip():
                out.append(it.strip())
            elif isinstance(it, dict):
                q = (it.get("query") or it.get("label") or "").strip()
                if q:
                    out.append(q)
    meta = rec.get("meta") or {}
    bq = (meta.get("base_query") or "").strip()
    if bq and bq not in out:
        out.append(bq)
    # outcome-log style
    for k in ("user_term", "query", "label"):
        v = (rec.get(k) or "").strip() if isinstance(rec.get(k), str) else ""
        if v and v not in out:
            out.append(v)
    return out


def _descriptions_from_record(rec: dict[str, Any]) -> list[str]:
    descs: list[str] = []
    summary = rec.get("summary") or {}
    td = summary.get("top_description")
    if isinstance(td, str) and td.strip():
        descs.append(td.strip())
    # outcome log tops
    for t in rec.get("top_lines") or rec.get("tops") or []:
        if isinstance(t, str) and t.strip():
            descs.append(t.strip())
        elif isinstance(t, dict):
            d = (t.get("description") or t.get("desc") or "").strip()
            if d:
                descs.append(d)
    d0 = (rec.get("top_description") or rec.get("description") or "").strip()
    if d0:
        descs.append(d0)
    # walk stores
    resp = rec.get("response") or {}
    for store in resp.get("stores") or []:
        if not isinstance(store, dict):
            continue
        for it in store.get("items") or []:
            if not isinstance(it, dict):
                continue
            if it.get("found") is False:
                continue
            d = (it.get("description") or "").strip()
            if d:
                descs.append(d)
    # dedupe preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for d in descs:
        if d not in seen:
            seen.add(d)
            uniq.append(d)
    return uniq


def _row_match_meta(rec: dict[str, Any]) -> tuple[int | None, bool]:
    summary = rec.get("summary") or {}
    stores = summary.get("stores_found")
    if stores is None and "stores_found" in rec:
        stores = rec.get("stores_found")
    if stores is None:
        resp = rec.get("response") or {}
        st = resp.get("stores")
        if isinstance(st, list):
            stores = len(st)
    fetch_failed = bool(
        summary.get("items_fetch_failed")
        or rec.get("items_fetch_failed")
        or rec.get("fetch_failed")
    )
    try:
        stores_i = int(stores) if stores is not None else None
    except (TypeError, ValueError):
        stores_i = None
    return stores_i, fetch_failed


# ---------------------------------------------------------------------------
# Mining
# ---------------------------------------------------------------------------


def mine_records(
    records: Iterable[dict[str, Any]],
    *,
    min_head_count: int = 2,
    min_co_success: int = 1,
    max_heads: int = 500,
    max_synonyms: int = 200,
) -> dict[str, Any]:
    """Mine heads + synonym candidates from already-parsed records."""
    query_head_counts: Counter[str] = Counter()
    desc_head_counts: Counter[str] = Counter()
    # first content token in descriptions (for brand-skip mining)
    desc_first_token: Counter[str] = Counter()
    co_success: Counter[tuple[str, str]] = Counter()
    n_records = 0
    n_usable = 0
    n_skipped_fetch = 0
    n_skipped_empty = 0

    for rec in records:
        n_records += 1
        stores_found, fetch_failed = _row_match_meta(rec)
        queries = _queries_from_record(rec)
        descs = _descriptions_from_record(rec)

        if fetch_failed:
            n_skipped_fetch += 1
            # still count query heads for frequency
            for q in queries:
                h = extract_intent(q).head
                if h:
                    query_head_counts[h] += 1
            continue

        primary_desc = descs[0] if descs else None
        if not is_usable_match_row(
            stores_found=stores_found,
            items_fetch_failed=False,
            description=primary_desc,
        ):
            n_skipped_empty += 1
            for q in queries:
                h = extract_intent(q).head
                if h:
                    query_head_counts[h] += 1
            continue

        n_usable += 1
        q_heads: list[str] = []
        for q in queries:
            h = extract_intent(q).head
            if h:
                query_head_counts[h] += 1
                q_heads.append(h)

        for d in descs:
            di = extract_intent(d)
            if di.head:
                desc_head_counts[di.head] += 1
            content = _content_tokens_ordered(token_list(d))
            if content:
                desc_first_token[content[0]] += 1
            # co-success synonym candidates: query head vs desc head
            if not di.head:
                continue
            for qh in q_heads:
                if qh == di.head:
                    continue
                # only count safe pairs (strict filter; re-checked on emit)
                if synonym_pair_safe(qh, di.head):
                    key = tuple(sorted((qh, di.head)))
                    co_success[key] += 1  # type: ignore[index]

    # Build heads list: prefer frequent heads; always keep query heads seen ≥1 time
    # so staples appear even on small CI fixtures (5-S7).
    combined: Counter[str] = Counter()
    combined.update(query_head_counts)
    combined.update(desc_head_counts)
    head_rows: list[dict[str, Any]] = []
    for tok, total in combined.most_common():
        if not _is_head_candidate(tok):
            continue
        as_q = int(query_head_counts.get(tok, 0))
        as_d = int(desc_head_counts.get(tok, 0))
        if total < min_head_count and as_q < 1:
            continue
        head_rows.append(
            {
                "token": tok,
                "count": int(total),
                "as_query": as_q,
                "as_desc": as_d,
            }
        )
        if len(head_rows) >= max_heads:
            break

    # Synonym candidates via filter (hard safety)
    raw_pairs = [
        {"a": a, "b": b, "co_success": int(n)}
        for (a, b), n in co_success.most_common()
        if n >= min_co_success
    ]
    syn_rows = filter_synonym_pairs(raw_pairs)[:max_synonyms]
    # also re-check co_success threshold after merge
    syn_rows = [s for s in syn_rows if int(s.get("co_success") or 0) >= min_co_success][
        :max_synonyms
    ]

    # Brand-skip hints: frequent first desc tokens that are never/rare query heads
    brand_hints: list[dict[str, Any]] = []
    for tok, c in desc_first_token.most_common(100):
        if not _is_head_candidate(tok):
            continue
        if query_head_counts.get(tok, 0) > 0:
            continue
        if c < 3:
            continue
        # likely brand or size-ish product prefix
        brand_hints.append({"token": tok, "as_desc_first": int(c)})
        if len(brand_hints) >= 40:
            break

    return {
        "schema_version": SCHEMA_VERSION,
        "version": LEXICON_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {},
        "heads": head_rows,
        "synonym_candidates": syn_rows,
        "brand_skip_hints": brand_hints,
        # Always empty from miner — promotion is a separate review step (5-S6).
        "promoted_synonym_groups": [],
        "meta": {
            "n_records": n_records,
            "n_usable": n_usable,
            "n_skipped_fetch": n_skipped_fetch,
            "n_skipped_empty": n_skipped_empty,
            "min_head_count": min_head_count,
            "min_co_success": min_co_success,
            "note": (
                "synonym_candidates are NOT production synonyms. "
                "Promote via reviewed promoted_synonym_groups only."
            ),
        },
    }


def mine_paths(
    paths: list[Path],
    **kwargs: Any,
) -> dict[str, Any]:
    def _gen() -> Iterator[dict[str, Any]]:
        for p in paths:
            yield from _iter_jsonl(p)

    artifact = mine_records(_gen(), **kwargs)
    artifact["source"] = {
        "paths": [str(p) for p in paths],
        "kind": "jsonl_training_or_outcomes",
        "n_files": len(paths),
    }
    return artifact


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Mine match heads/synonym candidates (Phase 5)")
    ap.add_argument(
        "--input",
        "-i",
        action="append",
        default=None,
        help="JSONL path (repeatable). Default: 10k if present else CI fixture",
    )
    ap.add_argument(
        "--out",
        "-o",
        type=Path,
        default=None,
        help=f"Output JSON (default: {DEFAULT_OUT})",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Write only if --out set; print summary; prefer fixture when no --input",
    )
    ap.add_argument("--min-head-count", type=int, default=2)
    ap.add_argument("--min-co-success", type=int, default=1)
    ap.add_argument("--max-heads", type=int, default=500)
    ap.add_argument("--max-synonyms", type=int, default=200)
    ap.add_argument(
        "--print-summary",
        action="store_true",
        default=True,
        help="Print head/synonym counts (default on)",
    )
    args = ap.parse_args(argv)

    if args.input:
        paths = [Path(p) for p in args.input]
    elif args.dry_run and DEFAULT_FIXTURE.is_file():
        paths = [DEFAULT_FIXTURE]
    elif DEFAULT_INPUT.is_file():
        paths = [DEFAULT_INPUT]
    elif DEFAULT_FIXTURE.is_file():
        paths = [DEFAULT_FIXTURE]
    else:
        raise SystemExit("no input JSONL found")

    for p in paths:
        if not p.is_file():
            raise SystemExit(f"input not found: {p}")

    # Dry-run defaults to looser thresholds for tiny fixtures
    min_head = args.min_head_count
    if args.dry_run and min_head > 1 and all(
        p.name.endswith("sample.jsonl") or "fixture" in str(p) for p in paths
    ):
        min_head = 1

    artifact = mine_paths(
        paths,
        min_head_count=min_head,
        min_co_success=args.min_co_success,
        max_heads=args.max_heads,
        max_synonyms=args.max_synonyms,
    )

    out_path = args.out
    if out_path is None and not args.dry_run:
        out_path = DEFAULT_OUT

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {out_path}")

    heads = artifact.get("heads") or []
    syns = artifact.get("synonym_candidates") or []
    meta = artifact.get("meta") or {}
    tokens = [h.get("token") for h in heads if isinstance(h, dict)]
    print(
        json.dumps(
            {
                "version": artifact.get("version"),
                "generated_at": artifact.get("generated_at"),
                "n_heads": len(heads),
                "n_synonym_candidates": len(syns),
                "n_records": meta.get("n_records"),
                "n_usable": meta.get("n_usable"),
                "sample_heads": tokens[:20],
                "dry_run": bool(args.dry_run),
                "out": str(out_path) if out_path else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
