#!/usr/bin/env python3
"""
Data patterns analyzer for Compre Barato Alagoas.

Runs a battery of realistic "dumb user" queries against the mock SEFAZ + normalization
stack (and real when wired) to discover:
- response formats, timing, volume
- match quality, quantity parse success
- description patterns (size presence, GTIN, unidadeMedida, freshness)
- not-found / vague term behavior
- cache behavior signals

Output: console report + JSON + HTML fragment suitable for docs/data-patterns.html

This is the "live rolling data analysis" layer. Run manually during dev or in CI to
regenerate the patterns doc. Do NOT call real SEFAZ in loops (rate limit).

Usage (after venv with backend[dev]):
  python -m backend.scripts.analyze_data_patterns
  # or from backend/: PYTHONPATH=. python scripts/analyze_data_patterns.py
"""
from __future__ import annotations

import asyncio
import json
import statistics
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# We import from the package so the same normalization/llm/sefaz paths are used.
import sys

# Allow running as script or module
if __name__ == "__main__" and "backend" not in str(Path.cwd()):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.llm.mock_client import MockLLMClient
from app.services.normalization.matcher import normalize_offer
from app.services.sefaz.mock_client import MockSefazClient
from app.services.sefaz.models import PesquisaResponse

# Realistic dumb-user queries (short, vague, compound, with/without sizes, brands, typos-ish)
DUMB_QUERIES: list[str] = [
    "arroz",
    "5kg arroz",
    "leite",
    "leite 1L",
    "2 litros de leite",
    "feijao",
    "feijão preto",
    "arroz e feijao",
    "coca cola 2L",
    "refrigerante",
    "sabao em po",
    "sabonete",
    "pao",
    "pão francês",
    "frango",
    "peito de frango",
    "banana",
    "tomate",
    "acucar",
    "açúcar",
    "cafe",
    "óleo",
    "macarrao",
    "dipirona",
    "fralda",
    "cerveja",
    "arroz integral",
    "leite em po",
    "ovos",
    "o mais barato arroz",
    "manteiga",  # likely low match in mock
    "iogurte",   # likely low match
    "detergente",
    "shampoo",
]

MACEIO = dict(latitude=-9.6633, longitude=-35.7089, radius_km=8, days=7)

@dataclass
class QueryResult:
    raw: str
    parsed_items: int
    parse_time_ms: float
    sefaz_time_ms: float
    norm_time_ms: float
    total_time_ms: float
    items_with_match: int
    total_offers: int
    quantity_parsed_rate: float
    sample_descs: list[str]
    sample_unidades: list[str]
    has_gtin_count: int
    not_found: bool
    avg_price: float | None

async def analyze_one(llm: MockLLMClient, sefaz: MockSefazClient, raw: str) -> QueryResult:
    t0 = time.perf_counter()
    pres = await llm.parse_list([raw])
    parse_ms = (time.perf_counter() - t0) * 1000
    parsed = pres.items

    sefaz_ms = 0.0
    norm_ms = 0.0
    offers: list = []
    matched = 0
    total_off = 0
    q_parsed = 0
    descs: list[str] = []
    ums: list[str] = []
    gtin_c = 0
    prices: list[float] = []

    for pitem in parsed:
        t1 = time.perf_counter()
        resp: PesquisaResponse = await sefaz.search_product(
            descricao=pitem.search_term, **MACEIO, registros_por_pagina=100
        )
        sefaz_ms += (time.perf_counter() - t1) * 1000

        t2 = time.perf_counter()
        for reg in resp.conteudo:
            if (o := normalize_offer(reg)) is not None:
                offers.append(o)
                descs.append(o.description[:70])
                if o.unidade_medida:
                    ums.append(o.unidade_medida)
                if o.gtin:
                    gtin_c += 1
                prices.append(o.price)
        norm_ms += (time.perf_counter() - t2) * 1000

    total_off = len(offers)
    matched = 1 if offers else 0
    qpr = (sum(1 for o in offers if o.quantity_parsed) / total_off) if total_off else 0.0
    avg_p = round(statistics.mean(prices), 2) if prices else None

    total_ms = (time.perf_counter() - t0) * 1000
    return QueryResult(
        raw=raw,
        parsed_items=len(parsed),
        parse_time_ms=round(parse_ms, 1),
        sefaz_time_ms=round(sefaz_ms, 1),
        norm_time_ms=round(norm_ms, 1),
        total_time_ms=round(total_ms, 1),
        items_with_match=matched,
        total_offers=total_off,
        quantity_parsed_rate=round(qpr, 3),
        sample_descs=list(dict.fromkeys(descs))[:3],  # dedup order preserve
        sample_unidades=list(dict.fromkeys(ums))[:4],
        has_gtin_count=gtin_c,
        not_found=(len(parsed) > 0 and total_off == 0),
        avg_price=avg_p,
    )

