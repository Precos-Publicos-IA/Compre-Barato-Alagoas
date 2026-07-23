# W-eval-overall — fresh production scorecard

| Field | Value |
|-------|--------|
| **Worker** | W-eval-overall |
| **When (UTC)** | 2026-07-23T18:48Z → 19:17Z |
| **Live app** | https://alagoas.precospublicos.ia.br |
| **Tip of main** | `bc5964f` (docs status after B2) |
| **Product SHAs in tree** | head+wait `12b2c97` · desugar `3112eb7` · staple B2 `9ec6775` |
| **Probe artifact** | [`.grok/status/eval_overall_live_probes.json`](eval_overall_live_probes.json) |
| **Method** | Live prod only · CONCURRENCY=1 · timeout 110s · Maceió lat/lon · days=3, thin→retry days=7 |
| **429** | none (full set completed) |

## Bottom line

**Overall grade: C+ (conditional pilot, not daily-driver ready)**

**Ready for real Maceió shopping lists?** **Not yet as a reliable daily tool.**  
When SEFAZ returns rows, **match class quality is clearly better than the 2026-07-18 honest-100** (egg-bleed and several cross-class tops are gone). But **staple coverage is still flaky**: 5/18 single-item probes empty after retry (feijão, óleo, café, açúcar via `items_fetch_failed` ~55s; detergente true empty). p50 latency **~37s** and p95 **~56s** make the product feel broken on cold paths even when metrics are honest.

Use for **demo / pilot with caveats** (wait UI + fetch_failed honesty help). Do **not** market as dependable full-list shopping until staple fetch p95 and empty rate improve.

---

## 1) Infrastructure

| Check | Result | Notes |
|-------|--------|-------|
| `GET /health` | **200** `{"status":"ok"}` | ~0.69s |
| App shell `/` | **200** Flutter web HTML | ~0.69s |
| `GET /api/v1/suggestions?q=arroz` | **200** catalog labels | arroz, feijão, leite… |
| Docs | **200** | Host: `docs.alagoas.precospublicos.ia.br` |
| Admin | **200** | Host: `admin.alagoas.precospublicos.ia.br` |
| Bare `docs.precospublicos.ia.br` / `admin.precospublicos.ia.br` | **NXDOMAIN** | Wrong hostnames; alagoas-prefixed are correct |

Mid-deploy blip: earlier same session saw **HTTP 502** on `/api/v1/search` while CI was rolling; after green deploy, searches returned 200 consistently.

**Infra grade: A−** (solid; only DNS naming footgun on bare hosts)

---

## 2) Search reliability (live probes)

**Geo:** lat=-9.6658 lon=-35.735 radius_km=10 · **n=19** (18 singles + multi basket)

| query | http | stores | match_rate | data_source | latency_ms | items_fetch_failed | top description (trunc) | notes |
|-------|-----:|-------:|-----------:|-------------|----------:|-------------------:|-------------------------|-------|
| arroz | 200 | 5 | 1.0 | web | 55814 | 0 | Arroz Shari Und | good; cold ~56s |
| feijão | 200 | 0 | 0.0 | web | 55693 | 1 | — | days7 retry still empty; **~55s fail** |
| leite | 200 | 5 | 1.0 | web | 54681 | 0 | COCADA LEITE | **weak** confection, not UHT milk |
| óleo | 200 | 0 | 0.0 | web | 55694 | 1 | — | **~55s fail** |
| ovo | 200 | 5 | 1.0 | web | 785 | 0 | OVOS EXTRA STA MARIA LUNA UN | good; **warm cache** |
| banana | 200 | 5 | 1.0 | web | 711 | 0 | BANANA PROMOCAO | good; warm |
| peito de frango | 200 | 5 | 1.0 | web | 36595 | 0 | SOPA VONO PEITO FRANGO C QUEIJO 17G | **weak** soup; not ovos/pastel |
| farinha de trigo | 200 | 5 | 1.0 | web | 36334 | 0 | FARINHA TRIGO TIA MARA C FERM 1kg | good (**was egg-bleed**) |
| pão | 200 | 5 | 1.0 | web | 54177 | 0 | PAO SORTIDO | good-ish; days7 recovered |
| queijo | 200 | 5 | 1.0 | web | 724 | 0 | SALG POPCROC QUEIJO 15G | **weak** snack, not dairy cheese |
| papel higiênico | 200 | 5 | 1.0 | web | 36212 | 0 | PAPEL HIGIENICO PIMPO LAVANDA | good (**was toalha**) |
| salsicha | 200 | 5 | 1.0 | web | 18846 | 0 | SALSICHA PERDIGÃO | good (**was pipoca**) |
| sabão em pó | 200 | 5 | 1.0 | web | 38182 | 0 | SABAO EM PO SONHO | good (**was cocada**) |
| sal | 200 | 1 | 1.0 | web | 19757 | 0 | SAL KG GRANEL - KG | good; thin coverage |
| detergente | 200 | 0 | 0.0 | web | 19820 | 0 | — | true **no_data** (failed=0) |
| café | 200 | 0 | 0.0 | web | 55698 | 1 | — | **~55s fail** |
| açúcar | 200 | 0 | 0.0 | web | 55703 | 1 | — | **~55s fail** |
| alho | 200 | 5 | 1.0 | web | 16783 | 0 | MOLHO EXTRA ALHO | **weak** sauce; deeper list has ALHO |
| arroz+feijão+leite | 200 | 5 | 1.0 | web | 53914 | 0 | ARROZ MARIANO P.T.1 | multi: arroz+feijão ok; leite→coco/pó |

