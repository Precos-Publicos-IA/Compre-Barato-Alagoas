#!/usr/bin/env python3
"""Honest live match-quality eval for shopping_list_100.json against production API.

Methodology (post-f7ef373 invalid parallel stampede):
  - Default CONCURRENCY=1 (cap 2) — serial/low for production SEFAZ web path
  - On empty stores OR match_rate==0: one retry after short backoff (default 3s)
  - Verdicts: pass | wrong_class | missing_after_retry | upstream_error
  - Records data_source, latency, top lines; flushed progress; final JSON + human report

Usage (from repo root):
  API_BASE=https://alagoas.precospublicos.ia.br CONCURRENCY=1 \\
    python3 backend/scripts/eval_shopping_list_100.py \\
    --out .grok/status/match_eval_100_honest.json

  # Probe-only (single staple; exit 2 on 429 so CI/orchestrator can hard-block):
  python3 backend/scripts/eval_shopping_list_100.py --probe-only

Env:
  API_BASE       default https://alagoas.precospublicos.ia.br
  CONCURRENCY    default 1 (max enforced 2)
  TIMEOUT_S      default 150
  RETRY_BACKOFF_S  default 3.0 (empty/zero-match retry delay)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import statistics
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REPO = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = REPO / "backend/tests/fixtures/shopping_list_100.json"
DEFAULT_OUT = REPO / ".grok/status/match_eval_100_honest.json"
DEFAULT_REPORT = REPO / ".grok/status/match_eval_100_honest_report.md"

MACEIO = dict(latitude=-9.6658, longitude=-35.735, radius_km=8, days=7)
MAX_CONCURRENCY = 2
DEFAULT_CONCURRENCY = 1
DEFAULT_RETRY_BACKOFF_S = 3.0
WORKER_ID = "W-eval-honest"


def strip_accents(s: str) -> str:
    nk = unicodedata.normalize("NFD", s)
    return "".join(c for c in nk if unicodedata.category(c) != "Mn")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", strip_accents(s or "").lower()).strip()


# Primary intent tokens per query (normalized). Multi-word: all tokens should appear
# OR any synonym group. Generic fallback: first significant token of query.
INTENT_ALIASES: dict[str, list[str]] = {
    "arroz": ["arroz"],
    "feijao": ["feijao"],
    "feijao preto": ["feijao"],
    "acucar": ["acucar"],
    "acucar demerara": ["acucar", "demerara"],
    "sal": ["sal"],
    "farinha de trigo": ["farinha", "trigo"],
    "farinha de mandioca": ["farinha", "mandioca"],
    "fuba": ["fuba"],
    "macarrao": ["macarrao", "macarr", "espaguete", "parafuso", "penne", "nhoque"],
    "macarrao espaguete": ["macarrao", "espaguete", "macarr"],
    "aveia": ["aveia"],
    "leite": ["leite"],
    "leite integral": ["leite"],
    "leite desnatado": ["leite", "desnat"],
    "leite em po": ["leite"],
    "ovo": ["ovo", "ovos"],
    "ovos": ["ovo", "ovos"],
    "manteiga": ["manteiga"],
    "margarina": ["margarina"],
    "queijo": ["queijo"],
    "queijo mussarela": ["queijo", "mussarela", "muzarela", "muçarela", "mozarel"],
    "requeijao": ["requeijao"],
    "iogurte": ["iogurte", "yogurt", "iougurte"],
    "oleo": ["oleo"],
    "oleo de soja": ["oleo", "soja"],
    "azeite": ["azeite"],
    "vinagre": ["vinagre"],
    "molho de tomate": ["molho", "tomate", "extrato"],
    "catchup": ["catchup", "ketchup", "catch"],
    "maionese": ["maionese", "mayonnaise"],
    "mostarda": ["mostarda"],
    "tempero": ["tempero"],
    "alho": ["alho"],
    "cebola": ["cebola"],
    "caldo de galinha": ["caldo", "galinha", "knorr", "maggi"],
    "frango": ["frango", "galinha"],
    "peito de frango": ["peito", "frango"],
    "carne moida": ["carne", "moida", "moid"],
    "carne": ["carne", "bovina", "patinho", "alcatra", "acem", "picanha"],
    "linguica": ["linguica"],
    "salsicha": ["salsicha"],
    "bacon": ["bacon", "toucinho"],
    "presunto": ["presunto"],
    "peixe": ["peixe", "tilapia", "file de peixe"],
    "sardinha": ["sardinha"],
    "atum": ["atum"],
    "mortadela": ["mortadela"],
    "banana": ["banana"],
    "tomate": ["tomate"],
    "batata": ["batata"],
    "batata doce": ["batata", "doce"],
    "cenoura": ["cenoura"],
    "alface": ["alface"],
    "limao": ["limao"],
    "laranja": ["laranja"],
    "maca": ["maca"],
    "mamao": ["mamao"],
    "abobora": ["abobora", "jerimum"],
    "chuchu": ["chuchu"],
    "pao": ["pao"],
    "pao de forma": ["pao", "forma"],
    "pao frances": ["pao", "frances", "cacetinho"],
    "bolo": ["bolo"],
    "biscoito": ["biscoito", "bolacha"],
    "bolacha": ["bolacha", "biscoito"],
    "torrada": ["torrada", "toast"],
    "pao de queijo": ["pao de queijo", "pao queijo"],
    "cafe": ["cafe"],
    "cafe soluvel": ["cafe", "soluvel", "nescafe"],
    "agua": ["agua"],
    "refrigerante": ["refrigerante", "refri", "coca", "guarana", "pepsi", "fanta", "soda"],
    "coca cola": ["coca", "cola"],
    "suco": ["suco", "nectar"],
    "cerveja": ["cerveja", "skol", "brahma", "heineken", "antarctica", "itaipava"],
    "cha": ["cha"],
    "achocolatado": ["achocolatado", "nescau", "toddy", "chocolate em po"],
    "agua de coco": ["coco"],
    "salgadinho": ["salgadinho", "chips", "doritos", "ruffles", "cheetos", "fandango"],
    "pipoca": ["pipoca", "milho de pipoca"],
    "chocolate": ["chocolate", "choc"],
    "amendoim": ["amendoim"],
    "batata chips": ["chips", "batata", "ruffles", "lays", "pringles"],
    "barra de cereal": ["barra", "cereal", "nutribar"],
    "sabao em po": ["sabao", "omo", "surf", "ariel", "tixan", "acelera"],
    "detergente": ["detergente", "limpol", "ypê", "ype"],
    "agua sanitaria": ["sanitaria", "sanitario", "cloro", "qboa", "q-boa"],
    "amaciante": ["amaciante", "downy", "comfort"],
    "desinfetante": ["desinfetante", "pine", "lysoform", "veja"],
    "esponja": ["esponja", "bombril", "scotch"],
    "papel toalha": ["papel toalha", "toalha", "snob", "kitchen"],
    "saco de lixo": ["saco", "lixo"],
    "sabonete": ["sabonete", "dove", "lux", "protex"],
    "shampoo": ["shampoo", "xampu"],
    "creme dental": ["creme dental", "pasta de dente", "colgate", "closeup", "sensodyne", "oral-b"],
    "papel higienico": ["papel higienico", "higienico", "nevel", "personal", "scott", "folhada"],
    "desodorante": ["desodorante", "rexona", "nivea", "dove", "axe", "old spice"],
    "condicionador": ["condicionador"],
    "fralda": ["fralda", "pampers", "huggies", "babysec", "cremer"],
    "racao": ["racao", "pedigree", "whiskas", "golden", "premier"],
}


def intent_tokens(query: str) -> list[str]:
    nq = norm(query)
    if nq in INTENT_ALIASES:
        return INTENT_ALIASES[nq]
    toks = [t for t in re.split(r"[^a-z0-9]+", nq) if len(t) >= 3]
    return toks or [nq]


def desc_has_intent(desc: str, query: str) -> bool:
    nd = norm(desc)
    tokens = intent_tokens(query)
    for t in tokens:
        if t in nd:
            return True
    return False


def check_wrong_class(query: str, description: str) -> tuple[bool, str | None]:
    """Return (is_wrong, reason). Heuristics for known PR1 pain points + generic."""
    if not description:
        return False, None
    nq = norm(query)
    nd = norm(description)

    # --- óleo / cooking oil ---
    if nq in {"oleo", "oleo de soja"} or (nq.startswith("oleo") and "coco" not in nq):
        if re.search(r"\bcoco\b", nd) and "coco" not in nq:
            return True, "cooking oil query → coco (sachet/coconut oil)"
        m = re.search(r"(\d+)\s*ml\b", nd)
        if m and int(m.group(1)) <= 50:
            return True, f"cooking oil query → tiny package ({m.group(1)} ml)"
        non_oil = [
            (r"\bsard\.?\b|\bsardinha\b", "sardine in oil, not cooking oil"),
            (r"\batum\b", "tuna in oil, not cooking oil"),
            (r"\bmist\.?\s*leite|mistura.*leite", "milk/oil mix, not cooking oil"),
            (r"\bcreme\b.*\boleo\b|\boleo\b.*\bcreme\b", "cream product, not cooking oil"),
            (r"\bshampoo\b|\bcondicionador\b|\bsabonete\b", "personal care, not cooking oil"),
            (r"\bpintura\b|\bmotor\b|\blubrificante\b", "industrial/motor oil"),
        ]
        for pat, reason in non_oil:
            if re.search(pat, nd):
                return True, f"cooking oil query → {reason}"
        if "saturado" in nd and "soja" not in nd and "girassol" not in nd and "milho" not in nd:
            return True, "cooking oil query → OLEO SATURADO / non-standard oil label"
        if "oleo" not in nd and "óleo" not in norm(description):
            if not desc_has_intent(description, query):
                return True, "cooking oil query → description has no oil intent"

    # --- ovo / ovos → pasta MAC/macarrão c/ovos ---
    if nq in {"ovo", "ovos"}:
        if re.search(r"\bmac\b|\bmacarr|\bmacarrao|\bespaguete|\bmassa\b|\bfuradinho\b|\bnhoque\b|\bpenne\b", nd):
            return True, "ovo/ovos → pasta MAC/macarrão c/ovos"
        if re.search(r"\bbolo\b|\bbiscoito\b|\bbisco\b|\bcookie\b", nd) and re.search(r"\bovo", nd):
            return True, "ovo/ovos → baked good with egg, not eggs"
        if re.search(r"\bshampoo\b|\btinta\b|\bcolester\b", nd):
            return True, "ovo/ovos → non-food egg product"

    # --- sal → snack chips / “s sal” cashews ---
    if nq == "sal":
        snackish = re.search(
            r"\bchips\b|\bsalgadinho\b|\bdoritos\b|\bruffles\b|\bcheetos\b|"
            r"\bamendoim\b|\bcastanha\b|\bcaju\b|\bpipoca\b|\bbiscoito\b|"
            r"\bbisco\b|\bsnack\b|\bbatata\b.*\bsal\b",
            nd,
        )
        s_sal = re.search(r"\bs\s*sal\b|\bsem\s+sal\b|\bcom\s+sal\b|\btemp\.?\s*sal\b", nd)
        pure_salt = re.search(
            r"\bsal\s+(refinado|grosso|light|himalaia|marinho|iodado|cisne|leseur|le saur)\b"
            r"|\bsal\s+\d|\bkg\b.*\bsal\b|\bsal\b.*\b1kg\b|\bsal\b.*\b500g\b",
            nd,
        )
        if snackish or (s_sal and not pure_salt):
            return True, "sal → snack chips / 's sal' / seasoned snack"
        if not re.search(r"(^|[^a-z])sal([^a-z]|$)", nd) and not pure_salt:
            if not desc_has_intent(description, query):
                return True, "sal → description has no salt product intent"
        if re.search(r"\bpresunto\b|\bqueijo\b|\bcarne\b|\bfrango\b", nd) and not pure_salt:
            return True, "sal → meat/cheese product, not table salt"

    # --- feijão → tempero trap ---
    if nq in {"feijao", "feijao preto"}:
        if re.search(r"\btempe[ri]|\btempero\b", nd) and not re.search(
            r"\bfeijao\s+(carioca|preto|mulatinho|tipo)", nd
        ):
            return True, "feijão → tempero para feijão (seasoning, not beans)"

    # --- café → unrelated ---
    if nq in {"cafe", "cafe soluvel"}:
        if re.search(r"\bcafeteria\b|\bfiltro de cafe\b|\bfiltro\b.*\bpapel\b", nd):
            return True, "café → filter/accessories, not coffee"
        if re.search(r"\bcaramelo\b|\bbala\b|\bdoce\b", nd) and "soluvel" not in nd:
            return True, "café → candy/caramel, not coffee"
        if re.search(r"coracao|canela", nd) and not re.search(
            r"\bcafe\s+(pilao|melitta|3\s*coracoes|utam|soluvel|torrado|po)\b", nd
        ):
            return True, "café → spice/flavor mix or unrelated"
        if re.search(r"\bachocolatado\b|\bchocolate\b|\bleite\b", nd) and "cafe" not in nd:
            return True, "café → unrelated beverage/snack"

    # --- açúcar: candy/not sugar ---
    if nq in {"acucar", "acucar demerara"}:
        if re.search(r"\bbigbig\b|\bbala\b|\bchiclete\b|\bzero\s+acucar\b", nd):
            return True, "açúcar → candy / zero-sugar confection"
        m = re.search(r"(\d+)\s*g\b", nd)
        if m and int(m.group(1)) <= 50 and "cristal" not in nd and "demerara" not in nd:
            return True, "açúcar → tiny sachet / non-household pack"
        if re.search(r"\bbala\b|\bdoce\b|\bchocolate\b|\bchiclete\b", nd) and "acucar" not in nd:
            return True, "açúcar → candy without sugar product intent"

    # --- leite: candy ---
    if nq.startswith("leite"):
        if re.search(r"\bbala\b|\bcaramelo\b|\bpocket\b|\bchocolate\b", nd) and "uht" not in nd:
            if re.search(r"\bbala\b|\bcaramelo\b|\bpocket\b", nd):
                return True, "leite → candy/caramel, not milk"

    # --- cross-query egg bleed ---
    if nq not in {"ovo", "ovos"} and re.search(r"\bovos?\b", nd) and not desc_has_intent(
        description, query
    ):
        return True, "cross-query bleed: eggs returned for non-egg query"

    # --- generic: no primary intent token ---
    if not desc_has_intent(description, query):
        return True, "generic: description has no primary intent token"

    return False, None


def extract_top_lines(body: dict[str, Any], query: str, limit: int = 5) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for store in body.get("stores") or []:
        for item in store.get("items") or []:
            if not item.get("found"):
                continue
            desc = item.get("description") or ""
            wrong, reason = check_wrong_class(query, desc)
            lines.append(
                {
                    "store": store.get("name"),
                    "description": desc,
                    "price": item.get("price"),
                    "unit_price": item.get("unit_price"),
                    "quantity": item.get("quantity"),
                    "unit": item.get("unit"),
                    "package_label": item.get("package_label"),
                    "wrong_class": wrong,
                    "wrong_class_reason": reason,
                }
            )
        if len(lines) >= limit * 2:
            break
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for ln in lines:
        key = norm(ln["description"])
        if key in seen:
            continue
        seen.add(key)
        out.append(ln)
        if len(out) >= limit:
            break
    return out


def is_upstream_status(status: int | None) -> bool:
    if status is None:
        return False
    return status == 429 or status >= 500


def classify_result(record: dict[str, Any]) -> str:
    """pass | wrong_class | missing_after_retry | upstream_error"""
    status = record.get("http_status")
    if record.get("error") or (status is not None and status != 200):
        if is_upstream_status(status):
            return "upstream_error"
        if status is not None and status != 200:
            return "upstream_error"
        if record.get("error") and not record.get("found"):
            # transport/timeout → treat as upstream
            return "upstream_error"
    if not record.get("found"):
        return "missing_after_retry"
    if record.get("wrong_class"):
        return "wrong_class"
    return "pass"


def apply_body_to_record(rec: dict[str, Any], body: dict[str, Any], query: str) -> None:
    metrics = body.get("metrics") or {}
    rec["match_rate"] = metrics.get("match_rate")
    rec["stores_found"] = metrics.get("stores_found") or len(body.get("stores") or [])
    rec["data_source"] = body.get("data_source")
    stores = body.get("stores") or []
    found = False
    for st in stores:
        for it in st.get("items") or []:
            if it.get("found"):
                found = True
                break
        if found:
            break
    if rec["match_rate"] and rec["match_rate"] > 0:
        found = True
    rec["found"] = found
    rec["items_found"] = 1 if found else 0
    top = extract_top_lines(body, query, limit=5)
    rec["top_lines"] = top
    wrong_examples = [ln for ln in top if ln.get("wrong_class")]
    rec["wrong_class_examples"] = wrong_examples
    if top:
        top1_wrong = bool(top[0].get("wrong_class"))
        frac = sum(1 for ln in top if ln.get("wrong_class")) / len(top)
        rec["wrong_class"] = top1_wrong or frac >= 0.5
        if rec["wrong_class"]:
            rec["wrong_class_reason"] = (
                top[0].get("wrong_class_reason")
                if top1_wrong
                else (
                    wrong_examples[0].get("wrong_class_reason")
                    if wrong_examples
                    else "majority wrong class"
                )
            )
    else:
        rec["wrong_class"] = False
        rec["wrong_class_reason"] = None
    if not stores:
        rec["coverage_note"] = "zero stores / empty result"
    elif not found:
        rec["coverage_note"] = "stores present but item not found"
    else:
        rec["coverage_note"] = None


def needs_empty_retry(rec: dict[str, Any]) -> bool:
    """Retry once when empty stores or match_rate is 0 (not on hard upstream errors)."""
    if rec.get("http_status") != 200:
        return False
    if rec.get("error"):
        return False
    stores = rec.get("stores_found")
    mr = rec.get("match_rate")
    if stores == 0 or stores is None:
        return True
    if mr is not None and mr == 0 and not rec.get("found"):
        return True
    if not rec.get("found") and (stores == 0 or mr == 0):
        return True
    return False


async def http_post_search(
    client: httpx.AsyncClient,
    url: str,
    payload: dict[str, Any],
    timeout_s: float,
) -> tuple[int | None, dict[str, Any] | None, str | None, int]:
    """Return (status, body_or_none, error_or_none, latency_ms)."""
    t0 = time.perf_counter()
    try:
        r = await client.post(url, json=payload, timeout=timeout_s)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        if r.status_code != 200:
            return r.status_code, None, f"HTTP {r.status_code}: {r.text[:300]}", latency_ms
        try:
            body = r.json()
        except Exception as e:
            return r.status_code, None, f"json_decode: {e}", latency_ms
        return r.status_code, body, None, latency_ms
    except httpx.TimeoutException as e:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return None, None, f"timeout: {e}", latency_ms
    except Exception as e:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return None, None, f"{type(e).__name__}: {e}", latency_ms


async def fetch_one(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    item: dict[str, Any],
    base: str,
    timeout_s: float,
    retry_backoff_s: float,
) -> dict[str, Any]:
    q = item["query"]
    rid = item["id"]
    cat = item["category"]
    url = f"{base.rstrip('/')}/api/v1/search"
    payload = {"items": [q], **MACEIO}
    rec: dict[str, Any] = {
        "id": rid,
        "query": q,
        "category": cat,
        "latency_ms": None,
        "latency_ms_attempts": [],
        "http_status": None,
        "match_rate": None,
        "stores_found": None,
        "found": False,
        "items_found": 0,
        "top_lines": [],
        "wrong_class": False,
        "wrong_class_reason": None,
        "wrong_class_examples": [],
        "coverage_note": None,
        "error": None,
        "data_source": None,
        "verdict": None,
        "attempts": 0,
        "retried": False,
        "retry_reason": None,
    }
    async with sem:
        status, body, err, lat = await http_post_search(client, url, payload, timeout_s)
        rec["attempts"] = 1
        rec["latency_ms_attempts"].append(lat)
        rec["latency_ms"] = lat
        rec["http_status"] = status
        if err and body is None:
            rec["error"] = err
            if status is not None and status != 200:
                rec["coverage_note"] = "non-200 response"
            elif err.startswith("timeout"):
                rec["coverage_note"] = "request timeout"
            else:
                rec["coverage_note"] = "request failed"
            rec["verdict"] = classify_result(rec)
            return rec

        assert body is not None
        apply_body_to_record(rec, body, q)

        if needs_empty_retry(rec):
            rec["retried"] = True
            rec["retry_reason"] = (
                f"empty_or_zero_match (stores_found={rec.get('stores_found')}, "
                f"match_rate={rec.get('match_rate')})"
            )
            await asyncio.sleep(retry_backoff_s)
            status2, body2, err2, lat2 = await http_post_search(client, url, payload, timeout_s)
            rec["attempts"] = 2
            rec["latency_ms_attempts"].append(lat2)
            rec["latency_ms"] = sum(rec["latency_ms_attempts"])
            rec["http_status"] = status2
            if err2 and body2 is None:
                rec["error"] = err2
                rec["found"] = False
                rec["items_found"] = 0
                rec["top_lines"] = []
                if status2 is not None and status2 != 200:
                    rec["coverage_note"] = "non-200 on retry"
                else:
                    rec["coverage_note"] = "retry failed"
            else:
                assert body2 is not None
                rec["error"] = None
                apply_body_to_record(rec, body2, q)
                if not rec.get("found"):
                    note = rec.get("coverage_note") or "empty after retry"
                    rec["coverage_note"] = f"{note} (after 1 retry)"

        rec["verdict"] = classify_result(rec)
        return rec


def percentile(vals: list[float], p: float) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    if len(s) == 1:
        return float(s[0])
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return float(s[f])
    return float(s[f] + (s[c] - s[f]) * (k - f))


def write_human_report(out: dict[str, Any], report_path: Path) -> None:
    meta = out["meta"]
    summary = out["summary"]
    results = out["results"]
    lines: list[str] = []
    lines.append("# Honest match eval — shopping_list_100")
    lines.append("")
    lines.append(f"- **Worker:** `{meta.get('worker')}`")
    lines.append(f"- **API:** `{meta.get('api_base')}`")
    lines.append(f"- **Evaluated at (UTC):** {meta.get('evaluated_at')}")
    lines.append(f"- **Concurrency:** {meta.get('concurrency')} (max {MAX_CONCURRENCY})")
    lines.append(f"- **Retry backoff (s):** {meta.get('retry_backoff_s')}")
    lines.append(f"- **Timeout (s):** {meta.get('timeout_s')}")
    lines.append(f"- **Fixture:** `{meta.get('fixture')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|--------|------:|")
    lines.append(f"| total | {summary['total']} |")
    lines.append(f"| pass | {summary.get('pass', 0)} |")
    lines.append(f"| wrong_class | {summary.get('wrong_class', 0)} |")
    lines.append(f"| missing_after_retry | {summary.get('missing_after_retry', 0)} |")
    lines.append(f"| upstream_error | {summary.get('upstream_error', 0)} |")
    lines.append(f"| found_count | {summary.get('found_count', 0)} |")
    lines.append(f"| retried_count | {summary.get('retried_count', 0)} |")
    lines.append("")
    lat = summary.get("latency_ms") or {}
    lines.append("### Latency (ms)")
    lines.append("")
    lines.append(f"- p50: {lat.get('p50')}")
    lines.append(f"- p95: {lat.get('p95')}")
    lines.append(f"- min/max: {lat.get('min')} / {lat.get('max')}")
    lines.append(f"- mean: {lat.get('mean')}")
    lines.append("")
    lines.append("### By category")
    lines.append("")
    lines.append("| category | total | pass | wrong_class | missing_after_retry | upstream_error |")
    lines.append("|----------|------:|-----:|------------:|--------------------:|---------------:|")
    for cat, c in sorted((summary.get("by_category") or {}).items()):
        lines.append(
            f"| {cat} | {c.get('total', 0)} | {c.get('pass', 0)} | {c.get('wrong_class', 0)} | "
            f"{c.get('missing_after_retry', 0)} | {c.get('upstream_error', 0)} |"
        )
    lines.append("")
    lines.append("## Failures / non-pass")
    lines.append("")
    for r in results:
        if r.get("verdict") == "pass":
            continue
        top0 = (r.get("top_lines") or [{}])[0] if r.get("top_lines") else {}
        desc = (top0.get("description") or "")[:90]
        lines.append(
            f"- **id={r['id']}** `{r['query']}` → `{r['verdict']}` "
            f"http={r.get('http_status')} ds={r.get('data_source')} "
            f"stores={r.get('stores_found')} mr={r.get('match_rate')} "
            f"retried={r.get('retried')} "
            f"{('top=' + desc) if desc else ''} "
            f"{('err=' + str(r.get('error'))[:80]) if r.get('error') else ''} "
            f"{('reason=' + str(r.get('wrong_class_reason'))) if r.get('wrong_class_reason') else ''}"
        )
    lines.append("")
    lines.append("## Methodology notes")
    lines.append("")
    lines.append(
        "- Serial/low concurrency only (default 1, cap 2) — avoids SEFAZ stampede false empties."
    )
    lines.append(
        "- One retry on empty stores or match_rate=0 after short backoff; "
        "`missing_after_retry` only after that retry fails to find items."
    )
    lines.append(
        "- `upstream_error` = HTTP 429/5xx/non-200 or transport/timeout (not product missing)."
    )
    lines.append(
        "- Prior parallel eval `f7ef373` is INVALID for coverage; do not compare raw missing rates to it."
    )
    lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote human report {report_path}", flush=True)


async def run_eval(
    fixture_path: Path,
    out_path: Path,
    report_path: Path,
    base: str,
    concurrency: int,
    timeout_s: float,
    retry_backoff_s: float,
    offset: int = 0,
    limit: int | None = None,
) -> dict[str, Any]:
    concurrency = max(1, min(int(concurrency), MAX_CONCURRENCY))
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    items = data["items"]
    if offset or limit is not None:
        end = len(items) if limit is None else min(len(items), offset + limit)
        items = items[offset:end]
    total = len(items)
    sem = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(max_connections=concurrency + 2, max_keepalive_connections=concurrency)
    results: list[dict[str, Any]] = []
    print(
        f"Honest eval start: n={total} concurrency={concurrency} "
        f"retry_backoff_s={retry_backoff_s} base={base}",
        flush=True,
    )
    async with httpx.AsyncClient(
        limits=limits, headers={"User-Agent": "CBA-match-eval-honest/1.0"}
    ) as client:
        tasks = [
            fetch_one(client, sem, it, base, timeout_s, retry_backoff_s) for it in items
        ]
        done = 0
        ckpt = out_path.with_suffix(".partial.json")
        for coro in asyncio.as_completed(tasks):
            rec = await coro
            results.append(rec)
            done += 1
            flag = rec["verdict"]
            top0 = ""
            if rec.get("top_lines"):
                top0 = (rec["top_lines"][0].get("description") or "")[:50]
            print(
                f"[{done:3d}/{total}] id={rec['id']:3d} {rec['query']!r:30s} "
                f"http={rec['http_status']} {rec['latency_ms']}ms "
                f"ds={rec.get('data_source')} stores={rec.get('stores_found')} "
                f"found={rec['found']} retry={rec.get('retried')} wrong={rec['wrong_class']} → {flag}"
                + (f" top={top0!r}" if top0 else "")
                + (f" err={rec['error'][:60]}" if rec.get("error") else ""),
                flush=True,
            )
            if done % 5 == 0 or done == total:
                ckpt.write_text(
                    json.dumps(
                        {
                            "done": done,
                            "offset": offset,
                            "limit": limit,
                            "results": sorted(results, key=lambda r: r["id"]),
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

    results.sort(key=lambda r: r["id"])
    latencies = [r["latency_ms"] for r in results if r.get("latency_ms") is not None]
    verdict_keys = ("pass", "wrong_class", "missing_after_retry", "upstream_error")
    by_verdict: dict[str, int] = {k: 0 for k in verdict_keys}
    for r in results:
        v = r["verdict"]
        by_verdict[v] = by_verdict.get(v, 0) + 1

    summary = {
        "total": len(results),
        "pass": by_verdict.get("pass", 0),
        "wrong_class": by_verdict.get("wrong_class", 0),
        "missing_after_retry": by_verdict.get("missing_after_retry", 0),
        "upstream_error": by_verdict.get("upstream_error", 0),
        "found_count": sum(1 for r in results if r.get("found")),
        "retried_count": sum(1 for r in results if r.get("retried")),
        "latency_ms": {
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "min": min(latencies) if latencies else None,
            "max": max(latencies) if latencies else None,
            "mean": statistics.mean(latencies) if latencies else None,
        },
        "by_category": {},
        "data_sources": {},
    }
    cats: dict[str, dict[str, int]] = {}
    for r in results:
        c = r["category"]
        cats.setdefault(
            c,
            {
                "total": 0,
                "pass": 0,
                "wrong_class": 0,
                "missing_after_retry": 0,
                "upstream_error": 0,
            },
        )
        cats[c]["total"] += 1
        cats[c][r["verdict"]] = cats[c].get(r["verdict"], 0) + 1
        ds = r.get("data_source") or ("error" if r.get("error") else "unknown")
        summary["data_sources"][ds] = summary["data_sources"].get(ds, 0) + 1
    summary["by_category"] = cats

    out = {
        "meta": {
            "api_base": base,
            "fixture": str(fixture_path),
            "fixture_commit_hint": "81bed97",
            "latitude": MACEIO["latitude"],
            "longitude": MACEIO["longitude"],
            "radius_km": MACEIO["radius_km"],
            "days": MACEIO["days"],
            "concurrency": concurrency,
            "max_concurrency": MAX_CONCURRENCY,
            "timeout_s": timeout_s,
            "retry_backoff_s": retry_backoff_s,
            "retry_on": "empty_stores_or_match_rate_0",
            "methodology": "honest_serial_low_concurrency",
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "worker": WORKER_ID,
            "invalidates_prior": "f7ef373",
        },
        "summary": summary,
        "results": results,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {out_path} summary={summary}", flush=True)
    write_human_report(out, report_path)
    return out


async def probe_once(base: str, timeout_s: float, query: str = "arroz") -> dict[str, Any]:
    """Single search probe. Returns structured result; does not write full eval."""
    url = f"{base.rstrip('/')}/api/v1/search"
    payload = {"items": [query], **MACEIO}
    async with httpx.AsyncClient(headers={"User-Agent": "CBA-match-eval-honest/1.0"}) as client:
        status, body, err, lat = await http_post_search(client, url, payload, timeout_s)
    result: dict[str, Any] = {
        "query": query,
        "http_status": status,
        "latency_ms": lat,
        "error": err,
        "data_source": None,
        "stores_found": None,
        "match_rate": None,
        "found": False,
        "top_description": None,
        "blocked_429": status == 429,
        "ok_for_full_eval": False,
    }
    if body:
        result["data_source"] = body.get("data_source")
        metrics = body.get("metrics") or {}
        result["match_rate"] = metrics.get("match_rate")
        result["stores_found"] = metrics.get("stores_found") or len(body.get("stores") or [])
        stores = body.get("stores") or []
        for st in stores:
            for it in st.get("items") or []:
                if it.get("found"):
                    result["found"] = True
                    result["top_description"] = it.get("description")
                    break
            if result["found"]:
                break
        if result["match_rate"] and result["match_rate"] > 0:
            result["found"] = True
        result["ok_for_full_eval"] = status == 200 and (
            (result["stores_found"] or 0) > 0 or result["found"]
        )
    return result


def write_blocked_429_evidence(probe: dict[str, Any], base: str) -> Path:
    path = REPO / ".grok/status/match_eval_100_honest_BLOCKED_429.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    text = f"""# F BLOCKED_429 — honest 100 live re-eval