async def run_analysis() -> dict[str, Any]:
    llm = MockLLMClient()
    sefaz = MockSefazClient()

    results: list[QueryResult] = []
    for q in DUMB_QUERIES:
        r = await analyze_one(llm, sefaz, q)
        results.append(r)
        await asyncio.sleep(0)  # yield

    # Aggregate patterns
    total_q = len(results)
    match_rate = sum(r.items_with_match for r in results) / total_q if total_q else 0
    avg_offers = statistics.mean([r.total_offers for r in results]) if results else 0
    avg_qpr = statistics.mean([r.quantity_parsed_rate for r in results if r.total_offers]) if any(r.total_offers for r in results) else 0
    notfound_rate = sum(1 for r in results if r.not_found) / total_q
    parse_times = [r.parse_time_ms for r in results]
    sefaz_times = [r.sefaz_time_ms for r in results]
    norm_times = [r.norm_time_ms for r in results]
    total_times = [r.total_time_ms for r in results]

    # Description patterns across all
    all_descs = [d for r in results for d in r.sample_descs]
    all_ums = [u for r in results for u in r.sample_unidades]
    gtin_hits = sum(r.has_gtin_count for r in results)

    patterns = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "queries_run": total_q,
        "overall_match_rate": round(match_rate, 3),
        "avg_offers_per_query": round(avg_offers, 1),
        "avg_quantity_parse_rate": round(avg_qpr, 3),
        "not_found_rate_on_vague": round(notfound_rate, 3),
        "timing_ms": {
            "parse_p50": round(statistics.median(parse_times), 1),
            "sefaz_p50": round(statistics.median(sefaz_times), 1),
            "normalize_p50": round(statistics.median(norm_times), 1),
            "end_to_end_p95": round(sorted(total_times)[int(0.95 * len(total_times))], 1) if total_times else 0,
        },
        "description_patterns": {
            "sample_realistic_descs": all_descs[:8],
            "common_unidade_medida_tokens": list(dict.fromkeys(all_ums))[:6],
            "gtin_presence_rate_estimate": round(gtin_hits / max(1, sum(r.total_offers for r in results)), 3),
            "note": "GTIN often absent for fresh produce; sizes live in free-text descricao.",
        },
        "bad_data_signals": [
            "Short/vague terms (pao, arroz) still match well in catalog but would be broader on real SEFAZ.",
            "Compound inputs split by mock LLM; real Claude will do better on 'arroz e feijao 2kg'.",
            "Phrases with 'o mais barato' are stripped to keyword (good); size in user text is dropped from search_term (intentional).",
            "Not-found items (manteiga, iogurte in current mock) surface as 0 offers -> verifier layer opportunity.",
        ],
        "per_query": [asdict(r) for r in results],
    }
    return patterns

