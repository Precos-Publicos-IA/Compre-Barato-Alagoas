# W-eval-100 report — live match quality (100 queries)

**Status:** **B DONE**  
**Worker:** W-eval-100  
**Date:** 2026-07-18  
**API:** `POST https://alagoas.precospublicos.ia.br/api/v1/search`  
**Fixture:** `backend/tests/fixtures/shopping_list_100.json` (catalog commit `81bed97`)  
**Geo:** lat=-9.6658, lon=-35.735, radius_km=8, days=7  
**Concurrency:** 5 · timeout_s=150.0  
**Evaluated at:** 2026-07-18T15:22:59.787338+00:00  
**Heuristics:** v2 (offline re-score after live capture)

## Artifacts

| Path | Role |
|------|------|
| `.grok/status/match_eval_100.json` | Machine-readable results + summary (all 100) |
| `.grok/status/worker_w_eval_100_report.md` | This report |
| `backend/scripts/eval_shopping_list_100.py` | Reusable eval runner (modest concurrency, checkpoints) |
| `.grok/status/match_eval_100_run.log` | Console run log |
| `.grok/status/match_eval_100_missing_recheck.json` | Serial recheck of 71 missing (then 429) |

## Headline counts

| Verdict | Count | Notes |
|---------|------:|-------|
| **pass** | **2** | Only true eggs class looked correct at top |
| **wrong_class** | **27** | Top-1 (or ≥50% of top lines) fails heuristics |
| **missing** | **71** | HTTP 200, zero stores / empty |
| **error** | **0** | Timeouts / non-200 in primary run |
| **found** (any store) | **29** | Before quality filter |
| **total** | **100** | |

**Effective quality rate (pass/100): 2%**  
**Found-but-wrong rate among found: 27/29 = 93%**

### Latency (primary run, ms)

| metric | value |
|--------|------:|
| p50 | 1034 |
| p95 | 2902 |
| mean | 1003 |
| min | 196 |
| max | 3563 |

Cold SEFAZ paths earlier in the session were ~45–56s; after warm/negative-cache, most empties returned in ~200–2700ms.

## By category

| Category | total | pass | wrong_class | missing |
|----------|------:|-----:|------------:|--------:|
| staples | 12 | 0 | 7 | 5 |
| dairy | 12 | 2 | 2 | 8 |
| oils | 12 | 0 | 4 | 8 |
| meat | 12 | 0 | 2 | 10 |
| produce | 12 | 0 | 0 | 12 |
| bakery | 8 | 0 | 4 | 4 |
| beverages | 10 | 0 | 4 | 6 |
| snacks | 6 | 0 | 2 | 4 |
| cleaning | 8 | 0 | 2 | 6 |
| hygiene | 6 | 0 | 0 | 6 |
| baby | 1 | 0 | 0 | 1 |
| pet | 1 | 0 | 0 | 1 |

**Produce / hygiene / baby / pet:** 100% missing in this run.  
**Staples:** almost all either missing (arroz, macarrão, fubá, aveia) or wrong-class (feijão tempero, sal snacks, farinha→eggs).

## Pass list (only 2)

- **ovo** (id=17): 'OVOS EXTRA STA MARIA LUNA UN', 'OVOS', 'OVOS EXTRA LUNA'
- **ovos** (id=18): 'OVOS EXTRA STA MARIA LUNA UN', 'OVOS', 'OVOS EXTRA LUNA'

> Note: ovo/ovos top lines are single-unit eggs (`OVOS BRANCOS UND` ~R$0.50), not bandeja/dozen. Package-class ranking still weak, but product *class* is correct (not pasta MAC/OVOS).

## Worst failures (top ~20)

### 1. `farinha de trigo` (id=7, staples) — **wrong_class**

- latency_ms=226 · http=200 · match_rate=1.0 · stores=5
- reason: cross-query bleed: eggs returned for non-egg query
- top: `OVOS BRANCOS UND` · price=0.5 · unit_price=0.5
- also: `OVOS EXTRA STA MARIA LUNA UN`, `OVOS BRANCO - UNIDADE`, `OVOS`

### 2. `farinha de mandioca` (id=8, staples) — **wrong_class**

- latency_ms=223 · http=200 · match_rate=1.0 · stores=5
- reason: cross-query bleed: eggs returned for non-egg query
- top: `OVOS BRANCOS UND` · price=0.5 · unit_price=0.5
- also: `OVOS EXTRA STA MARIA LUNA UN`, `OVOS BRANCO - UNIDADE`, `OVOS`

