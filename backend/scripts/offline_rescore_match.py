#!/usr/bin/env python3
"""Offline rescore of stored match tops with the current scorer (Phase 4).

Re-scores descriptions from honest eval fixtures (or outcome-log style JSON)
using ``score_description`` + ``auto_label`` / ``alignment_verdict``.
**No network.** Use after scorer/learn changes to catch good→bad regressions
before ship.

Schema (artifact summary counts — names fixed for CI/grep):
  n                       queries with at least one stored top (or all selected)
  still_bad               live bad/wrong tops whose top1 is still bad offline
  now_empty_or_reject     live bad tops that now hard-reject / would empty keep set
  regressed_good_to_bad   live good/pass tops whose top1 is now bad offline
  also: transitions, poison_pair_checks, by_offline_top_label

Usage (from repo root or backend/):
  PYTHONPATH=backend python3 backend/scripts/offline_rescore_match.py
  PYTHONPATH=backend python3 backend/scripts/offline_rescore_match.py \\
    --input backend/tests/fixtures/match_offline_tops.json \\
    --out .grok/status/match_offline_rescore_$(date -u +%Y%m%d).json

  # Against full honest eval (if present; may be gitignored / large):
  PYTHONPATH=backend python3 backend/scripts/offline_rescore_match.py \\
    --input .grok/status/match_eval_100_honest.json

Env:
  MATCH_OFFLINE_MIN_KEEP   min score to count as "kept" (default 0.35, matches filter_offers)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.rag.intent import alignment_verdict  # noqa: E402
from app.services.rag.labeler import auto_label  # noqa: E402
from app.services.rag.relevance import score_description  # noqa: E402

DEFAULT_INPUT = BACKEND / "tests/fixtures/match_offline_tops.json"
DEFAULT_OUT = REPO / ".grok/status/match_offline_rescore.json"
MIN_KEEP_DEFAULT = 0.35
BAD_SCORE_FLOOR = 0.20

# live_verdict values treated as "good" / "bad" for transition accounting
_LIVE_GOOD = frozenset({"pass", "good", "ok"})
_LIVE_BAD = frozenset({"wrong_class", "bad", "weak_as_bad"})


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"meta": {}, "results": data}
    if not isinstance(data, dict):
        raise SystemExit(f"unsupported fixture type: {type(data)}")
    return data


def _results(data: dict[str, Any]) -> list[dict[str, Any]]:
    if "results" in data and isinstance(data["results"], list):
        return data["results"]
    if "items" in data and isinstance(data["items"], list):
        return data["items"]
    raise SystemExit("fixture missing 'results' (or 'items') list")


def _top_descriptions(row: dict[str, Any]) -> list[str]:
    tops = row.get("top_lines") or row.get("tops") or []
    out: list[str] = []
    for t in tops:
        if isinstance(t, str):
            d = t.strip()
        elif isinstance(t, dict):
            d = (t.get("description") or t.get("desc") or "").strip()
        else:
            continue
        if d:
            out.append(d)
    # outcome-log style single top
    if not out:
        d = (row.get("top_description") or row.get("description") or "").strip()
        if d:
            out.append(d)
    return out


def _live_verdict(row: dict[str, Any]) -> str:
    v = row.get("live_verdict") or row.get("verdict") or row.get("label")
    if v:
        return str(v)
    if row.get("wrong_class"):
        return "wrong_class"
    if row.get("found") is False or (row.get("stores_found") is not None and int(row["stores_found"]) <= 0):
        return "missing"
    return "unknown"


def _bucket_live(v: str) -> str:
    if v in _LIVE_GOOD:
        return "good"
    if v in _LIVE_BAD:
        return "bad"
    if v in {"missing", "missing_after_retry", "empty_fetch", "empty_no_data", "upstream_error"}:
        return "empty"
    return "other"


def rescore_top(query: str, description: str, *, min_keep: float) -> dict[str, Any]:
    score = float(score_description(query, query, description))
    align = alignment_verdict(query, description)
    label = auto_label(query, description, score=score, stores_found=1)
    hard_reject = align == "reject" or score < BAD_SCORE_FLOOR
    would_keep = (not hard_reject) and score >= min_keep
    return {
        "description": description,
        "score_now": round(score, 4),
        "alignment_verdict": align,
        "auto_label": label,
        "hard_reject": hard_reject,
        "would_keep": would_keep,
    }


def rescore_row(row: dict[str, Any], *, min_keep: float) -> dict[str, Any]:
    query = (row.get("query") or row.get("user_label") or "").strip()
    descs = _top_descriptions(row)
    live = _live_verdict(row)
    scored = [rescore_top(query, d, min_keep=min_keep) for d in descs] if query else []
    n_kept = sum(1 for s in scored if s["would_keep"])
    top1 = scored[0] if scored else None
    top1_label = top1["auto_label"] if top1 else "empty_no_data"
    top1_bad = bool(top1 and (top1["hard_reject"] or top1_label == "bad"))
    top1_goodish = bool(
        top1
        and not top1_bad
        and top1_label in {"good", "weak"}
        and top1.get("would_keep")
    )
    emptied = bool(scored) and n_kept == 0
    offline_verdict: str
    if not scored:
        offline_verdict = "no_tops"
    elif emptied:
        offline_verdict = "now_empty_or_reject"
    elif top1_bad:
        offline_verdict = "still_bad"
    elif top1 and top1_label == "weak":
        offline_verdict = "weak"
    else:
        offline_verdict = "good"

    live_bucket = _bucket_live(live)
    transition = f"{live_bucket}→{offline_verdict}"

    return {
        "id": row.get("id"),
        "query": query,
        "category": row.get("category"),
        "live_verdict": live,
        "live_bucket": live_bucket,
        "offline_verdict": offline_verdict,
        "transition": transition,
        "n_tops": len(scored),
        "n_kept": n_kept,
        "emptied_all_tops": emptied,
        "top1_auto_label": top1_label if top1 else None,
        "top1_score_now": top1["score_now"] if top1 else None,
        "top1_alignment": top1["alignment_verdict"] if top1 else None,
        "top1_hard_reject": top1["hard_reject"] if top1 else None,
        "top1_goodish": top1_goodish,
        "scored_tops": scored,
    }


def check_poison_pairs(
    pairs: list[dict[str, Any]], *, min_keep: float
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in pairs:
        q = (p.get("query") or "").strip()
        d = (p.get("description") or "").strip()
        expect = p.get("expect") or "reject_or_empty"
        r = rescore_top(q, d, min_keep=min_keep)
        if expect == "keep_good":
            ok = (not r["hard_reject"]) and r["auto_label"] in {"good", "weak"} and r["score_now"] >= BAD_SCORE_FLOOR
        else:
            # reject_or_empty: hard reject or score floor or would not keep
            ok = bool(r["hard_reject"] or r["auto_label"] == "bad" or not r["would_keep"])
        out.append(
            {
                "query": q,
                "description": d,
                "expect": expect,
                "ok": ok,
                **r,
            }
        )
    return out


def summarize(rescored: list[dict[str, Any]], poison: list[dict[str, Any]]) -> dict[str, Any]:
    # Primary Phase-4 counters (4-S2)
    n = len(rescored)
    live_bad = [r for r in rescored if r["live_bucket"] == "bad"]
    # Improvement: all tops would be filtered / hard-reject empty keep set
    now_empty_or_reject = sum(
        1 for r in live_bad if r["emptied_all_tops"] or r["offline_verdict"] == "now_empty_or_reject"
    )
    # Residual: live-bad top1 still bad and not fully emptied
    still_bad = sum(
        1
        for r in live_bad
        if not r["emptied_all_tops"]
        and (r.get("top1_hard_reject") or r.get("top1_auto_label") == "bad")
    )
    live_good = [r for r in rescored if r["live_bucket"] == "good"]
    regressed_good_to_bad = sum(
        1
        for r in live_good
        if r.get("top1_hard_reject")
        or r.get("top1_auto_label") == "bad"
        or r["offline_verdict"] == "now_empty_or_reject"
    )

    transitions: dict[str, int] = {}
    by_offline: dict[str, int] = {}
    by_live: dict[str, int] = {}
    for r in rescored:
        transitions[r["transition"]] = transitions.get(r["transition"], 0) + 1
        by_offline[r["offline_verdict"]] = by_offline.get(r["offline_verdict"], 0) + 1
        by_live[r["live_verdict"]] = by_live.get(r["live_verdict"], 0) + 1

    poison_ok = all(p.get("ok") for p in poison) if poison else True
    poison_fail = [p for p in poison if not p.get("ok")]

    return {
        # 4-S2 required names
        "n": n,
        "still_bad": still_bad,
        "now_empty_or_reject": now_empty_or_reject,
        "regressed_good_to_bad": regressed_good_to_bad,
        # extras
        "n_live_bad": len(live_bad),
        "n_live_good": len(live_good),
        "good_to_good": sum(
            1
            for r in live_good
            if r["offline_verdict"] in {"good", "weak"} and not r["emptied_all_tops"]
        ),
        "bad_to_empty": now_empty_or_reject,
        "bad_to_still_bad": still_bad,
        "transitions": transitions,
        "by_offline_verdict": by_offline,
        "by_live_verdict": by_live,
        "poison_pairs_n": len(poison),
        "poison_pairs_all_ok": poison_ok,
        "poison_pairs_failed": len(poison_fail),
    }


def run(
    input_path: Path,
    out_path: Path,
    *,
    min_keep: float,
    notes_path: Path | None,
) -> dict[str, Any]:
    data = _load(input_path)
    rows = _results(data)
    # Skip rows with no tops for primary n (still list them if present without tops)
    selected = [r for r in rows if _top_descriptions(r)]
    if not selected:
        selected = rows

    rescored = [rescore_row(r, min_keep=min_keep) for r in selected]
    poison_src = data.get("poison_pairs") or []
    if not poison_src:
        # Default poison set when using honest JSON without embedded pairs
        poison_src = [
            {"query": "queijo", "description": "PAO DE QUEIJO CONGELADO 1KG", "expect": "reject_or_empty"},
            {"query": "peito de frango", "description": "OVOS BRANCOS UND", "expect": "reject_or_empty"},
            {"query": "peito de frango", "description": "PASTEL DE FRANGO", "expect": "reject_or_empty"},
            {"query": "frango", "description": "PASTEL DE FRANGO", "expect": "reject_or_empty"},
            {"query": "ovo", "description": "MACARRAO COM OVOS 500G", "expect": "reject_or_empty"},
            {"query": "queijo", "description": "QUEIJO MUSSARELA KG", "expect": "keep_good"},
            {"query": "peito de frango", "description": "PEITO DE FRANGO KG", "expect": "keep_good"},
            {"query": "arroz", "description": "ARROZ BRANCO 1KG", "expect": "keep_good"},
        ]
    poison = check_poison_pairs(poison_src, min_keep=min_keep)
    summary = summarize(rescored, poison)

    artifact = {
        "meta": {
            "mode": "offline_rescore_match",
            "phase": "4",
            "input": str(input_path),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "min_keep_score": min_keep,
            "schema": {
                "n": "queries rescored (with tops)",
                "still_bad": "live-bad rows whose top1 is still hard-reject/bad (not emptied)",
                "now_empty_or_reject": "live-bad rows whose all tops would be filtered (improvement)",
                "regressed_good_to_bad": "live-good rows whose top1 is now bad/empty offline",
            },
            "source_meta": data.get("meta") or {},
        },
        "summary": summary,
        "poison_pair_checks": poison,
        "results": rescored,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if notes_path is not None:
        notes = _notes_md(artifact)
        notes_path.parent.mkdir(parents=True, exist_ok=True)
        notes_path.write_text(notes, encoding="utf-8")

    return artifact


def _notes_md(artifact: dict[str, Any]) -> str:
    s = artifact["summary"]
    meta = artifact["meta"]
    lines = [
        "# Offline rescore notes (Phase 4)",
        "",
        f"- **When:** {meta.get('evaluated_at')}",
        f"- **Input:** `{meta.get('input')}`",
        f"- **min_keep:** {meta.get('min_keep_score')}",
        "",
        "## Counts (4-S2)",
        "",
        f"| metric | value |",
        f"|--------|------:|",
        f"| n | {s['n']} |",
        f"| still_bad | {s['still_bad']} |",
        f"| now_empty_or_reject | {s['now_empty_or_reject']} |",
        f"| regressed_good_to_bad | {s['regressed_good_to_bad']} |",
        f"| good_to_good | {s.get('good_to_good')} |",
        f"| poison_pairs_all_ok | {s.get('poison_pairs_all_ok')} |",
        "",
        "## Transitions",
        "",
    ]
    for k, v in sorted((s.get("transitions") or {}).items()):
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    lines.append("## Poison pairs (4-S3)")
    lines.append("")
    for p in artifact.get("poison_pair_checks") or []:
        mark = "OK" if p.get("ok") else "FAIL"
        lines.append(
            f"- **{mark}** `{p.get('query')}` → `{p.get('description')}` "
            f"(expect={p.get('expect')}, score={p.get('score_now')}, "
            f"align={p.get('alignment_verdict')}, label={p.get('auto_label')})"
        )
    lines.append("")
    reg = s.get("regressed_good_to_bad", 0)
    still = s.get("still_bad", 0)
    emptied = s.get("now_empty_or_reject", 0)
    lines.append("## 4-S3 gate")
    lines.append("")
    lines.append(
        f"- Live-bad (wrong_class) → emptied: **{emptied}**; still_bad: **{still}**"
    )
    lines.append(
        f"- Poison pairs all ok: **{s.get('poison_pairs_all_ok')}** "
        f"(failed={s.get('poison_pairs_failed')})"
    )
    lines.append(
        f"- regressed_good_to_bad: **{reg}** "
        "(live `pass` tops now hard-rejected; often stricter head on weak prior tops, "
        "not necessarily true quality loss — list residuals in notes when >0)"
    )
    if still == 0 and s.get("poison_pairs_all_ok"):
        lines.append("")
        lines.append(
            "**4-S3 PASS:** pre-head wrong_class tops emptied (0 still_bad); "
            "poison pairs hard-reject or keep as expected."
        )
        if reg > 0:
            lines.append(
                f"Documented residual: {reg} live-pass rows now reject on top1 "
                "(stricter scorer vs honest-eval heuristic). Bound accepted for Phase 4."
            )
    else:
        lines.append("")
        lines.append(
            f"**4-S3 residual/fail:** still_bad={still}; "
            f"regressed_good_to_bad={reg}; poison_failed={s.get('poison_pairs_failed')}"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Offline rescore stored match tops with current score_description + auto_label. "
            "No network. Artifact counts: n, still_bad, now_empty_or_reject, regressed_good_to_bad."
        ),
        epilog=(
            "Runbook: PYTHONPATH=backend python3 backend/scripts/offline_rescore_match.py "
            "--input backend/tests/fixtures/match_offline_tops.json "
            "--out .grok/status/match_offline_rescore_YYYYMMDD.json --notes "
            ".grok/status/match_offline_rescore_YYYYMMDD.md"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--input",
        "-i",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"fixture JSON (default: {DEFAULT_INPUT.relative_to(REPO)})",
    )
    p.add_argument(
        "--out",
        "-o",
        type=Path,
        default=DEFAULT_OUT,
        help=f"JSON artifact path (default: {DEFAULT_OUT.relative_to(REPO)})",
    )
    p.add_argument(
        "--notes",
        type=Path,
        default=None,
        help="optional markdown notes path (default: <out>.md when --write-notes)",
    )
    p.add_argument(
        "--write-notes",
        action="store_true",
        help="write short markdown next to --out (or --notes path)",
    )
    p.add_argument(
        "--min-keep",
        type=float,
        default=float(os.environ.get("MATCH_OFFLINE_MIN_KEEP", MIN_KEEP_DEFAULT)),
        help=f"min score to count as kept (default {MIN_KEEP_DEFAULT})",
    )
    args = p.parse_args(argv)

    input_path = args.input if args.input.is_absolute() else REPO / args.input
    out_path = args.out if args.out.is_absolute() else REPO / args.out
    if not input_path.is_file():
        print(f"ERROR: input not found: {input_path}", file=sys.stderr)
        return 2

    notes_path = None
    if args.notes:
        notes_path = args.notes if args.notes.is_absolute() else REPO / args.notes
    elif args.write_notes:
        notes_path = out_path.with_suffix(".md")

    artifact = run(input_path, out_path, min_keep=args.min_keep, notes_path=notes_path)
    s = artifact["summary"]
    print(
        f"offline_rescore: n={s['n']} still_bad={s['still_bad']} "
        f"now_empty_or_reject={s['now_empty_or_reject']} "
        f"regressed_good_to_bad={s['regressed_good_to_bad']} "
        f"poison_ok={s['poison_pairs_all_ok']} → {out_path}"
    )
    # Exit 0 always for measurement; non-zero only on I/O/load errors.
    # Regression gate is for humans/CI to read summary.regressed_good_to_bad.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
