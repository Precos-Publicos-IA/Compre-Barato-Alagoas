# W-b2-verify — staple fetch reliability (post B2 prewarm)

**Date:** 2026-07-23  
**Worker:** W-b2-verify  
**Ship under test:** `9ec6775` prewarm + fetch_failed honesty  
**Live base:** `https://alagoas.precospublicos.ia.br`  
**Policy:** API serial only (CONCURRENCY=1); no UI matrix  

## Verdict

**HARD_BLOCK (SEFAZ / upstream) — live staple reliability REGRESSED vs overall-eval baseline**

Prewarm **wiring is correct and present**, but live accented staple probes still hit the classic **~55s `items_fetch_failed`** wall for most terms. Not inventable data; needs healthy SEFAZ + (after this worker) deploy of accent/static-rewrite fix.

| Metric (7 staples) | Baseline overall-eval subset | Pass1 initial | Pass2 “warm” |
|--------------------|------------------------------|---------------|--------------|
| **found_rate** | **3/7 = 0.43** (arroz, leite, ovo) | **1/7 = 0.14** | **2/7 = 0.29** |
| **fetch_fail_rate** | **4/7 = 0.57** | **6/7 = 0.86** | **3/7 = 0.43** (+2× HTTP 502) |
| **approx_55s empties** | 4 | 6 | 3 |
| **p50 latency among found** | (subset mixed) | **795 ms** (arroz only) | **~27.3 s** (arroz warm + açúcar cold-ish) |
| **p50 latency all** | ~36.6 s (19 probes) | **55.7 s** | **53.8 s** |

**JSON artifact:** [`.grok/status/worker_w_b2_verify_probes.json`](worker_w_b2_verify_probes.json)

---

## 1. Prewarm wiring (confirmed)

| Piece | Status |
|-------|--------|
| `deploy/prewarm-staples.sh` | Present, executable; curl POST `/api/v1/search`; batch=1; Maceió coords; terms include arroz/feijao/leite/… |
| `deploy/remote-update.sh` | After health: runs prewarm when `PREWARM_STAPLES` default **1**; `PREWARM_STAPLES=0` skips; non-fatal unless `PREWARM_STRICT=1` |
| `deploy/README.md` | Documents prewarm |
| Ship SHA | `9ec6775` *fix(search): staple prewarm on deploy + fetch_failed UI honesty* |
| Live `/health` | `200 {"status":"ok"}` |

Wiring is **not** the hard block. Effectiveness on live is.

---

## 2. Live probes (serial CONCURRENCY=1)

**Geo:** lat=-9.6633 lon=-35.7089 radius_km=8 days=7 (prewarm default)  
**Terms:** arroz, feijão, leite, óleo, ovo, café, açúcar  
**Timeout:** 120s  

### Pass 1 — initial

| query | http | stores | latency_ms | items_fetch_failed | top desc |
|-------|------|--------|------------|--------------------|----------|
| arroz | 200 | 5 | 795.1 | 0 | Arroz Shari Und |
| feijão | 200 | 0 | 55689.6 | 1 | — |
| leite | 200 | 0 | 55706.3 | 1 | — |
| óleo | 200 | 0 | 55698.8 | 1 | — |
| ovo | 200 | 0 | 55710.4 | 1 | — |
| café | 200 | 0 | 55702.1 | 1 | — |
| açúcar | 200 | 0 | 55705.8 | 1 | — |

### Pass 2 — after short delay (“warm”)

| query | http | stores | latency_ms | items_fetch_failed | top desc |
|-------|------|--------|------------|--------------------|----------|
| arroz | 200 | 5 | 787.2 | 0 | Arroz Shari Und |
| feijão | **502** | 0 | 679.1 | 0 | — (gateway) |
| leite | **502** | 0 | 675.6 | 0 | — (gateway) |
| óleo | 200 | 0 | 55720.6 | 1 | — |
| ovo | 200 | 0 | 55706.8 | 1 | — |
| café | 200 | 0 | 55707.9 | 1 | — |
| açúcar | 200 | 5 | 53771.5 | 0 | ACUCAR PINDORAMA 1KG |

