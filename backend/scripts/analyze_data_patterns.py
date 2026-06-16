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
<h2>Análise de Padrões de Dados (SEFAZ + normalização)</h2>
<p><em>Gerado em {p['generated_at']} via simulações realistas com o catálogo mock (proxy para dados reais até token SEFAZ). {p['queries_run']} queries de usuários 'burros' (curtas, vagas, sem marca, tamanhos misturados, 'e', etc).</em></p>

<h3>Resumo executivo (pronto para escala)</h3>
<ul>
  <li>Match rate geral: <strong>{p['overall_match_rate']*100:.1f}%</strong> — bom para termos comuns de mercearia; cai forte em itens não modelados no catálogo.</li>
  <li>Ofertas médias por item: <strong>{p['avg_offers_per_query']}</strong> — SEFAZ devolve volume útil (lojas dentro raio). Cache por (termo+lat+lon+raio+dias) é crítico.</li>
  <li>Taxa de parse de quantidade: <strong>{p['avg_quantity_parse_rate']*100:.1f}%</strong> — o coração do "preço justo". Fallback para preço por pacote ainda útil mas menos honesto.</li>
  <li>Not-found em termos vagos: <strong>{p['not_found_rate_on_vague']*100:.1f}%</strong> — normal; o Verifier agent deve sugerir similar (ex: 'manteiga' -> 'margarina' ou 'creme vegetal' se soubermos do histórico).</li>
</ul>

<h3>Timings (mock, lower bound; real SEFAZ + LLM adicionam latência de rede)</h3>
<ul>
  <li>Parse (mock LLM): p50 ~{p['timing_ms']['parse_p50']}ms</li>
  <li>SEFAZ (mock): p50 ~{p['timing_ms']['sefaz_p50']}ms por item</li>
  <li>Normalização: p50 ~{p['timing_ms']['normalize_p50']}ms</li>
  <li>E2E p95 (uma busca de 1-3 itens): ~{p['timing_ms']['end_to_end_p95']}ms</li>
</ul>
<p><strong>Implicação de escala:</strong> Cada item = 1 chamada SEFAZ (sem token ainda não medimos, mas espere 200-800ms + variação). Cache hit = ~0 custo SEFAZ. Ver "Plano de Escadas" abaixo.</p>

<h3>Padrões observados nas descrições (o que o normalizador enfrenta)</h3>
<ul>
  <li>Descrições reais (amostra): {', '.join(repr(d) for d in p['description_patterns']['sample_realistic_descs'])}</li>
  <li>Tokens de unidade comuns: {', '.join(p['description_patterns']['common_unidade_medida_tokens'])}</li>
  <li>GTIN presente em ~{p['description_patterns']['gtin_presence_rate_estimate']*100:.0f}% das ofertas úteis (fresco/hortifruti quase nunca tem; confiar em descrição + keywords do mock/LLM).</li>
  <li>Tamanho da embalagem <strong>sempre</strong> no texto livre da descricao (ex: "ARROZ BRANCO TIPO 1 PCT 5KG", "LEITE NA CAIXA INTEGRAL 1L"). O campo unidadeMedida é a unidade de venda, não o tamanho.</li>
</ul>

<h3>Sinais de "dados ruins" ou armadilhas</h3>
<ul>
  {"".join(f"<li>{s}</li>" for s in p['bad_data_signals'])}
  <li>Preços variam por loja (price_factor + jitter) + dataVenda recente (últimos N dias). Nunca prometa "hoje"; mostre a data da venda.</li>
  <li>Lojas de categorias diferentes (farmácia não vende arroz) — o mock já filtra por categories; real SEFAZ pode devolver lixo que o ranking deve ignorar ou o normalizador descartar.</li>
</ul>

<h3 id="stairs-plan">Plano de Escadas — Otimizações de Custo/Escala (logarítmico, não linear)</h3>
<p>Objetivo: custo de LLM+SEFAZ ~ log(N usuários) graças a camadas de cache + dedup semântico. Não implemente tudo agora (complexidade mata velocidade para 100 usuários iniciais).</p>