**Status:** hard-blocked on production daily search quota  
**Worker:** `{WORKER_ID}`  
**Recorded (UTC):** {now}

## Probe evidence (single call — did not burn 100)

| Field | Value |
|-------|-------|
| API | `{base}` |
| Query | `{probe.get('query')}` |
| HTTP | **{probe.get('http_status')}** |
| Latency ms | {probe.get('latency_ms')} |
| Error / body | `{probe.get('error')}` |
| data_source | {probe.get('data_source')} |
| stores_found | {probe.get('stores_found')} |
| found | {probe.get('found')} |

Production response (expected):

```text
{{"detail":"Limite diário de buscas atingido. Tente novamente amanhã."}}
```

## Why we stop

Prior invalid eval (`f7ef373`) used parallel load and poisoned empty-cache. Full honest
serial 100 would burn the remaining quota for no usable coverage while 429 is active.
**Do not** re-run the full 100 until a single staple probe returns HTTP 200 with stores.

## Script ready

Honest methodology is implemented in `backend/scripts/eval_shopping_list_100.py`:

- default `CONCURRENCY=1` (hard cap 2)
- one retry on empty stores / match_rate=0 after backoff
- verdicts: `pass` | `wrong_class` | `missing_after_retry` | `upstream_error`
- flushed progress, JSON + human report

