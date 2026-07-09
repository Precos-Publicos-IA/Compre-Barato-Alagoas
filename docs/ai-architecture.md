# AI architecture — Requester + Verifier (cost-first)

**Status:** active design for implementation  
**Principle:** controlled complexity for *logarithmic* cost vs users — not inventing from scratch.

## Audit of the original plan

| Original idea | Verdict | Adjustment |
|---------------|---------|------------|
| Two specialized agents (Requester / Verifier) | **Keep** | Valid multi-agent *role* split (planner/executor vs critic). Do **not** make them free-chat peers. |
| RAG over past successful queries | **Keep** | Metadata RAG only — never a full SEFAZ mirror. |
| Verifier can re-request | **Keep, bounded** | Max **1** re-query round per basket item (plan-execute, not open ReAct loop). |
| User prefs for query writing | **Keep** | Favorites / excluded stores already on the request; use them in ranking first, in query only when favorites dominate. |
| Organize inputs + responses for future | **Keep** | Redis term-mapping store now; pgvector later when volume justifies it. |
| Do not rebuild SEFAZ catalog | **Keep** | Confirmed: SEFAZ remains source of truth for prices/geo. |
| Full agentic multi-hop LLM | **Reject for v1** | 2026 research: agentic RAG is ~2–3.6× cost vs optimized Enhanced RAG for similar quality. |

## Validated patterns we follow (2025–2026)

Sources: production RAG/agent surveys, Adaptive RAG, CRAG/Self-RAG critics, model routing, semantic caching, plan-then-execute (not free multi-agent networks).

1. **Multi-tier cache first** (largest cost lever)  
   Exact basket/term cache → (later) semantic near-hit → then agents. Shopping queries in one city are highly repetitive.

2. **Cheap router, not a supervisor LLM**  
   Deterministic rules + RAG hit/miss decide the path. No Sonnet/Opus “orchestrator.”

3. **Plan-then-Execute, not peer multi-agent chat**  
   Fixed pipeline with optional one retry. Predictable latency, auditability, testability.

4. **Enhanced RAG + critic (CRAG-style)**  
   Retrieve known good `user_term → sefaz_term` mappings; Verifier scores results with **rules first**; LLM only when uncertain (v2).

5. **Model cascade**  
   80%+ of traffic: mock/deterministic parse + RAG rewrite (\$0 LLM).  
   Cold/complex lists: small model only for *JSON list parse*.  
   Never Opus / Sonnet for this product path.

6. **Hierarchical memory**  
   Short-term: current request context.  
   Long-term: success/failure term mappings (Redis; later embeddings in pgvector).

## Pipeline (what we implement)

```
POST /api/v1/search
        │
        ▼
┌───────────────────┐
│ Exact response /  │  already: per-term SEFAZ cache + list UUID
│ term cache (Redis)│
└─────────┬─────────┘
          │ miss
          ▼
┌───────────────────┐
│ REQUESTER         │  parse_list (LLM or mock) + RAG rewrite search_term
│ (query writer)    │  uses known successful mappings
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ SEFAZ fan-out     │  web or API client; concurrent; partial results OK
│ (existing)        │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ VERIFIER (critic) │  score match; record RAG; if zero-match + known alt
│                   │  → ONE re-fetch with better term; else suggest
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Rank + prefs      │  coverage > price > distance; excluded CNPJs
└───────────────────┘
```

### Requester responsibilities

- Parse free-text basket → `{label, search_term, quantity}`  
- Rewrite `search_term` via RAG when history beats the raw parse  
- Stay **stateless** except via RAGStore (no personal data in RAG keys)  
- **Not** responsible for ranking or “did SEFAZ answer well?”

### Verifier responsibilities

- Score whether offers are plausible for the user’s label (token overlap / category noise)  
- Record successful mappings (and, later, hard failures) into RAGStore  
- On zero-match: propose known-good alternative term → orchestrator may re-fetch **once**  
- Surface PT user-facing “Tente X…” suggestions when still empty  
- **Not** a second full LLM conversation

### Shared knowledge (RAGStore)

| Store | Purpose | Backend now | Later |
|-------|---------|-------------|--------|
| `user_term → effective_terms` (scored) | Rewrite vague input | Redis ZSET | + embeddings |
| products that “existed” for a term | Confidence for verifier | offer counts on mapping | optional product fingerprints |
| non-existent / toxic terms | Avoid repeat bad SEFAZ calls | (v1.1) | same |

**Explicit non-goal:** full product price warehouse. SEFAZ + short TTL offer cache remain authoritative.

## Models (honest cost)

| Role | Choice | Why |
|------|--------|-----|
| List parse (production) | **Claude Haiku** (current default) *or* **Gemini Flash-Lite / GPT-4o-mini** if we multi-vendor later | Small structured JSON task; Haiku already wired + prompt-cache friendly |
| List parse (dev) | **Mock** (deterministic) | Architecture must work without \$\$ |
| Query rewrite | **No LLM** — RAG + rules | History beats another model call |
| Result verification | **No LLM v1** — deterministic scorer | CRAG-style critic without tokens |
| Embeddings (v2) | Local / cheap embed API | Only when keyword RAG plateaus |
| Never | Opus, Sonnet, o3, multi-agent free debate | Cost + false confidence |

Rough math: one Haiku parse of a 5-item list ≈ few hundred tokens → **≪ R\$0.01**.  
With RAG + cache, most repeat searches pay **\$0 LLM**.  
R\$20 experiment budget ≈ tens of thousands of Haiku parse calls — enough to validate, not to burn on Sonnet.

**Development rule:** validate architecture on mock + RAG first; turn Haiku on only for integration checks. An architecture that only works with a big model is a failed architecture for this product.

## Implementation stages

| Stage | Deliverable | Status |
|-------|-------------|--------|
| A | Keyword RAG + BasicRequester/Verifier | Exists |
| B | RAGStore module, relevance scoring, **1 retry** orchestration | **This work** |
| C | Failure memory (`record_miss`), prewarm popular terms | Next |
| D | Optional embedding similarity (pgvector already in compose image) | When A/B metrics demand it |
| E | Multi-provider small-model adapter (Gemini/OpenAI) | Optional cost race |

## Observability

Already: admin timings (`llm`, `sefaz`, `normalize`, `rank`), provider health, LLM cost.  
Add: `requester_rag_hits`, `verifier_retries`, `verifier_suggestions` in metrics/analytics when cheap.

## Risks

| Risk | Mitigation |
|------|------------|
| Infinite re-query loops | Hard cap 1 per item |
| RAG learns garbage | Only record `offers_found ≥ 1`; optional min score |
| Pet-food / noise offers | Deterministic relevance filter (also used by web SEFAZ client) |
| LLM outage | Mock fallback (already) |
| Cost surprise | Default mock in dev; Haiku only with key; cache first |

