# Worker W-F-run2 / W-eval-honest report

**Task:** F — honest 100 live re-eval (serial CONCURRENCY=1)  
**Status:** **DONE**  
**Date (UTC):** 2026-07-18T16:28:44Z  
**Worker:** W-F-run2 (replaced stalled W-F-run)

## Probe (first tool call)

| Attempt | Query | HTTP | stores | data_source | exit |
|---------|-------|-----:|-------:|-------------|-----:|
| 1 | arroz | 200 | 0 | sefaz | 1 (not ok_for_full) |
| 2 | arroz | 200 | 0 | sefaz | 1 |
| 3 | feijao | 200 | 0 | sefaz | 1 |

- **Not 429** (quota ok; prior BLOCKED_429 superseded).
- Empty sefaz official path → session required honest measure anyway.
- Full serial 100 started with CONCURRENCY=1 (no parallel stampede).

Mid-run prod path healed (`197628c` empty sefaz → web fallback). Final run used **`data_source=web` for all 100**.

## Final counts (honest serial 100)

| Verdict | Count |
|---------|------:|
| **pass** | **71** |
| **wrong_class** | **20** |
| **missing_after_retry** | **9** |
| **upstream_error** | **0** |
| total | 100 |
| found_count | 91 |
| retried_count | 9 |

Artifacts:

- [`.grok/status/match_eval_100_honest.json`](match_eval_100_honest.json)
- [`.grok/status/match_eval_100_honest_report.md`](match_eval_100_honest_report.md)
- [`.grok/status/match_eval_100_honest_run_log.txt`](match_eval_100_honest_run_log.txt) (copy of run log; `*.log` gitignored)

API: `https://alagoas.precospublicos.ia.br`  
Fixture: `backend/tests/fixtures/shopping_list_100.json`  
Concurrency: **1** · retry backoff 3s · timeout 150s

### Latency (ms)

- p50 11262 · p95 22986 · min 198 · max 24374 · mean 7852

## arroz returned stores?

**Yes.** id=1 `arroz` → **pass**, http=200, `data_source=web`, **stores_found=5**, match_rate=1.0, latency 216ms (cache-warm).

Top lines (sample):

| Store | Description | Price |
|-------|-------------|------:|
| MERCADINHO DO AMIGÃO | ARROZ EMOCOES INTEGRAL 1KG | 1.00 |
| EBENEZER ALIMENTOS | FIBRA ARROZ CORINGA - PEQ 12X200G | 1.81 |
| BARRATEIRO | ARROZ BRANCO 1KG | 2.00 |
| A CASA PORTUGUESA | PORCAO DE ARROZ 250ML | 2.00 |
| MERCEARIA FERREIRA | ARROZ TIO VIEIRA BRANCO 1KG | 2.35 |

## wrong_class (20) — dominant pattern

**Cross-query bleed: eggs (`OVOS BRANCOS UND`)** returned for non-egg queries (~16/20). Examples: farinha de trigo, farinha de mandioca, queijo, pão*, peito de frango, água, saco de lixo, barra de cereal, molho de tomate, …

Other wrong_class:

- salsicha / salgadinho → Pipoca Bokus sal
- sabão em pó → COCADA LEITE
- papel higiênico → PAPEL TOALHA …

## missing_after_retry (9)

All http=200, ds=web, stores=0 after one retry:

sal, bolacha, cerveja, achocolatado, detergente, amaciante, desinfetante, sabonete, shampoo

## Category snapshot

| category | pass | wrong_class | missing |
|----------|-----:|------------:|--------:|
| produce | 12/12 | 0 | 0 |
| dairy | 10/12 | 2 | 0 |
| meat | 10/12 | 2 | 0 |
| oils | 10/12 | 2 | 0 |
| staples | 9/12 | 2 | 1 |
| bakery | 3/8 | 4 | 1 |
| cleaning | 2/8 | 3 | 3 |
| hygiene | 3/6 | 1 | 2 |
| beverages | 6/10 | 2 | 2 |

## Methodology

- CONCURRENCY=1 only (hard cap 2)
- One retry on empty stores / match_rate=0
- Verdicts: pass | wrong_class | missing_after_retry | upstream_error
- Prior parallel stampede eval `f7ef373` remains **INVALID** for coverage ground truth

## Explicitly not done (out of scope)

- Product matching code changes (no wrong_class fix this worker)
- Full UI matrix
- Parallel re-run

## Next (orchestrator)

Spawn match-improve from **honest** wrong_class list (egg bleed + weak intent tokens). F is complete measurement, not a product ship.
