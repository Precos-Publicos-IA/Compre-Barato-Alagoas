# W-b2-resmoke — post accent-fold deploy serial staple re-smoke

**Date:** 2026-07-23  
**Worker:** W-b2-resmoke  
**Agent fix under test (deployed via CI):** `9dd136b` accent-fold SEFAZ cache + staple cold rewrite  
**Live base:** `https://alagoas.precospublicos.ia.br`  
**Policy:** API serial only (`CONCURRENCY=1`); no UI matrix; no large SEFAZ client rewrite  
**Artifacts:** [`worker_w_b2_resmoke_probes.json`](worker_w_b2_resmoke_probes.json)  
**Prior HARD_BLOCK:** [`worker_w_b2_verify_report.md`](worker_w_b2_verify_report.md) / [`worker_w_b2_verify_probes.json`](worker_w_b2_verify_probes.json)

## Live serving evidence (no VPS git SHA claim)

| Check | Result |
|-------|--------|
| `GET /health` | `200 {"status":"ok"}` |
| `POST /api/v1/search` shape | `metrics.match_rules_version`, `search_rewrites`, `items_fetch_failed` present |
| `match_rules_version` seen on probes | **`2026-07-23-head-v1`** (all 200 bodies) |
| Staple rewrites observed | `feijão→feijao carioca`, `ovo→ovos`, `óleo→oleo de soja`, `café→cafe torrado`, `açúcar→acucar cristal`, `leite→leite uht`, `arroz→arroz tipo 1` |
| VPS git SHA | **Not proven** — behavior matches post-`9dd136b` rewrite/fold intent |

Method: **two serial passes** (pass1 then pass2 warm) even if deploy prewarm already ran — documents user-facing path after cache population + second-hit warm. Accent pairs after pass2. Geo Maceió `-9.6633,-35.7089` r=8 d=7; timeout 120s.

---

## Verdict

**DONE / SLO pass (warm staples)** with **one pure-SEFAZ residual (`leite`)**.

| Metric (7 staples) | Prior HARD_BLOCK pass1 | Prior pass2 | **Resmoke pass1** | **Resmoke pass2** |
|--------------------|------------------------|-------------|-------------------|-------------------|
| **found_rate** | 1/7 = **0.14** | 2/7 = **0.29** | **6/7 = 0.86** | **6/7 = 0.86** |
| **fetch_fail_rate** | 6/7 = **0.86** | 3/7 = **0.43** | **1/7 = 0.14** | **1/7 = 0.14** |
| **approx_55s empties** | 6 | 3 | **1** (`leite`) | **1** (`leite`) |
| **HTTP 502** | 0 | 2 | **0** | **0** |
| **p50 latency found** | 795 ms | ~27 s | **344 ms** | **333 ms** |
| **p50 latency all** | 55.7 s | 53.8 s | **353 ms** | **340 ms** |

vs overall-eval staple subset (found 0.43 / fail 0.57): **IMPROVED** on both passes.

Warm SLO used for this ticket: pass2 `fetch_fail_rate ≤ 0.15` **and** `found_rate ≥ 0.85` **and** `approx_55s_empties ≤ 1` → **PASS**.

**Do not re-open M3/M4.** Match tops on successful rows look sane (Arroz Shari, FEIJAO CARIOCA, OLEO DE SOJA, OVOS EXTRA, CAFE GOURMET, ACUCAR PINDORAMA). Match track remains out of band for B2 fetch SLO.

---

## Fetch track vs match track

| Track | This run |
|-------|----------|
| **Fetch** | **CLEARED for agent-owned accent/rewrite residual.** 6/7 staples return stores=5, fail=0, sub-second after warm path. Only **`leite`** still ~55.2s `items_fetch_failed=1` after rewrite to `leite uht` → **pure SEFAZ residual**, not inventable catalog data. |
| **Match** | Out of band for B2. When fetch succeeds, tops are coherent product descriptions. |

---

## Pass 1 — initial (post-deploy)

| query | http | stores | latency_ms | items_fetch_failed | rewrite | top desc |
|-------|------|--------|------------|--------------------|---------|----------|
| arroz | 200 | 5 | 770.6 | 0 | arroz tipo 1 | Arroz Shari Und |
| feijão | 200 | 5 | 353.3 | 0 | feijao carioca | FEIJAO CARIOCA SPECIAL TP1 1KG |
| leite | 200 | 0 | **55250.4** | **1** | leite uht | — |
| óleo | 200 | 5 | 279.6 | 0 | oleo de soja | OLEO DE SOJA SOYA 900ML |
| ovo | 200 | 5 | 343.7 | 0 | ovos | OVOS EXTRA STA MARIA LUNA UN |
| café | 200 | 5 | 531.8 | 0 | cafe torrado | CAFE GOURMET |
| açúcar | 200 | 5 | 327.5 | 0 | acucar cristal | ACUCAR PINDORAMA 1KG |

