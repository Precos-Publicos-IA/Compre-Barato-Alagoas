# Matching reliability plan — Compre Barato Alagoas

**Status:** actionable backlog (grounded in codebase + eval evidence)  
**Written:** 2026-07-23  
**Updated:** 2026-07-23 — **head-aligned spine shipped** (`rag/intent.py` + score/rewrite gates; property tests in `tests/test_intent_heads.py`). B1 “queijo denylist” **superseded** by systemic head alignment.  
**Product lock:** Alagoas only  
**North star:** A Maceió shopper trusts the top line enough to leave for a store.

---

## 1. Current architecture (short)

```
POST /api/v1/search (+ optional SSE progress)
        │
        ▼
Requester  (llm/requester.py BasicRequester)
  · parse_list → {label, search_term, quantity}
  · RAG rewrite via rag/store.py lookup + rewrite_compatible filter
        │
        ▼
Fetch per item  (search_service.fetch_offers)
  · Redis term cache sefaz:search:* (non-empty only; empty purged)
  · SEFAZ: factory.build_sefaz_client → HttpSefazClient only by default
    (use_web_sefaz=False; website scraper retired for live — commit 6affe85)
  · asyncio.Semaphore(sefaz_concurrency=3) + sefaz_item_deadline_seconds=55
  · normalize_offer → NormalizedOffer
        │
        ▼
Verifier  (llm/verifier.py BasicVerifier)
  · rag/relevance.filter_offers (score_description, min_score=0.35)
  · hard rejects + package_class_rank gates
  · record_success only if score≥0.50 AND package_class_ok
  · max 1 retry term from RAG (rewrite_compatible only)
        │
        ▼
Rank  (ranking.build_store_results)
  · best offer: package_class_rank → unit_price → freshness → pack R$
  · stores: items_found desc → favorites → total asc → distance
        │
        ▼
UI  progressive partials + wait copy; PR3 coverage gate (≥0.7) for primary savings
```

| Stage | Key symbols / paths |
|-------|---------------------|
| Orchestration | `search_service.run_search`, `llm/orchestrator.SearchOrchestrator` |
| Rewrite safety | `rag/store.rewrite_compatible`, `_class_conflict`, `filter_compatible_terms` |
| Relevance | `rag/relevance.score_description`, `_hard_reject_score`, `package_class_rank` |
| Package class | `ranking._best_offer` → `offer_package_class_rank` |
| Upstream | `sefaz/http_client.HttpSefazClient`, `sefaz/factory.build_sefaz_client` |
| Metrics honesty | `SearchMetrics.items_fetch_failed`, `fetch_failed_labels` vs true no_data |
| Eval harness | `backend/scripts/eval_shopping_list_100.py` + `tests/fixtures/shopping_list_100.json` |

**Already shipped (do not re-litigate as open P0s):**

| Ship | SHA / report | What it fixed |
|------|--------------|---------------|
| PR1 package-class oil/egg | `504eb38` / `worker_w_pr1_match_report.md` | coco 15 ml, MAC OVOS |
| Empty-cache poison | `c92b9ba` / `worker_w_fix_empty_cache_report.md` | no cache of empty/failed SEFAZ |
| P0 relevance gates | `5853031` / `worker_w_match_improve_report.md` | egg bleed scoring, sal/óleo/feijão/açúcar/café |
| RAG cross-class block | `efca61d` / `worker_w_g_improve_report.md` | peito→ovos poison learn/apply |
| H deploy + Redis flush | `worker_w_h_ship_report.md` | live smoke 7/7 post-flush |
| PR3 honest savings | `8676303` / `worker_w_pr3_honest_ui_report.md` | no “Economize R$” under 70% coverage |
| Official API only | `6affe85` | no slow web fallback on live path |

**Honest baseline (pre-G fix measure):**  
`.grok/status/match_eval_100_honest_report.md` — pass **71**/100, wrong_class **20**, missing_after_retry **9**, p50 **11.3 s**, p95 **23 s** (all `data_source=web` at that time). Offline G re-score emptied all 20 class traps; H smoke confirmed no egg poison on 7 queries. **Full serial re-eval post-G still due** (quota/429 blocked earlier).

---

## 2. Failure modes by user impact

### P0 — Trust breakers (wrong product feels like a lie)

| Mode | Evidence | User impact | Status |
|------|----------|-------------|--------|
| **Cross-class RAG rewrite poison** (label→ovos/sal/leite) | Honest 16/20 WC = eggs; H confirmed Redis poison keys; G fixed `rewrite_compatible` + label-primary egg reject | “Peito de frango” shows eggs | **Fixed in product** — re-eval still required |
| **Adjacent wrong product (same token family)** | H residual: `queijo` → **PAO DE QUEIJO**; phone plan: óleo coco / MAC OVOS (PR1 fixed those) | Cheese intent gets cheese-bread | **Open** (not egg-class; still wrong basket) |
| **Package-class miss among kept lines** | Offline residual: açúcar 30 kg industrial preferred when only cristal mass present; oil tiny packs historically | “Cheapest oil” is a sachet | **Mostly fixed for oil/egg**; sugar/household size residual |
| **Partial basket sold as full win** | Phone ~3/10: 4/10 + “Economize R$ 5,64” | Overconfident savings | **Fixed PR3 UI** |

