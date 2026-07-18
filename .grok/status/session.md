# Session status

Last update: 2026-07-18 — W-fix-empty-cache **E DONE** (pending SHA after push)

## Project lock
**HARD** Alagoas only.

## Goal
**Search matching quality** — honest eval + empty-cache poison fix.

## Operator correction (HARD)
Prior B claim “~70% products have no SEFAZ rows” is **INVALID**. Empty 200s came from parallel web-scrape stampede + fetch-fail→[] + **caching empties**. Staples like arroz exist; re-eval must be serial/low-concurrency and not treat poisoned empties as ground truth.

## Phase
**Active** — E **DONE** + F (**BLOCKED_429**, honest script ready)

## Workers
| ID | Task | Status |
|----|------|--------|
| W-catalog-100 | 100 names | **DONE** `81bed97` |
| W-eval-100 (old) | parallel live eval | **INVALID for coverage** `f7ef373` |
| W-match-improve | P0 relevance | **DONE** `5853031` |
| W-ship-D | ship C | **DONE** CI `29650180694` |
| W-fix-empty-cache | no-cache empty / distinguish fetch fail | **DONE** (see SHA below) |
| W-eval-honest | serial honest 100 script + probe | **BLOCKED_429** script ready; re-run tomorrow |

## Must-complete
| # | Status |
|---|--------|
| A catalog | **DONE** `81bed97` |
| B live eval (old) | **INVALID** — false missing under load |
| C match improvements | **DONE** `5853031` |
| D ship C | **DONE** |
| **E** empty-cache + fetch-fail honesty | **DONE** — W-fix-empty-cache (SHA after push) |
| **F** honest serial 100 live re-eval | **BLOCKED_429** — script ready; probe 429; re-run after quota |

## Concurrency
**N=1** after E lands — F waits on quota only.

## Live signals
- Prod probe: **HTTP 429** daily limit (W-eval-honest `--probe-only` arroz; evidence `match_eval_100_honest_BLOCKED_429.md`)
- Scheduler: `019f75c59715` every 10m

## Next focus
F re-run after quota:
```
API_BASE=https://alagoas.precospublicos.ia.br CONCURRENCY=1 \
  python3 backend/scripts/eval_shopping_list_100.py --out .grok/status/match_eval_100_honest.json
```
Probe first: `python3 backend/scripts/eval_shopping_list_100.py --probe-only` (exit 0 = safe to full run).

## E summary
- No-cache empty SEFAZ responses; no-cache on fetch exception
- Read-side purge of poisoned empty cache entries
- Metrics: `items_fetch_failed` / `fetch_failed_labels` (no_data vs upstream_failed)
- Tests: `backend/tests/test_empty_cache.py` (5) + partial/api green
- Report: `.grok/status/worker_w_fix_empty_cache_report.md`