### Accent / prewarm-term comparison (diagnostic)

| query | result |
|-------|--------|
| feijão | empty fetch_fail ~55s |
| **feijao** (prewarm spelling) | stores=5 (still ~54s cold once) |
| óleo / oleo | both warm hit after prior traffic |
| **ovo** | empty fetch_fail ~55s |
| **ovos** (prewarm list) | stores=5 |
| café / cafe | warm hits |
| açúcar / acucar | warm hits |
| leite | still ~55s fail |

**Agent-owned gap (not only SEFAZ):**

1. Cache key used `term.lower()` **without accent fold** → prewarm `feijao` did not share slot with user `feijão`.  
2. Prewarm list warms **`ovos`**, not **`ovo`**; without Redis RAG seed, requester did not apply static `ovo→ovos`.  
3. Shell prewarm does not seed Redis RAG; cold rewrite depended on organic RAG.

---

## 3. vs overall-eval baseline

Source: `.grok/status/eval_overall_live_probes.json` (same day, serial, tip around `bc5964f`, B2 already listed).

Baseline staple tags: arroz good; **feijão/óleo/café/açúcar empty_fetch_failed ~55s**; leite weak_top; ovo good_top → **found 3/7, fetch_fail 4/7**.

This verify pass1: **found 1/7, fetch_fail 6/7** → **REGRESSED** coverage under same product surface. Pass2 partial recovery for açúcar only; **502** on feijão/leite shows edge instability under serial load.

Prewarm did **not** deliver warm-staple `items_fetch_failed=0` for the user-facing accented list.

---

## 4. Phase-8 style metrics (headline)

```
pass1: fetch_fail_rate=0.857  found_rate=0.143  p50_found_ms=795
pass2: fetch_fail_rate=0.429  found_rate=0.286  p50_found_ms≈27279  (502s excluded from fetch_fail)
baseline staple subset: fetch_fail_rate=0.571  found_rate=0.429
verdict: HARD_BLOCK
```

---

## 5. Agent-owned fix (this worker) — code + tests

Shipped in same worker (pytest green):

| Change | Why |
|--------|-----|
| `search_service._fold_cache_term` / `_cache_key` accent-fold | prewarm `feijao` ≡ user `feijão` |
| `staples.staple_effective_term` | static best rewrite from `STAPLE_RAG_MAPPINGS` |
| `BasicRequester` staple fallback when RAG empty | `ovo→ovos`, `feijão→feijao carioca`, oils/coffee/sugar without Redis seed |

**Tests:** `pytest tests/test_prewarm_staples.py tests/test_empty_cache.py tests/test_rag_agents.py tests/test_llm_mock.py -q` → **pass**

**Not fixed by code alone (true hard-block):** SEFAZ deadline empties for `leite` and intermittent cold ~55s / **502** — cannot invent prices; needs upstream health + post-deploy re-verify.

---

## 6. Acceptance vs B2 / Phase 8

| Criterion | Result |
|-----------|--------|
| Prewarm script + remote-update / `PREWARM_STAPLES` | **OK** |
| Post-deploy warm staples fetch_fail≈0 | **FAIL live** |
| No stampede (serial probes) | **OK** (still deadline fails) |
| Honesty `items_fetch_failed` on empty | **OK** (present) |

## Next

1. Deploy agent fix (accent cache + staple static rewrite).  
2. Ensure one full `prewarm-staples.sh` run on VPS after stack health.  
3. Re-run this serial 7-term probe; expect ovo/feijão/óleo/café/açúcar to share warm path when SEFAZ returns once.  
4. If `leite` still ~55s fail with rewrite to `leite uht` — leave as **SEFAZ hard-block** with probe evidence.