<ol>
  <li><strong>Agora (0-1k usuários, mock ou primeiros reais)</strong><br>
    - Cache Redis exato por (search_term, lat~0.0001, lon, raio, dias) — já existe.<br>
    - Dedup de listas idênticas por hash (save_search_list) — já existe.<br>
    - LLM só no parse de lista (mock ou Haiku barato). Fallback mock sempre.<br>
    - Admin timings + providers para medir degradação real de SEFAZ/LLM.<br>
    - Limite diário 300/buscas por device (rate limit por IP hash + device).<br>
    <em>Custo: ~linear com buscas novas; hit rate alto em Maceió itens populares.</em></li>

  <li><strong>5k usuários (pico de adoção local)</strong><br>
    - Semantic query cache: embed normalized search_term (ou full basket hash) + cosine >0.93 -> hit cached response (ou re-rank local). Redis + pgvector ou Redis vector.<br>
    - Response-side cache: armazene normalized offers + ranking por fingerprint do resultado SEFAZ (hash dos registros + data max).<br>
    - Popular items pre-warm (top 50 de stats:items:searched) em background job (1x/h).<br>
    - Model router: use Haiku para 95% dos parses; só Opus/Sonnet em listas >8 itens ambíguas (detect por #tokens ou entropy).<br>
    - Early cutoff: se 0 offers após 1a página e termo vago, pare e marque "poucos resultados" (não puxe 500 sempre).<br>
    <em>Redução esperada: 40-70% chamadas SEFAZ/LLM via semântica + pre-warm.</em></li>

  <li><strong>20k usuários (crescimento + outras cidades AL)</strong><br>
    - RAG leve sobre histórico de buscas bem-sucedidas: "arroz 5kg" -> equivalentes que já deram match alto ("ARROZ TIPO1 5KG", "ARROZ BRANCO PCT 5KG"). Index em pgvector (config já tem DATABASE_URL opcional).<br>
    - Verifier agent (ver abaixo) filtra/ruído e faz 1 re-query só quando necessário (ex: usuário pediu "arroz integral" e só veio branco -> oferecer similar ou pedir clarificação).<br>
    - Sharded cache por região (lat/lon grid grosseiro) + TTL mais curto para produtos voláteis (hortifruti 2h, mercearia 6-12h).<br>
    - Analytics-driven invalidation: quando parse_method distribution piora ou notfound sobe, force refresh de top itens.<br>
    <em>Meta: custo por usuário novo cai; MAU alto com baixo custo marginal.</em></li>

  <li><strong>100k usuários (estado + viralidade)</strong><br>
    - Full agentic: requester (parse + rewrite + RAG past successful mappings) + verifier (relevance + similarity + user prefs filter) orquestrados (LangGraph-like, ou simples state machine em Python).<br>
    - Multi-model: SLM local/small (Phi-3 / Gemma / Haiku) para router, query rewrite, verifier scoring; Haiku só para parse difícil + final synthesis.<br>
    - Persistent product catalog index (GTIN + normalized descs que sabemos que existem) em pgvector para "produtos que existem" / "não existem" — evita SEFAZ em itens sabidamente ruins.<br>
    - Edge cache (CDN para web) + app on-device recent results + suggestions offline.<br>
    - Budget guard: circuit breaker por provedor (se SEFAZ p95 >1.5s ou error >5%, force mock + warn no admin).<br>
    <em>Logarítmico: 80%+ hits em camadas sem tocar LLM/SEFAZ.</em></li>

  <li><strong>1M+ usuários (nacional? ou outros estados copiam)</strong><br>
    - Distributed: múltiplas regiões com cache local + async replication de popular fingerprints.<br>
    - Heavy pre-compute: nightly "cestas básicas" + promoções detectadas; push only para consented devices (sem polling).<br>
    - Graph RAG ou item-item co-occurrence (de buscas reais) para "pessoas que buscam arroz também compram..." sem LLM por request.<br>
    - Custo por busca deve estar < R$0.0005 (com cache + routing) mesmo em pico; monetize via parcerias SEFAZ-like ou "apoiadores locais" em vez de ads invasivos.<br>
    - Hardcore: learned embeddings de produtos SEFAZ + approximate NN para "melhor match" sem chamada por item (futuro, quando tivermos 10M+ registros reais).<br>
    <em>Não linear nunca: o sistema inteiro vira um filtro inteligente + cache gigante + ocasional verificação barata.</em></li>
</ol>

<p><strong>Hard rules para o plano:</strong> Nunca pague linear em tokens SEFAZ/LLM. Sempre meça (admin já tem). Prefira complexidade controlada (mais camadas de cache + roteamento) a "simples e rápido de shipar" quando o simples explode a conta em 10k usuários.</p>

<h3>Como usar este relatório</h3>
<p>1. Rode o script periodicamente (ou adicione job) para atualizar os números com dados reais (flip USE_MOCK_*=false + token).<br>
2. O admin panel (timings, items, quality) é o "live" equivalente — use-o como fonte de verdade para quando o cache está frio.<br>
3. Quando adicionar o requester/verifier agents (próxima fase), alimente-os com os "bad_data_signals" e "description_patterns" daqui como few-shot + RAG corpus.</p>
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
    (out_dir / "data-patterns.html").write_text("<!DOCTYPE html>\n<html lang=\"pt-BR\"><head><meta charset=\"utf-8\"><title>Padrões de Dados · Compre Barato Alagoas</title><link rel=\"stylesheet\" href=\"styles.css\"></head><body><div class=\"layout\"><main class=\"content\">" + html + "<p><a href=\"index.html\">← Voltar</a></p></main></div></body></html>", encoding="utf-8")
    print("\nWrote docs/data-patterns.html and data-patterns-report.json")
    print("To view in docs site: add link in index.html nav + content.")
