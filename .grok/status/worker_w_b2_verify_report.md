# W-b2-verify — staple warm/fetch smoke (post B2 prewarm)

**Date:** 2026-07-23  
**Worker:** W-b2-verify  
**Ship under test (live at probe time):** `9ec6775` prewarm + fetch_failed honesty  
**Agent fix SHA (not live at probe time):** `9dd136b` accent-fold + staple cold rewrite  
**Live base:** `https://alagoas.precospublicos.ia.br`  
**Policy:** API serial only (`CONCURRENCY=1`); no UI matrix; M4 scripts out of scope  

## Method

| Parameter | Value |
|-----------|--------|
| API base | `https://alagoas.precospublicos.ia.br` |
| Endpoint | `POST /api/v1/search` |
| Concurrency | **1** (serial; no parallel stampede) |
| Geo | Maceió: lat=**-9.6633**, lon=**-35.7089**, `radius_km=8`, `days=7` |
| Timeout | 120s per request |
| Terms (user-facing accents) | arroz, feijão, leite, óleo, ovo, café, açúcar |
| Passes | **pass1** initial cold-ish; **pass2** same list after short delay (“warm”) |
| Accent diagnostic | Pair accented vs ASCII / singular vs prewarm spelling (separate artifact) |
| Artifacts | [`worker_w_b2_verify_probes.json`](worker_w_b2_verify_probes.json), [`worker_w_b2_verify_accent_cmp.json`](worker_w_b2_verify_accent_cmp.json) |

No full UI matrix. Prefer not re-running the 55s×N suite; evidence below is complete for the ticket.

---

## Verdict

**HARD_BLOCK** — live staple **fetch** reliability did **not** meet warm SLO; **REGRESSED** vs overall-eval staple subset. Do **not** treat as DONE/SLO green.

Prewarm **wiring is confirmed and present**, but live accented staple probes still hit the classic **~55s `items_fetch_failed`** wall for most terms on both passes. Warm pass fetch_fail remains high (3/7 + 2× HTTP 502 empties). Not inventable catalog data; needs healthy SEFAZ + deploy of accent/static-rewrite fix then re-probe.

| Metric (7 staples) | Baseline overall-eval subset | Pass1 initial | Pass2 “warm” |
|--------------------|------------------------------|---------------|--------------|
| **found_rate** | **3/7 = 0.43** (arroz, leite, ovo) | **1/7 = 0.14** | **2/7 = 0.29** |
| **fetch_fail_rate** | **4/7 = 0.57** | **6/7 = 0.86** | **3/7 = 0.43** (+2× HTTP 502) |
| **approx_55s empties** | 4 | 6 | 3 |
| **p50 latency among found** | (subset mixed) | **795 ms** (arroz only) | **~27.3 s** (arroz warm + açúcar cold-ish) |
| **p50 latency all** | ~36.6 s (19 probes) | **55.7 s** | **53.8 s** |

**JSON artifact:** [`.grok/status/worker_w_b2_verify_probes.json`](worker_w_b2_verify_probes.json)  
**Accent cmp:** [`.grok/status/worker_w_b2_verify_accent_cmp.json`](worker_w_b2_verify_accent_cmp.json)  
**Baseline pointer:** `.grok/status/eval_overall_live_probes.json` → staple_found_rate 0.4286, staple_fetch_fail_rate 0.5714

---

## Fetch track vs match track (keep separate)

| Track | What it measures | This run |
|-------|------------------|----------|
| **Fetch** | Did SEFAZ/web return rows before `sefaz_item_deadline_seconds≈55`? Fields: `items_fetch_failed`, `fetch_failed_labels`, stores=0 + ~55s, intermittent **502** | **HARD_BLOCK** — pass1 fail 0.86, pass2 fail 0.43 + gateway 502s; warm path incomplete for accented/singular labels |
| **Match** | Given rows, is top description the right product? Fields: `match_rate`, top_description quality | **Out of band for B2-verify SLO** — when fetch succeeds, tops look sane (e.g. Arroz Shari, ACUCAR PINDORAMA, FEIJAO CARIOCA, OLEO DE SOJA, OVOS EXTRA, CAFE GOURMET). Matching MVP is M0–M4; do not greenwash fetch by citing good tops on the minority that returned |

