# Session status

Last update: 2026-07-18 W-G-improve — **G DONE** `efca61d` (RAG cross-class rewrite guard)

## Project lock
**HARD** Alagoas only.

## Operator correction
Old B “71 missing SEFAZ” **INVALID**. Honest serial: **found_count=91/100**.

## Phase
**G DONE** — next **H** ship G + live verify (deploy watch)

## Workers
| ID | Status |
|----|--------|
| W-F-run2 | **DONE** (eval finished; final JSON on disk) |
| **W-F-status** | **DONE** — honest artifacts committed + pushed to `origin/main` |
| **W-G-improve** | **DONE** — `efca61d` — report `worker_w_g_improve_report.md` |

## Must-complete
| # | Status |
|---|--------|
| A catalog | **DONE** |
| B old parallel | **INVALID** |
| C early match | **DONE** |
| D ship C | **DONE** |
| E empty-cache | **DONE** |
| **F** honest serial 100 | **DONE** — pass=**71** wrong=**20** missing_after_retry=**9** found=**91** upstream_error=**0** all web — artifacts on main |
| **G** improve from honest WC | **DONE** — **`efca61d`** — RAG poison + residual class gates; offline 20/20 WC emptied |
| **H** ship G + offline re-score | **OPEN** — deploy watch + live smoke (poison keys filtered even if Redis still has them) |

## F artifacts (on main)
- `.grok/status/match_eval_100_honest.json`
- `.grok/status/match_eval_100_honest_report.md`
- `.grok/status/match_eval_100_honest_run_log.txt` (`.log` gitignored)
- `.grok/status/worker_w_eval_honest_report.md`

## Concurrency
**N=2** — status commit ∥ improve (different files). Host CPU ~73% / Tctl~71°C at F finish — OK.

## F headline (proves operator right)
| Metric | Old invalid parallel | Honest serial |
|--------|---------------------:|--------------:|
| pass | 2 | **71** |
| wrong_class | 27 | **20** |
| missing | 71 | **9** (after retry) |
| found | 29 | **91** |

## Next focus
G lands → H ship. No new full 100 live unless needed.
