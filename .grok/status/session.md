# Session status

Last update: 2026-07-18 15:52 UTC — W-eval-honest F BLOCKED_429 (script ready)

## Project lock
**HARD** Alagoas only.

## Goal
**Search matching quality** — honest eval + empty-cache poison fix.

## Operator correction (HARD)
Prior B claim “~70% products have no SEFAZ rows” is **INVALID**. Empty 200s came from parallel web-scrape stampede + fetch-fail→[] + **caching empties**. Staples like arroz exist; re-eval must be serial/low-concurrency and not treat poisoned empties as ground truth.

## Phase
**Active** — E (empty-cache fix) + F (**BLOCKED_429**, honest script ready)

## Workers
| ID | Task | Status |
|----|------|--------|
| W-catalog-100 | 100 names | **DONE** `81bed97` |
| W-eval-100 (old) | parallel live eval | **INVALID for coverage** `f7ef373` |
| W-match-improve | P0 relevance | **DONE** `5853031` |
| W-ship-D | ship C | **DONE** CI `29650180694` |
| W-fix-empty-cache | no-cache empty / distinguish fetch fail | **RUNNING** |
| W-eval-honest | serial honest 100 script + probe | **BLOCKED_429** script ready; re-run tomorrow |

## Must-complete
| # | Status |
|---|--------|
| A catalog | **DONE** `81bed97` |
| B live eval (old) | **INVALID** — false missing under load |
| C match improvements | **DONE** `5853031` |
| D ship C | **DONE** |
| **E** empty-cache + fetch-fail honesty | **OPEN** — W-fix-empty-cache |
| **F** honest serial 100 live re-eval | **BLOCKED_429** — script ready; probe 429; re-run after quota |

## Concurrency
**N=2** — E (backend cache path) ∥ F (eval script). No parallel live stampede. F uses CONCURRENCY≤2 if it runs live.

## Live signals
- Hardware (15s): CPU **3.4%**; loadavg 0.35 0.40 0.44; **k10temp Tctl=45.2°C**
- Prod probe: **HTTP 429** daily limit (W-eval-honest `--probe-only` arroz; evidence `match_eval_100_honest_BLOCKED_429.md`)
- Scheduler: `019f75c59715` every 10m

## Scheduling rationale
Operator invalidated coverage conclusion → cannot stay idle with false B DONE. Spawn E (fix poison) and F (honest methodology) immediately. Full live F waits on quota.

## Next focus
E lands + push. F hard-blocked on prod 429 — re-run tomorrow:
```
API_BASE=https://alagoas.precospublicos.ia.br CONCURRENCY=1 \
  python3 backend/scripts/eval_shopping_list_100.py --out .grok/status/match_eval_100_honest.json
```
Probe first: `python3 backend/scripts/eval_shopping_list_100.py --probe-only` (exit 0 = safe to full run).