Green tops on `arroz` / successful accent-cmp hits do **not** clear the fetch hard-block.

---

## 1. Prewarm wiring (confirmed)

| Piece | Status |
|-------|--------|
| `deploy/prewarm-staples.sh` | Present; curl POST `/api/v1/search`; batch=1; Maceió coords; unaccented terms include arroz/feijao/leite/… |
| `deploy/remote-update.sh` | After health: runs prewarm when `PREWARM_STAPLES` default **1**; `PREWARM_STAPLES=0` skips; non-fatal unless `PREWARM_STRICT=1` |
| `deploy/README.md` | Documents prewarm |
| Ship SHA | `9ec6775` *fix(search): staple prewarm on deploy + fetch_failed UI honesty* |
| Live `/health` | `200 {"status":"ok"}` (probe window) |

Wiring is **not** the hard block. **Effectiveness** of warm path on live accented user terms **is**.

---

## 2. Live probes (serial CONCURRENCY=1)

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

**Summary pass1:** found 1/7 (0.14), fetch_fail 6/7 (0.86), six ~55s empties, p50_all ≈ 55702 ms. Verdict vs baseline: **REGRESSED**.

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

**Summary pass2:** found 2/7 (0.29), fetch_fail 3/7 (0.43), three ~55s empties + 2× 502 empties, p50_all ≈ 53772 ms. Still **REGRESSED** vs baseline found_rate; warm fetch_fail **still high** — prewarm **insufficient** for accented terms on live.

### Accent / prewarm-term comparison (actionable residual)

Source: [`worker_w_b2_verify_accent_cmp.json`](worker_w_b2_verify_accent_cmp.json) (ts 2026-07-23T19:49:46Z).

| query | http | ms | stores | fail | top |
|-------|------|-----|--------|------|-----|
| **feijão** | 200 | 55712 | 0 | 1 | — |
| **feijao** | 200 | 53986 | **5** | 0 | FEIJAO CARIOCA SPECIAL TP1 1KG |
| óleo | 200 | 735 | 5 | 0 | OLEO DE SOJA SOYA 900ML |
| oleo | 200 | 736 | 5 | 0 | OLEO DE SOJA SOYA 900ML |
| **ovo** | 200 | 55699 | 0 | 1 | — |
| **ovos** | 200 | 53491 | **5** | 0 | OVOS EXTRA STA MARIA LUNA UN |
| café / cafe | 200 | ~850 | 5 | 0 | CAFE GOURMET |
| açúcar / acucar | 200 | ~800 | 5 | 0 | ACUCAR PINDORAMA 1KG |
| leite | 200 | 55699 | 0 | 1 | — |

**Actionable residual (agent-owned, before pure SEFAZ blame):**

1. **ASCII fold before SEFAZ cache key** — prewarm `feijao` did not share slot with user `feijão` under live ship `9ec6775` (`term.lower()` only).  
2. **Static staple rewrite without Redis RAG** — prewarm list warms **`ovos`**, not **`ovo`**; cold path needed `ovo→ovos` / `feijão→feijao carioca` without organic RAG.  
3. Shell prewarm does not seed Redis RAG; rewrite must not depend on RAG seed for staples.

`óleo`/`oleo` both OK in accent sample (cache/traffic already warm) — accent is **not** the only failure mode; **SEFAZ ~55s** and **singular labels** remain.

---

## 3. vs overall-eval baseline

Source: `.grok/status/eval_overall_live_probes.json` (same day, serial).