### 3. `queijo` (id=21, dairy) — **wrong_class**

- latency_ms=218 · http=200 · match_rate=1.0 · stores=5
- reason: cross-query bleed: eggs returned for non-egg query
- top: `OVOS BRANCOS UND` · price=0.5 · unit_price=0.5
- also: `OVOS EXTRA STA MARIA LUNA UN`, `OVOS BRANCO - UNIDADE`, `OVOS`

### 4. `queijo mussarela` (id=22, dairy) — **wrong_class**

- latency_ms=226 · http=200 · match_rate=1.0 · stores=5
- reason: cross-query bleed: eggs returned for non-egg query
- top: `OVOS BRANCOS UND` · price=0.5 · unit_price=0.5
- also: `OVOS EXTRA STA MARIA LUNA UN`, `OVOS BRANCO - UNIDADE`, `OVOS`

### 5. `molho de tomate` (id=29, oils) — **wrong_class**

- latency_ms=222 · http=200 · match_rate=1.0 · stores=5
- reason: cross-query bleed: eggs returned for non-egg query
- top: `OVOS BRANCOS UND` · price=0.5 · unit_price=0.5
- also: `OVOS EXTRA STA MARIA LUNA UN`, `OVOS BRANCO - UNIDADE`, `OVOS`

### 6. `caldo de galinha` (id=36, oils) — **wrong_class**

- latency_ms=219 · http=200 · match_rate=1.0 · stores=5
- reason: cross-query bleed: eggs returned for non-egg query
- top: `OVOS BRANCOS UND` · price=0.5 · unit_price=0.5
- also: `OVOS EXTRA STA MARIA LUNA UN`, `OVOS BRANCO - UNIDADE`, `OVOS`

### 7. `peito de frango` (id=38, meat) — **wrong_class**

- latency_ms=221 · http=200 · match_rate=1.0 · stores=5
- reason: cross-query bleed: eggs returned for non-egg query
- top: `OVOS BRANCOS UND` · price=0.5 · unit_price=0.5
- also: `OVOS EXTRA STA MARIA LUNA UN`, `OVOS BRANCO - UNIDADE`, `OVOS`

### 8. `pão` (id=61, bakery) — **wrong_class**

- latency_ms=221 · http=200 · match_rate=1.0 · stores=5
- reason: cross-query bleed: eggs returned for non-egg query
- top: `OVOS BRANCOS UND` · price=0.5 · unit_price=0.5
- also: `OVOS EXTRA STA MARIA LUNA UN`, `OVOS BRANCO - UNIDADE`, `OVOS`

### 9. `pão de forma` (id=62, bakery) — **wrong_class**

- latency_ms=219 · http=200 · match_rate=1.0 · stores=5
- reason: cross-query bleed: eggs returned for non-egg query
- top: `OVOS BRANCOS UND` · price=0.5 · unit_price=0.5
- also: `OVOS EXTRA STA MARIA LUNA UN`, `OVOS BRANCO - UNIDADE`, `OVOS`

### 10. `pão francês` (id=63, bakery) — **wrong_class**

- latency_ms=233 · http=200 · match_rate=1.0 · stores=5
- reason: cross-query bleed: eggs returned for non-egg query
- top: `OVOS BRANCOS UND` · price=0.5 · unit_price=0.5
- also: `OVOS EXTRA STA MARIA LUNA UN`, `OVOS BRANCO - UNIDADE`, `OVOS`

### 11. `pão de queijo` (id=68, bakery) — **wrong_class**

- latency_ms=225 · http=200 · match_rate=1.0 · stores=5
- reason: cross-query bleed: eggs returned for non-egg query
- top: `OVOS BRANCOS UND` · price=0.5 · unit_price=0.5
- also: `OVOS EXTRA STA MARIA LUNA UN`, `OVOS BRANCO - UNIDADE`, `OVOS`

### 12. `água` (id=71, beverages) — **wrong_class**

- latency_ms=219 · http=200 · match_rate=1.0 · stores=5
- reason: cross-query bleed: eggs returned for non-egg query
- top: `OVOS BRANCOS UND` · price=0.5 · unit_price=0.5
- also: `OVOS EXTRA STA MARIA LUNA UN`, `OVOS BRANCO - UNIDADE`, `OVOS`