### P1 — Empty / slow / unreliable (list unusable)

| Mode | Evidence | User impact | Status |
|------|----------|-------------|--------|
| **Upstream timeout → empty as “missing”** | `sefaz_item_deadline_seconds=55`; metrics `items_fetch_failed` after E ship; multi-item stampede history | Staples empty after ~55 s wait | **Partially fixed** (no empty cache; signal fetch_failed); latency still high under load |
| **True SEFAZ coverage gaps** | Honest 9 `missing_after_retry`: sal, bolacha, cerveja, achocolatado, detergente, amaciante, desinfetante, sabonete, shampoo | Hygiene/cleaning/snacks dead | **Open** (data, not scorer invent) |
| **Official API empty with no web fallback** | `factory.py` 6affe85: API-only; empty official → empty basket (web retired) | Cold/outage = total miss | **Regressed coverage path vs honest-eval era** — intentional speed tradeoff; needs prewarm + token health |
| **Weak / over-broad rewrite** | Live history: peito→frango→wrong category; pão→pao frances (benign) | Loses cut specificity or drifts class | Open for compound intents (peito, queijo mussarela, farinha de X) |
| **Cold cache / no prewarm in prod ops** | `prewarm_staples.py` exists; not guaranteed on deploy | First hit pays full SEFAZ latency | Open ops |

### P2 — Quality polish / measurement

| Mode | Evidence | User impact | Status |
|------|----------|-------------|--------|
| **No match_score on ItemOffer** | schema has `package_label` only; plan W1.5 / PR2 not shipped | Client cannot badge “incerto” | Open |
| **Eval not in CI as gate** | Manual `eval_shopping_list_100.py`; parallel eval once INVALID | Silent wrong_class regression | Open |
| **RAG similar-term over-match** | Stopword `de` historically linked everything; content_tokens min len 3 now | Residual weak similar rewrites | Mostly fixed; watch learn loop |
| **Industrial pack preferred** | Sugar 30 kg among cristal | Unrealistic household “best” | Package demote only partial |
| **DNS/docs residual** | live-verify NXDOMAIN (I) | Not matching | Out of scope here |

---

## 3. Prioritized backlog

Effort: **S** ≤1 day · **M** 2–4 days · **L** ≥1 week

### B1 — Compound / adjacent-class relevance (queijo ≠ pão de queijo) — **P0**

| | |
|--|--|
| **Problem** | Shared tokens pass score; H smoke top for `queijo` is `PAO DE QUEIJO`. Same pattern risk: peito vs frango whole bird, farinha de trigo vs farinha de mandioca if rewrite collapses. |
| **Approach** | Label-primary phrase gates in `_hard_reject_score`: if label is bare `queijo` (no “pão”), reject desc with early `pao`/`paes` + `queijo`. Symmetric: `pão de queijo` must keep bread+cheese product. Extend `_class_conflict` / rewrite safety so RAG cannot map `queijo`→`pao de queijo`. Goldens from H smoke + honest fixture ids 21–22, 68. |
| **Files** | `backend/app/services/rag/relevance.py`, `rag/store.py`, `backend/tests/test_relevance_quality.py` |
| **Acceptance** | `score_description("queijo",…,"PAO DE QUEIJO…") < 0.20` and keep true cheese lines; scoped live probe `queijo` top not pão; pytest green |
| **Effort** | **S** |

### B2 — Staple fetch reliability + latency budget — **P0/P1**

| | |
|--|--|
| **Problem** | User-visible long waits (~11 s p50 serial honest; multi-item can hit 55 s deadline → `items_fetch_failed` empties). Official API only: failure is hard empty. |
| **Approach** | (1) Deploy cron/prewarm: expand `prewarm_staples.py` STAPLES to full shopping_list_100 staples+dairy+oils; run post-deploy. (2) Parallel item fetch stays at concurrency 2–3 but **stagger** retries; never parallel eval against prod. (3) On deadline: surface `fetch_failed_labels` in UI (“falha de consulta, tente de novo”) vs true missing. (4) Health: alert when official API empty-rate spikes (token/host). Optional: controlled web fallback **only** when official empty *and* term in staple allowlist (feature flag) — product decision. |
| **Files** | `backend/scripts/prewarm_staples.py`, `search_service.py`, `config.py`, deploy/cron, Flutter results for fetch_failed copy |
| **Acceptance** | Warm staple basket 10 items p95 &lt; 45 s; `items_fetch_failed` for arroz/feijão/leite = 0 on warm prod probe; UI distinguishes upstream fail vs no_data |
| **Effort** | **M** |