Baseline staple tags: arroz good; **feijão/óleo/café/açúcar empty_fetch_failed ~55s**; leite weak_top; ovo good_top → **found 3/7, fetch_fail 4/7**.

This verify pass1: **found 1/7, fetch_fail 6/7** → **REGRESSED**. Pass2 partial recovery for açúcar only; **502** on feijão/leite shows edge instability under serial load.

Prewarm did **not** deliver warm-staple `items_fetch_failed=0` for the user-facing accented list.

---

## 4. Phase-8 style metrics (headline)

```
pass1: fetch_fail_rate=0.857  found_rate=0.143  p50_found_ms=795  p50_all_ms=55702
pass2: fetch_fail_rate=0.429  found_rate=0.286  p50_found_ms≈27279  p50_all_ms=53772
       (502s excluded from fetch_fail_n but still empty for user)
baseline staple subset: fetch_fail_rate=0.571  found_rate=0.429
verdict: HARD_BLOCK
```

---

## 5. What is **not** fixed (live at probe time)

| Item | Evidence |
|------|----------|
| Warm staple fetch_fail ≈ 0 | Pass2 still 3/7 fail + 2× 502; óleo/ovo/café ~55s empties |
| Accented user terms share prewarm cache | `feijão` fail vs `feijao` success (pre-`9dd136b` live) |
| Singular vs prewarm plural | `ovo` fail vs `ovos` success |
| SEFAZ deadline reliability | `leite` still ~55s fail even ASCII; intermittent 502 under serial staple load |
| Full Redis RAG seed on VPS | Shell prewarm is API-only; not a substitute for rewrite/cache fold |

---

## 6. Agent-owned fix (shipped code; needs deploy + re-probe)

Committed as **`9dd136b`** `fix(search): accent-fold SEFAZ cache + staple cold rewrite (B2-verify)` — **not** a large SEFAZ reliability project; narrow and tested:

| Change | Why |
|--------|-----|
| `search_service._fold_cache_term` / `_cache_key` accent-fold | prewarm `feijao` ≡ user `feijão` |
| `staples.staple_effective_term` | static best rewrite from `STAPLE_RAG_MAPPINGS` |
| `BasicRequester` staple fallback when RAG empty | `ovo→ovos`, `feijão→feijao carioca`, oils/coffee/sugar without Redis seed |

**Tests:** `pytest tests/test_prewarm_staples.py tests/test_empty_cache.py tests/test_rag_agents.py tests/test_llm_mock.py -q` → **pass** (37) at fix time.

**Still hard-block after code alone:** SEFAZ deadline empties for `leite` and intermittent cold ~55s / **502** — cannot invent prices; needs upstream health + **post-deploy** re-verify of the 7-staple serial smoke.

M4 measure scripts are **out of scope** for this worker (owned by W-m4-measure).

---

## 7. Acceptance vs B2 / Phase 8

| Criterion | Result |
|-----------|--------|
| Prewarm script + remote-update / `PREWARM_STAPLES` | **OK** (wiring confirmed) |
| Post-deploy warm staples fetch_fail≈0 | **FAIL live** → **HARD_BLOCK** |
| No stampede (serial probes) | **OK** (still deadline fails) |
| Honesty `items_fetch_failed` on empty | **OK** (present) |
| Ticket status | **HARD_BLOCKED** with evidence (not SLO DONE) |

## Residual actions (honest must-follow)

1. **Deploy** `9dd136b` (or tip containing accent fold + `staple_effective_term`) to production.  
2. Run full `deploy/prewarm-staples.sh` after stack health (`PREWARM_STAPLES=1`).  
3. Re-run serial 7-term smoke (CONCURRENCY=1, Maceió geo); expect ovo/feijão/óleo/café/açúcar to share warm path when SEFAZ returns once.  
4. If `leite` still ~55s fail after rewrite to `leite uht` → pure **SEFAZ hard-block** (document, no greenwash).  
5. Triage intermittent live **502** under serial staple load (gateway/upstream).