def render_html_report(p: dict[str, Any]) -> str:
    return f"""<section id="data-patterns">
<h2>Data Pattern Analysis (SEFAZ + normalization)</h2>
<p><em>Generated at {p['generated_at']} via realistic simulations against the mock catalog (proxy for real data until a SEFAZ token is available). {p['queries_run']} "dumb user" queries (short, vague, no brand, mixed sizes, 'e'/and, etc.).</em></p>

<h3>Executive summary (scale-ready)</h3>
<ul>
  <li>Overall match rate: <strong>{p['overall_match_rate']*100:.1f}%</strong> — good for common grocery terms; drops hard on items not modeled in the catalog.</li>
  <li>Average offers per item: <strong>{p['avg_offers_per_query']}</strong> — SEFAZ returns useful volume (stores within radius). Cache by (term+lat+lon+radius+days) is critical.</li>
  <li>Quantity parse rate: <strong>{p['avg_quantity_parse_rate']*100:.1f}%</strong> — the heart of "fair price". Package-price fallback is still useful but less honest.</li>
  <li>Not-found on vague terms: <strong>{p['not_found_rate_on_vague']*100:.1f}%</strong> — expected; the Verifier agent should suggest similar (e.g. 'manteiga' -> 'margarina' or 'creme vegetal' when history knows them).</li>
</ul>

<h3>Timings (mock lower bound; real SEFAZ + LLM add network latency)</h3>
<ul>
  <li>Parse (mock LLM): p50 ~{p['timing_ms']['parse_p50']}ms</li>
  <li>SEFAZ (mock): p50 ~{p['timing_ms']['sefaz_p50']}ms per item</li>
  <li>Normalization: p50 ~{p['timing_ms']['normalize_p50']}ms</li>
  <li>E2E p95 (one 1–3 item search): ~{p['timing_ms']['end_to_end_p95']}ms</li>
</ul>
<p><strong>Scale implication:</strong> Each item = 1 SEFAZ call (without a token we have not measured yet, but expect 200–800ms + variance). Cache hit = ~0 SEFAZ cost. See "Stair-step Plan" below.</p>

<h3>Patterns in descriptions (what the normalizer faces)</h3>
<ul>
  <li>Realistic descriptions (sample): {', '.join(repr(d) for d in p['description_patterns']['sample_realistic_descs'])}</li>
  <li>Common unit tokens: {', '.join(p['description_patterns']['common_unidade_medida_tokens'])}</li>
  <li>GTIN present in ~{p['description_patterns']['gtin_presence_rate_estimate']*100:.0f}% of useful offers (fresh produce almost never has it; trust description + mock/LLM keywords).</li>
  <li>Package size is <strong>always</strong> in free-text descricao (e.g. "ARROZ BRANCO TIPO 1 PCT 5KG", "LEITE NA CAIXA INTEGRAL 1L"). The unidadeMedida field is the sale unit, not the package size.</li>
</ul>

<h3>"Bad data" signals and traps</h3>
<ul>
  {"".join(f"<li>{s}</li>" for s in p['bad_data_signals'])}
  <li>Prices vary by store (price_factor + jitter) + recent dataVenda (last N days). Never promise "today"; show the sale date.</li>
  <li>Stores have different categories (a pharmacy does not sell rice) — the mock already filters by categories; real SEFAZ may return noise that ranking should ignore or the normalizer should drop.</li>
</ul>

<h3 id="stairs-plan">Stair-step Plan — Cost/Scale Optimizations (logarithmic, not linear)</h3>
<p>Goal: LLM+SEFAZ cost ~ log(N users) thanks to cache layers + semantic dedup. Do not implement everything now (complexity kills speed for the first 100 users).</p>

<ol>
  <li><strong>Now (0–1k users, mock or first real traffic)</strong><br>
    - Exact Redis cache by (search_term, lat~0.0001, lon, radius, days) — already exists.<br>
    - Dedup of identical lists by hash (save_search_list) — already exists.<br>
    - LLM only for list parse (mock or cheap Haiku). Mock fallback always.<br>
    - Admin timings + providers to measure real SEFAZ/LLM degradation.<br>
    - Daily limit 300 searches per device (rate limit by IP hash + device).<br>
    <em>Cost: ~linear with new searches; high hit rate on popular Maceió items.</em></li>

  <li><strong>5k users (local adoption peak)</strong><br>
    - Semantic query cache: embed normalized search_term (or full basket hash) + cosine &gt;0.93 -&gt; hit cached response (or re-rank locally). Redis + pgvector or Redis vector.<br>
    - Response-side cache: store normalized offers + ranking by SEFAZ result fingerprint (hash of records + max date).<br>
    - Popular items pre-warm (top 50 of stats:items:searched) in a background job (1x/h).<br>
    - Model router: Haiku for 95% of parses; Opus/Sonnet only on ambiguous lists &gt;8 items (detect by #tokens or entropy).<br>
    - Early cutoff: if 0 offers after page 1 and the term is vague, stop and mark "few results" (do not always pull 500).<br>
    <em>Expected reduction: 40–70% SEFAZ/LLM calls via semantic cache + pre-warm.</em></li>

  <li><strong>20k users (growth + other AL cities)</strong><br>
    - Light RAG over successful search history: "arroz 5kg" -&gt; equivalents that already matched well ("ARROZ TIPO1 5KG", "ARROZ BRANCO PCT 5KG"). Index in pgvector (config already has optional DATABASE_URL).<br>
    - Verifier agent filters noise and re-queries only when needed (e.g. user asked "arroz integral" and only white rice came back -&gt; offer similar or ask for clarification).<br>
    - Sharded cache by region (coarse lat/lon grid) + shorter TTL for volatile products (produce 2h, grocery 6–12h).<br>
    - Analytics-driven invalidation: when parse_method distribution worsens or notfound rises, force refresh of top items.<br>
    <em>Goal: cost per new user falls; high MAU with low marginal cost.</em></li>

  <li><strong>100k users (state-wide + virality)</strong><br>
    - Full agentic: requester (parse + rewrite + RAG past successful mappings) + verifier (relevance + similarity + user prefs filter) orchestrated (LangGraph-like, or a simple Python state machine).<br>
    - Multi-model: local/small SLM (Phi-3 / Gemma / Haiku) for router, query rewrite, verifier scoring; Haiku only for hard parse + final synthesis.<br>
    - Persistent product catalog index (GTIN + normalized descs we know exist) in pgvector for "products that exist" / "don't exist" — skip SEFAZ on known-bad items.<br>
    - Edge cache (CDN for web) + app on-device recent results + offline suggestions.<br>
    - Budget guard: circuit breaker per provider (if SEFAZ p95 &gt;1.5s or error &gt;5%, force mock + warn in admin).<br>
    <em>Logarithmic: 80%+ hits in layers without touching LLM/SEFAZ.</em></li>

  <li><strong>1M+ users (national? or other states copy)</strong><br>
    - Distributed: multiple regions with local cache + async replication of popular fingerprints.<br>
    - Heavy pre-compute: nightly "basic baskets" + detected promotions; push only to consented devices (no polling).<br>
    - Graph RAG or item-item co-occurrence (from real searches) for "people who search rice also buy..." without LLM per request.<br>
    - Cost per search should be &lt; R$0.0005 (with cache + routing) even at peak; monetize via SEFAZ-like partnerships or "local supporters" instead of invasive ads.<br>
    - Hardcore: learned embeddings of SEFAZ products + approximate NN for "best match" without a call per item (future, once we have 10M+ real records).<br>
    <em>Never linear: the whole system becomes a smart filter + giant cache + occasional cheap verification.</em></li>
</ol>

<p><strong>Hard rules for the plan:</strong> Never pay linear in SEFAZ/LLM tokens. Always measure (admin already has this). Prefer controlled complexity (more cache layers + routing) over "simple and fast to ship" when simple blows the bill at 10k users.</p>

<h3>How to use this report</h3>
<p>1. Run the script periodically (or add a job) to refresh numbers with real data (flip USE_MOCK_*=false + token).<br>
2. The admin panel (timings, items, quality) is the live equivalent — use it as the source of truth when the cache is cold.<br>
3. When adding requester/verifier agents (next phase), feed them the "bad_data_signals" and "description_patterns" from here as few-shot + RAG corpus.</p>
</section>
"""

if __name__ == "__main__":
    p = asyncio.run(run_analysis())
    print("=== DATA PATTERNS REPORT ===")
    print(json.dumps(p, indent=2, ensure_ascii=False)[:3000])
    print("... (truncated; full in JSON)")

    out_dir = Path(__file__).resolve().parents[2] / "docs"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "data-patterns-report.json").write_text(json.dumps(p, indent=2, ensure_ascii=False), encoding="utf-8")
    html = render_html_report(p)
    (out_dir / "data-patterns.html").write_text("<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><title>Data Patterns · Compre Barato Alagoas</title><link rel=\"stylesheet\" href=\"styles.css\"></head><body><div class=\"layout\"><main class=\"content\">" + html + "<p><a href=\"index.html\">← Back</a></p></main></div></body></html>", encoding="utf-8")
    print("\nWrote docs/data-patterns.html and data-patterns-report.json")
    print("To view in docs site: add link in index.html nav + content.")