## Re-run tomorrow (or when quota resets)

```bash
# 1) Probe first
python3 backend/scripts/eval_shopping_list_100.py --probe-only

# 2) If probe is 200 with stores for arroz (or any staple), full serial 100:
API_BASE=https://alagoas.precospublicos.ia.br CONCURRENCY=1 \\
  python3 backend/scripts/eval_shopping_list_100.py \\
  --out .grok/status/match_eval_100_honest.json
```

Exit codes:

- probe `--probe-only`: **0** if ok for full eval; **2** if 429/blocked; **1** other failure
- full eval: **0** always writes report (inspect `upstream_error` count)

## Related

- Catalog fixture: `backend/tests/fixtures/shopping_list_100.json` (A DONE)
- Match relevance fixes: `5853031` (C DONE)
- Empty-cache poison fix: task E (parallel worker)
"""
    path.write_text(text, encoding="utf-8")
    print(f"Wrote hard-block evidence {path}", flush=True)
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Human markdown report path (default: out with _report.md suffix or default report)",
    )
    ap.add_argument("--api-base", default=None)
    ap.add_argument("--concurrency", type=int, default=None)
    ap.add_argument("--timeout", type=float, default=None)
    ap.add_argument(
        "--retry-backoff",
        type=float,
        default=None,
        help=f"seconds before empty/zero-match retry (default {DEFAULT_RETRY_BACKOFF_S})",
    )
    ap.add_argument("--offset", type=int, default=0, help="0-based index into fixture items")
    ap.add_argument("--limit", type=int, default=None, help="max items from offset")
    ap.add_argument(
        "--probe-only",
        action="store_true",
        help="Single arroz probe; exit 2 on 429, 0 if ok for full eval. Does not run 100.",
    )
    ap.add_argument(
        "--probe-query",
        default="arroz",
        help="Query used with --probe-only (default arroz)",
    )
    args = ap.parse_args()

    base = args.api_base or os.environ.get("API_BASE", "https://alagoas.precospublicos.ia.br")
    raw_conc = args.concurrency if args.concurrency is not None else int(
        os.environ.get("CONCURRENCY", str(DEFAULT_CONCURRENCY))
    )
    if raw_conc > MAX_CONCURRENCY:
        print(
            f"WARN: CONCURRENCY={raw_conc} capped to {MAX_CONCURRENCY} (honest eval)",
            flush=True,
        )
    conc = max(1, min(int(raw_conc), MAX_CONCURRENCY))
    timeout_s = args.timeout if args.timeout is not None else float(
        os.environ.get("TIMEOUT_S", "150")
    )
    retry_backoff_s = (
        args.retry_backoff
        if args.retry_backoff is not None
        else float(os.environ.get("RETRY_BACKOFF_S", str(DEFAULT_RETRY_BACKOFF_S)))
    )
    # keep backoff in 2–5s band unless user overrides far outside
    if args.retry_backoff is None and not os.environ.get("RETRY_BACKOFF_S"):
        retry_backoff_s = max(2.0, min(5.0, retry_backoff_s))

    if args.probe_only:
        probe = asyncio.run(probe_once(base, timeout_s, query=args.probe_query))
        print(json.dumps(probe, ensure_ascii=False, indent=2), flush=True)
        if probe.get("blocked_429") or probe.get("http_status") == 429:
            write_blocked_429_evidence(probe, base)
            sys.exit(2)
        if not probe.get("ok_for_full_eval"):
            print(
                "Probe not OK for full eval "
                f"(http={probe.get('http_status')} stores={probe.get('stores_found')} "
                f"found={probe.get('found')})",
                flush=True,
            )
            sys.exit(1)
        print("Probe OK — safe to run full serial 100.", flush=True)
        sys.exit(0)

    report_path = args.report
    if report_path is None:
        if args.out == DEFAULT_OUT:
            report_path = DEFAULT_REPORT
        else:
            report_path = args.out.with_name(args.out.stem + "_report.md")

    asyncio.run(
        run_eval(
            args.fixture,
            args.out,
            report_path,
            base,
            conc,
            timeout_s,
            retry_backoff_s,
            offset=args.offset,
            limit=args.limit,
        )
    )


if __name__ == "__main__":
    main()