### 13. `água de coco` (id=78, beverages) — **wrong_class**

- latency_ms=220 · http=200 · match_rate=1.0 · stores=5
- reason: cross-query bleed: eggs returned for non-egg query
- top: `OVOS BRANCOS UND` · price=0.5 · unit_price=0.5
- also: `OVOS EXTRA STA MARIA LUNA UN`, `OVOS BRANCO - UNIDADE`, `OVOS`

### 14. `barra de cereal` (id=84, snacks) — **wrong_class**

- latency_ms=220 · http=200 · match_rate=1.0 · stores=5
- reason: cross-query bleed: eggs returned for non-egg query
- top: `OVOS BRANCOS UND` · price=0.5 · unit_price=0.5
- also: `OVOS EXTRA STA MARIA LUNA UN`, `OVOS BRANCO - UNIDADE`, `OVOS`

### 15. `água sanitária` (id=87, cleaning) — **wrong_class**

- latency_ms=220 · http=200 · match_rate=1.0 · stores=5
- reason: cross-query bleed: eggs returned for non-egg query
- top: `OVOS BRANCOS UND` · price=0.5 · unit_price=0.5
- also: `OVOS EXTRA STA MARIA LUNA UN`, `OVOS BRANCO - UNIDADE`, `OVOS`

### 16. `saco de lixo` (id=92, cleaning) — **wrong_class**

- latency_ms=227 · http=200 · match_rate=1.0 · stores=5
- reason: cross-query bleed: eggs returned for non-egg query
- top: `OVOS BRANCOS UND` · price=0.5 · unit_price=0.5
- also: `OVOS EXTRA STA MARIA LUNA UN`, `OVOS BRANCO - UNIDADE`, `OVOS`

### 17. `sal` (id=6, staples) — **wrong_class**

- latency_ms=198 · http=200 · match_rate=1.0 · stores=5
- reason: sal → snack chips / 's sal' / seasoned snack
- top: `CASTANHA CAJU CROC TORRADA S SAL 50G` · price=0.33 · unit_price=6.6
- also: `PIPOCA BETTI 15G SAL`, `Pipoca Bokus sal 30g`, `SALG MILHO CORINGUITOS CEB SAL 30G`

### 18. `óleo` (id=25, oils) — **wrong_class**

- latency_ms=219 · http=200 · match_rate=1.0 · stores=5
- reason: cooking oil query → OLEO SATURADO / non-standard oil label
- top: `OLEO SATURADO 1LT` · price=2.0 · unit_price=2.0
- also: `MIST.LEITE E OLEO V.DAMARE 17% 200G`, `OLEO DE SOJA SOYA 900ML`, `SARD.PALMEIRA OLEO`

### 19. `óleo de soja` (id=26, oils) — **wrong_class**

- latency_ms=219 · http=200 · match_rate=1.0 · stores=5
- reason: cooking oil query → OLEO SATURADO / non-standard oil label
- top: `OLEO SATURADO 1LT` · price=2.0 · unit_price=2.0
- also: `MIST.LEITE E OLEO V.DAMARE 17% 200G`, `OLEO DE SOJA SOYA 900ML`, `SARD.PALMEIRA OLEO`

### 20. `açúcar` (id=4, staples) — **wrong_class**

- latency_ms=218 · http=200 · match_rate=1.0 · stores=5
- reason: açúcar → candy / zero-sugar confection
- top: `BIGBIG ZERO ACUCAR C 4` · price=0.5 · unit_price=0.5
- also: `ACUCAR 40G AZUL (SCH) FACA A FESTA`, `ACUCAR CRISTAL ESPECIAL FORMOSO 30KG`, `Acucar Cristal Corur`

## Failure themes (for W-match-improve / worker C)

### T1 — Cross-query bleed / price-sorted junk wins (CRITICAL)
Many non-egg queries return the same cheap egg SKUs (`OVOS BRANCOS UND` R$0.50) as top hit: farinha, queijo, pão, água, molho de tomate, peito de frango, saco de lixo, etc.

**Likely causes:** relevance floor too low; ranking still dominated by absolute price; possible cache key collision or “best cheap offer” global leak; SEFAZ web returns loosely related tokens.