### B3 — Rewrite safety for multi-token intents — **P1**

| | |
|--|--|
| **Problem** | Dropping modifiers (`peito de frango`→`frango`, `farinha de trigo`→`farinha`) loses intent; RAG “success” can reinforce. |
| **Approach** | Content-token retention rule: if user label has ≥2 content tokens (len≥3), effective rewrite must retain **all** content tokens OR a documented synonym group (not strict subset). Block subset rewrites unless score-proven in verifier after fetch. Prefer expand (add type) over drop (remove cut/species). |
| **Files** | `rag/store.rewrite_compatible`, `llm/requester.py`, `llm/verifier.py`, tests |
| **Acceptance** | No rewrite drops `peito`/`trigo`/`mussarela` from multi-token labels; RAG refuse + unit tests |
| **Effort** | **S–M** |

### B4 — Household package-class expansion — **P1**

| | |
|--|--|
| **Problem** | Oil/egg/sugar have priors; residual industrial sugar; rice “porção 250 ml” can rank; beans/milk size less enforced. |
| **Approach** | Extend `package_class_rank` for: arroz 1–5 kg preferred; leite 1 L UHT; açúcar demote &gt;10 kg hard; feijão 1 kg; reject restaurant “porção” when staple intent. Ranking already uses class-first. |
| **Files** | `rag/relevance.py`, `tests/test_relevance_quality.py`, `tests/test_ranking.py` |
| **Acceptance** | Goldens: 30 kg sugar demoted vs 1 kg; porção arroz score low for `arroz`; ranking crowns household pack when both present |
| **Effort** | **S** |

### B5 — Cold-start / coverage dictionary — **P1**

| | |
|--|--|
| **Problem** | 9 honest missing + hygiene/cleaning thin SEFAZ head. Empty better than invent, but shopper needs variants. |
| **Approach** | Curated **query variant table** (not full catalog): for known empties try fixed alts once in Verifier before give-up (`detergente`→`detergente ypê`/`lava louças`, `sal`→`sal refinado`, `sabonete`→`sabonete dove` generic brands from AL NFC-e). Seed via `prewarm_staples` + training 10k JSONL term frequencies (`backend/data/training-datasets/alagoas_search_10k.jsonl`). GTIN list for top 30 staples later (plan W5.4). |
| **Files** | `llm/verifier.py` or small `normalization/variants.py`, prewarm script, optional catalog |
| **Acceptance** | Reduce missing_after_retry on hygiene/cleaning fixture subset by ≥50% without raising wrong_class |
| **Effort** | **M** |

### B6 — Evaluation harness as regression gate — **P1**

| | |
|--|--|
| **Problem** | Quality is measured by ad-hoc workers; parallel stampede once invalid; no CI block on wrong_class. |
| **Approach** | (1) Offline scorer path already used (re-score stored top_lines) — promote to `pytest` goldens for every known WC theme. (2) Nightly/manual: serial CONCURRENCY=1 live eval → artifact. (3) Optional CI job: mock SEFAZ fixtures only (no live SEFAZ). Gate: wrong_class on fixture set = 0; live smoke 12 staples on deploy. |
| **Files** | `backend/scripts/eval_shopping_list_100.py`, `tests/test_relevance_quality.py`, `.github/workflows/*`, offline rescore helper |
| **Acceptance** | CI fails if egg/queijo-pão/oil-coco goldens regress; weekly honest serial report path documented |
| **Effort** | **M** |

### B7 — Progressive UX honesty (beyond PR3 savings) — **P1**

| | |
|--|--|
| **Problem** | Wait UI exists (`search_wait_copy.dart`); fetch_failed not clearly separated; no per-line confidence; partial stream may still feel “done” with wrong tops. |
| **Approach** | Show NFC-e description always under query (already often present); badge when rewrite ≠ label; missing panel + suggested_refinements chips; if `items_fetch_failed>0`, banner “consulta instável” not “produto não existe”. Optional PR2: `match_score` on ItemOffer for “incerto”. |
| **Files** | `frontend/lib/features/results/*`, `backend/app/schemas/search.py`, `ranking.py` populate score |
| **Acceptance** | Widget tests: fetch_failed banner; partial hero already PR3; no primary savings under 0.7 (regression) |
| **Effort** | **M** (score field S if isolated) |

### B8 — Learn-loop hygiene ops — **P2**