### Coverage snapshot

| Metric | Value |
|--------|------:|
| HTTP 200 | 19/19 |
| stores>0 | 14/19 (73.7%) |
| match_rate>0 | 14/19 |
| any `items_fetch_failed` | 4 singles (feijão, óleo, café, açúcar) |
| ~55s empties | 4 |
| true empty (failed=0) | 1 (detergente) |
| 429 | 0 |

**Notable flake:** solo **feijão** failed (`items_fetch_failed=1`), but multi basket returned **FEIJAO PRETO / CARIOCA** — SEFAZ/deadline race, not permanent catalog absence.

**Search coverage grade: C**

---

## 3) Match quality (soft-assert head alignment)

| Soft-assert | Result | Live top | Comment |
|-------------|--------|----------|---------|
| queijo ≠ pão de queijo | **PASS** | SALG POPCROC QUEIJO 15G | Not pão de queijo; still **wrong class** (snack) |
| peito ≠ pastel / ovos | **PASS** | SOPA VONO PEITO FRANGO… | Egg/pastel bleed gone; **weak** prepared soup |
| papel ≠ toalha (when data) | **PASS** | PAPEL HIGIENICO PIMPO… | Hard win vs honest-100 |

### Quality tags (this probe set)

| Tag | Queries |
|-----|---------|
| **good_top** | arroz, ovo, banana, farinha de trigo, pão, papel higiênico, salsicha, sabão em pó, sal |
| **weak_top** | leite (cocada), peito (sopa), queijo (salgadinho), alho (molho) |
| **empty** | feijão, óleo, detergente, café, açúcar |

Deeper tops sometimes better than rank-1 (e.g. peito also has `PEITO DE FRANGO DEF`; alho has bare `ALHO`) — ranking/filter still under-weights primary grocery sense vs prepared/snack.

**Match quality grade: B−** (systemic egg-bleed fixed; residual weak heads remain)

---

## 4) Latency

| Stat | ms |
|------|---:|
| min | 711 |
| p50 | **36595** |
| mean | 35059 |
| p95 | **55715** |
| max | 55814 |

- Warm hits (ovo, banana, queijo): **<1s** — proves cache path works.
- Cold / deadline path: **~36–56s**, with classic **~55s** empty failures = `sefaz_item_deadline_seconds` wall.
- Multi basket ~54s with stores — usable but slow.

Compare honest-100 (2026-07-18): p50 **11.3s** / p95 **23s** — this session's cold set is **worse on latency** (post-deploy cold cache + more deadline hits), not a regression of the wait UX itself.

**Latency grade: D+**

---

## 5) UX honesty

| Capability | Evidence |
|------------|----------|
| Wait UX + ETA/notify | Shipped `12b2c97`; unit tests for wait copy/UI; not re-browsered this run |
| `items_fetch_failed` / `fetch_failed_labels` | **Present on live API** (e.g. feijão failed=1) — B2 `9ec6775` |
| Client parse + banner | Code/tests in tree (`models_test.dart`, results UI) — API-side honesty confirmed live |
| Empty vs fail distinction | detergente failed=0 vs feijão failed=1 — metrics support honest empty-state copy |

**UX honesty grade: B+** (shipped; live metrics support it; full Flutter web visual not re-probed here)

---

