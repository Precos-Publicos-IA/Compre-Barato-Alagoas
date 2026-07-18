#!/usr/bin/env python3
"""Live match-quality eval for shopping_list_100.json against production API.

Scores each of the 100 catalog queries with modest concurrency, records latency,
match_rate, top store lines, and wrong_class heuristics. Does NOT change ranking.

Usage (from repo root or backend/):
  python3 backend/scripts/eval_shopping_list_100.py
  API_BASE=https://alagoas.precospublicos.ia.br CONCURRENCY=4 \\
    python3 backend/scripts/eval_shopping_list_100.py \\
    --out .grok/status/match_eval_100.json

Env:
  API_BASE       default https://alagoas.precospublicos.ia.br
  CONCURRENCY    default 4
  TIMEOUT_S      default 150
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REPO = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = REPO / "backend/tests/fixtures/shopping_list_100.json"
DEFAULT_OUT = REPO / ".grok/status/match_eval_100.json"

MACEIO = dict(latitude=-9.6658, longitude=-35.735, radius_km=8, days=7)


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
    # fallback: significant words length >= 3
    toks = [t for t in re.split(r"[^a-z0-9]+", nq) if len(t) >= 3]
    return toks or [nq]


def desc_has_intent(desc: str, query: str) -> bool:
    nd = norm(desc)
    tokens = intent_tokens(query)
    # Special: ovo must match word-ish ovo/ovos but pasta handled separately
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
    q_tokens = set(re.split(r"[^a-z0-9]+", nq)) - {""}

    # --- óleo / cooking oil ---
    if nq in {"oleo", "oleo de soja"} or (nq.startswith("oleo") and "coco" not in nq):
        # coco sachet / coconut oil when user wants cooking oil
        if re.search(r"\bcoco\b", nd) and "coco" not in nq:
            return True, "cooking oil query → coco (sachet/coconut oil)"
        # tiny ml packages (sachets, samples)
        m = re.search(r"(\d+)\s*ml\b", nd)
        if m and int(m.group(1)) <= 50:
            return True, f"cooking oil query → tiny package ({m.group(1)} ml)"
        # non-oil products that merely mention oil
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
        # "OLEO SATURADO" / saturated fat labels that aren't bottled cooking oil brands
        if "saturado" in nd and "soja" not in nd and "girassol" not in nd and "milho" not in nd:
            return True, "cooking oil query → OLEO SATURADO / non-standard oil label"
        # must look like cooking oil if description has no oleo at all
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
        # "S SAL" / "SEM SAL" / seasoned snacks
        s_sal = re.search(r"\bs\s*sal\b|\bsem\s+sal\b|\bcom\s+sal\b|\btemp\.?\s*sal\b", nd)
        pure_salt = re.search(
            r"\bsal\s+(refinado|grosso|light|himalaia|marinho|iodado|cisne|leseur|le saur)\b"
            r"|\bsal\s+\d|\bkg\b.*\bsal\b|\bsal\b.*\b1kg\b|\bsal\b.*\b500g\b",
            nd,
        )
        if snackish or (s_sal and not pure_salt):
            return True, "sal → snack chips / 's sal' / seasoned snack"
        # description that only has sal as abbreviation or secondary
        if "sal" in nd and not pure_salt and not re.search(r"(^|[^a-z])sal([^a-z]|$)", nd):
            pass  # rare
        if not re.search(r"(^|[^a-z])sal([^a-z]|$)", nd) and not pure_salt:
            if not desc_has_intent(description, query):
                return True, "sal → description has no salt product intent"
        # reject if clearly another product with incidental 'sal'
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
    # Prefer unique descriptions, keep first N
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


def classify_result(record: dict[str, Any]) -> str:
    """pass | wrong_class | missing | error"""
    if record.get("error") or record.get("http_status") not in (200, None):
        if record.get("http_status") == 200 and not record.get("error"):
            pass
        elif record.get("error") or (record.get("http_status") and record["http_status"] != 200):
            return "error"
    if not record.get("found"):
        return "missing"
    if record.get("wrong_class"):
        return "wrong_class"
    return "pass"


async def fetch_one(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    item: dict[str, Any],
    base: str,
    timeout_s: float,
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
    }
    async with sem:
        t0 = time.perf_counter()
        try:
            r = await client.post(url, json=payload, timeout=timeout_s)
            rec["latency_ms"] = int((time.perf_counter() - t0) * 1000)
            rec["http_status"] = r.status_code
            if r.status_code != 200:
                rec["error"] = f"HTTP {r.status_code}: {r.text[:300]}"
                rec["coverage_note"] = "non-200 response"
                rec["verdict"] = "error"
                return rec
            body = r.json()
            metrics = body.get("metrics") or {}
            rec["match_rate"] = metrics.get("match_rate")
            rec["stores_found"] = metrics.get("stores_found") or len(body.get("stores") or [])
            rec["data_source"] = body.get("data_source")
            stores = body.get("stores") or []
            # single-item found if any store has the item found
            found = False
            for st in stores:
                for it in st.get("items") or []:
                    if it.get("found"):
                        found = True
                        break
                if found:
                    break
            # also trust match_rate
            if rec["match_rate"] and rec["match_rate"] > 0:
                found = True
            rec["found"] = found
            rec["items_found"] = 1 if found else 0
            top = extract_top_lines(body, q, limit=5)
            rec["top_lines"] = top
            wrong_examples = [ln for ln in top if ln.get("wrong_class")]
            rec["wrong_class_examples"] = wrong_examples
            # Aggregate wrong_class: true if majority of top lines wrong OR top-1 wrong
            if top:
                top1_wrong = bool(top[0].get("wrong_class"))
                frac = sum(1 for ln in top if ln.get("wrong_class")) / len(top)
                rec["wrong_class"] = top1_wrong or frac >= 0.5
                if rec["wrong_class"]:
                    # prefer top1 reason
                    rec["wrong_class_reason"] = (
                        top[0].get("wrong_class_reason")
                        if top1_wrong
                        else (wrong_examples[0].get("wrong_class_reason") if wrong_examples else "majority wrong class")
                    )
            if not stores:
                rec["coverage_note"] = "zero stores / empty result"
            elif not found:
                rec["coverage_note"] = "stores present but item not found"
            rec["verdict"] = classify_result(rec)
            return rec
        except httpx.TimeoutException as e:
            rec["latency_ms"] = int((time.perf_counter() - t0) * 1000)
            rec["error"] = f"timeout: {e}"
            rec["coverage_note"] = "request timeout"
            rec["verdict"] = "error"
            return rec
        except Exception as e:
            rec["latency_ms"] = int((time.perf_counter() - t0) * 1000)
            rec["error"] = f"{type(e).__name__}: {e}"
            rec["coverage_note"] = "request failed"
            rec["verdict"] = "error"
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


async def run_eval(
    fixture_path: Path,
    out_path: Path,
    base: str,
    concurrency: int,
    timeout_s: float,
    offset: int = 0,
    limit: int | None = None,
) -> dict[str, Any]:
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    items = data["items"]
    if offset or limit is not None:
        end = len(items) if limit is None else min(len(items), offset + limit)
        items = items[offset:end]
    total = len(items)
    sem = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(max_connections=concurrency + 2, max_keepalive_connections=concurrency)
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(limits=limits, headers={"User-Agent": "CBA-match-eval/1.0"}) as client:
        # progress in batches for logging
        tasks = [fetch_one(client, sem, it, base, timeout_s) for it in items]
        done = 0
        ckpt = out_path.with_suffix(".partial.json")
        for coro in asyncio.as_completed(tasks):
            rec = await coro
            results.append(rec)
            done += 1
            flag = rec["verdict"]
            print(
                f"[{done:3d}/{total}] id={rec['id']:3d} {rec['query']!r:30s} "
                f"http={rec['http_status']} {rec['latency_ms']}ms "
                f"found={rec['found']} wrong={rec['wrong_class']} → {flag}"
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
                    ),
                    encoding="utf-8",
                )

    results.sort(key=lambda r: r["id"])
    latencies = [r["latency_ms"] for r in results if r.get("latency_ms") is not None]
    by_verdict: dict[str, int] = {"pass": 0, "wrong_class": 0, "missing": 0, "error": 0}
    for r in results:
        by_verdict[r["verdict"]] = by_verdict.get(r["verdict"], 0) + 1

    summary = {
        "total": len(results),
        "pass": by_verdict.get("pass", 0),
        "wrong_class": by_verdict.get("wrong_class", 0),
        "missing": by_verdict.get("missing", 0),
        "error": by_verdict.get("error", 0),
        "found_count": sum(1 for r in results if r.get("found")),
        "latency_ms": {
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "min": min(latencies) if latencies else None,
            "max": max(latencies) if latencies else None,
            "mean": statistics.mean(latencies) if latencies else None,
        },
        "by_category": {},
    }
    cats: dict[str, dict[str, int]] = {}
    for r in results:
        c = r["category"]
        cats.setdefault(c, {"total": 0, "pass": 0, "wrong_class": 0, "missing": 0, "error": 0})
        cats[c]["total"] += 1
        cats[c][r["verdict"]] = cats[c].get(r["verdict"], 0) + 1
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
            "timeout_s": timeout_s,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "worker": "W-eval-100",
        },
        "summary": summary,
        "results": results,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {out_path} summary={summary}", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--api-base", default=None)
    ap.add_argument("--concurrency", type=int, default=None)
    ap.add_argument("--timeout", type=float, default=None)
    ap.add_argument("--offset", type=int, default=0, help="0-based index into fixture items")
    ap.add_argument("--limit", type=int, default=None, help="max items from offset")
    args = ap.parse_args()
    import os

    base = args.api_base or os.environ.get("API_BASE", "https://alagoas.precospublicos.ia.br")
    conc = args.concurrency or int(os.environ.get("CONCURRENCY", "4"))
    timeout_s = args.timeout or float(os.environ.get("TIMEOUT_S", "150"))
    asyncio.run(
        run_eval(
            args.fixture,
            args.out,
            base,
            conc,
            timeout_s,
            offset=args.offset,
            limit=args.limit,
        )
    )


if __name__ == "__main__":
    main()