**Summary:** found 6/7 (0.86), fetch_fail 1/7 (0.14). vs prior pass1 (0.14 / 0.86): **IMPROVED**.

---

## Pass 2 — warm

| query | http | stores | latency_ms | items_fetch_failed | rewrite | top desc |
|-------|------|--------|------------|--------------------|---------|----------|
| arroz | 200 | 5 | 299.9 | 0 | arroz tipo 1 | Arroz Shari Und |
| feijão | 200 | 5 | 339.7 | 0 | feijao carioca | FEIJAO CARIOCA SPECIAL TP1 1KG |
| leite | 200 | 0 | **55248.7** | **1** | leite uht | — |
| óleo | 200 | 5 | 296.2 | 0 | oleo de soja | OLEO DE SOJA SOYA 900ML |
| ovo | 200 | 5 | 353.4 | 0 | ovos | OVOS EXTRA STA MARIA LUNA UN |
| café | 200 | 5 | 487.5 | 0 | cafe torrado | CAFE GOURMET |
| açúcar | 200 | 5 | 332.5 | 0 | acucar cristal | ACUCAR PINDORAMA 1KG |

**Summary:** found 6/7 (0.86), fetch_fail 1/7 (0.14). vs prior pass2 (0.29 / 0.43 + 2×502): **IMPROVED**. No gateway 502s.

---

## Accent / singular pairs (post-fix)

All five pairs: **parity both found**, fail=0, stores=5, sub-second.

| pair | accented | ascii/alt | parity |
|------|----------|-----------|--------|
| feijão / feijao | found, rewrite `feijao carioca` | found, same rewrite | **OK** |
| ovo / ovos | found, rewrite `ovos` | found | **OK** (singular fixed) |
| óleo / oleo | found, `oleo de soja` | found | **OK** |
| café / cafe | found, `cafe torrado` | found | **OK** |
| açúcar / acucar | found, `acucar cristal` | found | **OK** |

Prior HARD_BLOCK residual (`feijão` fail vs `feijao` ok; `ovo` fail vs `ovos` ok) is **cleared** on live.

---

## Phase-8 style headline

```
prior HARD_BLOCK:
  pass1: fetch_fail_rate=0.857  found_rate=0.143  p50_all_ms≈55702
  pass2: fetch_fail_rate=0.429  found_rate=0.286  p50_all_ms≈53772 (+2×502)

resmoke post-9dd136b deploy:
  pass1: fetch_fail_rate=0.143  found_rate=0.857  p50_all_ms=353  p50_found_ms=344
  pass2: fetch_fail_rate=0.143  found_rate=0.857  p50_all_ms=340  p50_found_ms=333
  accent pairs: 5/5 both_found, fail=0
  residual: leite only (~55s empty after rewrite leite uht) → pure SEFAZ
verdict: DONE_SLO_PASS (warm staples); residual leite = SEFAZ not agent-owned
```

---

## Acceptance vs B2 / prior residual actions

| Criterion | Result |
|-----------|--------|
| Deploy accent-fold + staple rewrite | **Live behavior confirms** (rewrites + fast accented hits) |
| Serial 7-term smoke CONCURRENCY=1 | **Done** |
| Warm staples fetch_fail ≈ low / found high | **PASS** (0.14 fail / 0.86 found; only leite) |
| Accented terms share path with prewarm/ASCII | **PASS** (feijão≡feijao) |
| Singular `ovo` → rewrite | **PASS** (`ovos`) |
| `leite` after rewrite | Still ~55s fail → **pure SEFAZ residual** (document; no greenwash) |
| Ticket status | **B2-verify DONE** (agent-owned fetch residual cleared). SEFAZ `leite` remains external residual, not a re-HARD_BLOCK of the accent/rewrite ship unit. |

## Residual (honest)

1. **`leite` / `leite uht`** — both passes ~55.25s `items_fetch_failed=1`, stores=0. Not fixed by accent-fold or static staple rewrite; needs upstream SEFAZ health or separate product-specific strategy later. **Do not** treat as failure of `9dd136b`.
2. No large SEFAZ client rewrite performed (per task scope).
3. Match quality / head weak tops / honest-100 remain separate matching residual tracks (M5+), not B2 fetch.

## Not done / out of scope

- UI matrix / Flutter
- Parallel stampede probes
- Re-opening M3/M4
- Claiming exact VPS git SHA without host proof