## 6) CI / deploy posture

| Run | SHA | Result |
|-----|-----|--------|
| workflow_dispatch CI/CD | `3112eb7` | **success** — changes, e2e-local, test, **deploy**, **live-verify** all green |
| push staple B2 | `9ec6775` | cancelled (superseded) |
| push docs status | `bc5964f` | **success** (tip) |

- Residual live-verify flake from earlier K3 window: **not reproduced** on the green `3112eb7` live-verify job.
- Mid-eval deploy churn caused brief **502**s — expected during roll; health recovered.

**Ship readiness grade: B**

---

## 7) Scorecard

| Dimension | Grade | One-liner |
|-----------|:-----:|-----------|
| **Uptime / infra** | **A−** | Health, shell, sugg, docs/admin (alagoas hosts) green |
| **Search coverage** | **C** | 14/19 stores>0; critical staples still 55s-fail |
| **Match quality** | **B−** | Head gate killed egg-bleed; weak snack/soup/sauce tops remain |
| **Latency** | **D+** | p50 ~37s / p95 ~56s; warm path fine |
| **Ship readiness** | **B** | Green deploy+live-verify; B2 prewarm not yet proving warm staples |
| **Overall** | **C+** | Improved quality spine; not yet reliable full shopping lists |

---

## 8) What improved since 2026-07-18 honest eval

| Area | 2026-07-18 honest-100 | This eval (2026-07-23) |
|------|----------------------|-------------------------|
| Dominant wrong tops | **OVOS BRANCOS** bleed on many non-egg queries | **Not observed** on peito/farinha/pão/queijo in this set |
| farinha de trigo | wrong_class → eggs | **FARINHA TRIGO** good |
| papel higiênico | PAPEL TOALHA | **PAPEL HIGIENICO** |
| sabão em pó | COCADA LEITE | **SABAO EM PO SONHO** |
| salsicha | Pipoca | **SALSICHA PERDIGÃO** |
| Head-aligned matching | not shipped | **Shipped** `12b2c97` + offline SHIP_OK |
| Wait UX | none | **Shipped** ETA/notify |
| Fetch-fail honesty | opaque empty | **`items_fetch_failed` live** + UI plumbing |
| Staple prewarm hook | scripts only | **Deploy prewarm path** `9ec6775` (effectiveness still uneven) |
| Coverage reliability | 91/100 found (serial) | 14/19 on this staple set — **still fragile** on cold SEFAZ |
| Latency | p50 11s | p50 37s on this cold-heavy set |

---

## 9) Top 5 next reliability fixes (structural; no product-pair denylists)

1. **Make staple prewarm actually hot on VPS** — verify post-deploy prewarm logs; measure warm hit-rate for feijão/óleo/açúcar/café; fix silent prewarm skip / SEFAZ stampede during warm; optional Redis RAG seed for staples.
2. **Deadline / partial-return strategy** — avoid all-or-nothing 55s empties: stream/partial stores earlier; shorter fail-soft with retry queue; never present "no products" when failure was deadline.
3. **Primary-sense ranking after head filter** — prefer bare grocery commodity (LEITE UHT, PEITO DE FRANGO KG, QUEIJO MUSSARELA, ALHO KG) over snack/soup/sauce that merely share head tokens; structural score features, not denylist pairs.
4. **Cache + rewrite discipline for multi vs solo** — feijão multi-hit vs solo-fail shows non-determinism; stabilize search_term + cache key + per-item budget so solo staples match multi success rates.
5. **Hygiene/cleaning recall path** — detergente true empty; café/açúcar fetch-fail — catalog rewrite + SEFAZ query variants + longer window only when failed≠0, without masking true no_data.

---

## Method notes / caveats

- Did **not** re-run full 100-item eval (quota/time; overall ≠ full 100).
- CONCURRENCY=1 to protect SEFAZ.
- One mid-session deploy window produced 502s — excluded from final table (final set is post-green).
- Hostnames: use `*.alagoas.precospublicos.ia.br` for docs/admin.

## Deliverables

1. This report: `.grok/status/worker_w_eval_overall_report.md`
2. Raw JSON: `.grok/status/eval_overall_live_probes.json`
3. Session note updated in `.grok/status/session.md`

## Verdict sentence

**Compre Barato Alagoas is demoable and match-quality is materially healthier after the head gate, but it is not yet ready as a dependable Maceió daily shopping list product until staple fetch failures and ~55s cold empties are structurally reduced.**
