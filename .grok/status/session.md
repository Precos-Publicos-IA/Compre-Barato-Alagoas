# Session status

Last update: 2026-07-18 — **B DONE** (W-eval-100)

## Project lock
**HARD** Alagoas only.

## Goal
**Search matching quality** — live eval of 100 complete; next is match improve (C).

## Operator HARD
Matching/function over looks; API/browser; no full matrix. Orchestrator spawns only.

## Phase
**Active** — Phase C ready (match improvements + tests)

## Workers
| ID | Task | Status |
|----|------|--------|
| W-catalog-100 | 100 product names | **DONE** `81bed97` |
| W-eval-100 | Live API match score all 100 | **DONE** |

## Must-complete
| # | Status |
|---|--------|
| A 100-product catalog | **DONE** `backend/tests/fixtures/shopping_list_100.json` @ `81bed97` |
| B Live API match eval report | **DONE** — see artifacts below |
| C Match improvements + tests | **OPEN** — after B |
| D Ship + scoped re-eval | **OPEN** — after C |

## B artifacts (W-eval-100)
| Path | Role |
|------|------|
| `.grok/status/match_eval_100.json` | All 100 live scores + summary |
| `.grok/status/worker_w_eval_100_report.md` | Human report (counts, worst ~20, fix themes) |
| `backend/scripts/eval_shopping_list_100.py` | Reusable live eval runner |
| `.grok/status/match_eval_100_run.log` | Run log |
| `.grok/status/match_eval_100_missing_recheck.json` | Serial recheck of missing |

### B headline
- **pass 2 / wrong_class 27 / missing 71 / error 0** (n=100)
- Only **ovo/ovos** passed product class; heavy **egg cross-bleed** on unrelated queries; **sal/óleo/feijão/açúcar/café** classic traps; **arroz/leite/macarrão** empty stores
- Latency p50≈1034ms p95≈2902ms (warm/empty-cache path); earlier cold empties ~55s; post-eval bulk hit **HTTP 429**
- **Did not** change `relevance.py` (C owns fixes)

## Concurrency
**N=1** — next owner: W-match-improve (C). Avoid multi-writer on relevance.

## Next focus
Spawn **W-match-improve** on worst failures: intent gate / egg bleed (P0), empty staples coverage (P0), PR1 traps sal/óleo/feijão/açúcar/café (P1), package-class sort (P1).