| | |
|--|--|
| **Problem** | Poison can re-accumulate if filters regress; H flushed 99 keys. |
| **Approach** | Periodic scan refuse incompatible ZSET members; admin metric “RAG refused learn count”; keep min_score_to_learn + package_class_ok. |
| **Files** | `rag/store.py`, training/daily_job or admin, tests |
| **Acceptance** | Injected poison never applied in lookup unit test; optional ops script |
| **Effort** | **S** |

### B9 — SEFAZ token / outage playbook — **P2**

| | |
|--|--|
| **Problem** | API-only path: token death = product death. |
| **Approach** | Health endpoint checks non-empty staple probe; secrets rotation already supported; document allowlist web fallback flag if token outage &gt; N min. |
| **Files** | deploy health, `factory.py`, docs |
| **Acceptance** | Alert path + runbook in ops; no silent empty for arroz when API down if flag on |
| **Effort** | **M** |

---

## 4. Quick wins (1–2 days) vs structural (weeks)

### Quick wins (ship this week)

1. **B1** queijo / pão de queijo (+ similar compound hard rejects) — pure `relevance.py` + tests.  
2. **B4** household package ranks for arroz/leite/açúcar industrial — same files.  
3. **B3 (minimal)** multi-token rewrite retention in `rewrite_compatible` — blocks peito→frango-class drift.  
4. **Scoped live smoke** (reuse H probe + queijo/açúcar/óleo/ovo) post-deploy; do **not** parallel-100.  
5. **Prewarm staples** on VPS once (`prewarm_staples.py --fetch`) + expand list.

### Structural (multi-week)

1. **B2** latency/SLA + optional controlled fallback + deploy prewarm automation.  
2. **B5** variant dictionary driven by 10k training frequencies.  
3. **B6** offline+CI gate + scheduled honest serial eval.  
4. **B7** match_score API + richer honesty UI.  
5. **B9** outage playbook / token monitoring.

---

## 5. Suggested next ship unit (after wait-UI)

**One PR-sized change — ship first:**

### PR title: `fix(match): reject pão-de-queijo (and kin) for bare cheese intent`

| Field | Value |
|-------|--------|
| **Why first** | Highest residual **wrong product** after egg poison (H soft residual); pure backend; tests offline; no SEFAZ invent; pairs with wait-UI without depending on it |
| **Scope** | `relevance._hard_reject_score` + optional `store._class_conflict`; goldens for queijo / pão de queijo / peito token retention if cheap |
| **Out of scope** | Full 100 live eval, matrix, catalog API, web scraper revive |
| **Tests** | `pytest tests/test_relevance_quality.py tests/test_rag_agents.py` + offline re-score if fixture tops available |
| **Live probe** | CONCURRENCY=1: `queijo`, `queijo mussarela`, `pão de queijo`, `peito de frango`, `óleo`, `ovo` — assert no adjacent-class top for first two; pão de queijo may keep cheese-bread |
| **Acceptance** | Probe tops class-correct; pytest green; commit + deploy |

**Immediate follow-on (same week if green):** B4 sugar/arroz pack ranks + expand prewarm; then B2 fetch_failed UI honesty.

---

## 6. Metrics to watch

| Metric | Target | Source |
|--------|--------|--------|
| wrong_class rate (serial honest 100) | ≤ 5% (→ 0 on known themes) | `eval_shopping_list_100.py` |
| missing_after_retry (true no_data) | trend down via variants; never invent | same |
| items_fetch_failed on warm staples | 0 | SearchMetrics / analytics |
| p95 multi-item 10 staples | &lt; 45 s | live smoke |
| Primary savings under coverage &lt; 0.7 | never | Flutter unit (PR3) |
| RAG refuse cross-class | &gt;0 logs OK; applied poison = 0 | Redis lookup tests |

---

## 7. Explicit non-goals (near-term)

- Full store inventory / catalog dump API (SEFAZ has no per-CNPJ dump).  
- Free multi-agent LLM loops on hot path.  
- Inventing products when SEFAZ has zero rows.  
- Full UI viewport matrix as matching gate.  
- Reviving website scraper as default (only consider allowlisted flag under API outage).

---

## 8. Evidence index

| Artifact | Role |
|----------|------|
| `.grok/status/match_eval_100_honest_report.md` | Baseline 71/20/9 |
| `.grok/status/match_eval_100_honest.json` | Per-query tops/verdicts |
| `.grok/status/worker_w_g_improve_report.md` | RAG poison root cause + fix |
| `.grok/status/worker_w_match_improve_report.md` | Relevance P0 gates |
| `.grok/status/worker_w_h_ship_report.md` | Post-deploy smoke 7/7 + residual queijo |
| `.grok/status/worker_w_fix_empty_cache_report.md` | Empty cache / fetch_failed |
| `docs/improvement-plan-search-quality.md` | Earlier phone-eval plan (W1–W5) |
| `docs/ai-architecture.md` | Requester/Verifier design |

---

*Update this file when a backlog item ships (SHA + residual wrong_class themes).*