**Fix themes:**
1. Hard **intent token gate** before ranking (description must match primary token / synonym set).
2. Raise `min_score` / drop offers below threshold instead of filling with cheapest junk.
3. Audit cache keys: ensure term-specific cache never serves another term’s cards.
4. Prefer package-class and unit_price only **after** class filter.

### T2 — Classic PR1 class confusions (still live)
| Query | Bad top | Wanted |
|-------|---------|--------|
| sal | CASTANHA CAJU … S SAL, PIPOCA … SAL | sal refinado/grosso 1kg |
| óleo / óleo de soja | OLEO SATURADO 1LT, MIST.LEITE E OLEO, SARD…OLEO | OLEO SOJA 900ML |
| feijão / feijão preto | TEMPE(I)RO PARA FEIJAO 10–15g | FEIJAO CARIOCA/PRETO 1kg |
| açúcar / demerara | BIGBIG ZERO ACUCAR, 40g sachet | ACUCAR CRISTAL 1kg |
| café / café solúvel | “Coracao, Cafe, Canela”, CARAMELOS CAFE | café torrado/moído or solúvel jar |

**Fix themes:** extend `relevance.py` goldens already in `test_relevance_quality.py` to cover feijão-tempero, açúcar-candy, café-caramel; demote substring-only hits (`S SAL`, `C/OVOS`, `ZERO ACUCAR`).

### T3 — Coverage collapse / empty stores (71/100)
Primary run: **71 missing** with HTTP 200 and `stores: []` — including **arroz, leite, macarrão**, all produce, almost all cleaning/hygiene.

Observed independently of concurrency (serial recheck of missing also empty until rate limit). Later burst traffic produced **HTTP 429**.

**Fix themes:**
1. Investigate SEFAZ web client empty responses for high-frequency staples (arroz/leite) vs working terms (feijão/ovos/óleo).
2. Negative-cache TTL: do not cache empty long if upstream was degraded.
3. Rate-limit / queue for bulk eval and production fan-out; back off on 429.
4. Prewarm staples (`prewarm_staples.py --fetch`) after deploy; verify cache hit path returns non-empty.
5. Consider multi-rewrite fallback (arroz → “arroz tipo 1”, leite → “leite uht”) when zero stores.

### T4 — Package class still weak even when class is right
ovo/ovos pass product class but surface **unit eggs** not bandeja c/12–30. Oil has correct soja 900ml at rank 3 under junk. Açúcar has 30kg industrial pack in top-3.

**Fix themes:** package_class_rank already exists — ensure it drives **sort** of store lines, not only filter; demote UN single eggs and industrial 30kg for household queries.

### T5 — Substring / token traps
- `sal` matches “S SAL”, “CEB SAL”, pipoca salgada  
- `açúcar` matches “ZERO ACUCAR” candy  
- `óleo` matches sardinha/atum “em óleo”, “óleo saturado” nutrition-ish labels  
- `feijão` matches “tempero para feijão”

**Fix themes:** whole-word / negative-token lists; boost exact-class phrases (`sal refinado`, `oleo de soja`, `feijao carioca`).

## Recommended priority for worker C (match improve)

1. **P0** Intent gate + stop egg bleed across unrelated queries (biggest user-facing lie).  
2. **P0** Empty-result investigation for arroz/leite/macarrão (coverage).  
3. **P1** PR1 traps: sal snacks, óleo junk, feijão tempero, açúcar candy, café caramel.  
4. **P1** Package-class sort for eggs/oil/sugar household sizes.  
5. **P2** Rate-limit / empty-cache policy so eval + multi-item baskets stay reliable.

## Method notes

- Each query: single-item `POST /api/v1/search` with fixed Maceió geo.
- Concurrency 5; no silent skips; timeouts would be recorded as error (none in primary complete run).
- `wrong_class` heuristics applied to top store lines; aggregate = top-1 wrong OR ≥50% of unique top lines wrong.
- **Did not** modify `relevance.py` / ranking (scoped to eval only).
- After primary run, serial recheck of missing confirmed empties; then API returned **429** (document as operational constraint, not as substitute for empty-store findings that preceded 429).

## Exit criteria for B

| Criterion | Status |
|-----------|--------|
| All 100 scored vs live API | **YES** |
| Machine JSON written | **YES** `.grok/status/match_eval_100.json` |
| Human report with counts + worst ~20 + fix themes | **YES** |
| session.md B DONE | **YES** (this worker updates) |
| No relevance.py changes | **YES** |
