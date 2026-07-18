# Session status

Last update: 2026-07-18 — W-catalog-100 DONE (100 shopping-list product names)

## Project lock
**HARD** Alagoas only. Refuse foreign projects.

## Goal
**Search matching quality** — 100 common list names → live API eval → improve matchers.

## Operator HARD
- Functionality / matching over looks; browser/API over phone; **no** full UI matrix.
- Orchestrator spawns only; workers implement.

## Phase
**Active** — Phase A catalog **DONE** → next: B live match eval

## Workers
| ID | Task | Status |
|----|------|--------|
| W-catalog-100 | Persist 100 PT-BR shopping-list product names | **DONE** |

## Must-complete
| # | Status |
|---|--------|
| A 100-product catalog landed | **DONE** — `backend/tests/fixtures/shopping_list_100.json` (+ `.txt`); see `worker_w_catalog_100_report.md`; commit **81bed97a09d3d9296aec8589525c5588c2e9ffe7** |
| B Live API match eval report (all 100) | **OPEN** — after A |
| C Match improvements + scoped tests for worst failures | **OPEN** — after B |
| D Ship/push product code + scoped re-eval if code changed | **OPEN** — after C |

## Concurrency
**N=1** — catalog complete; eval next (shard 100 if CPU allows).

## Live signals (this cycle)
- Catalog fixtures landed (100 unique queries, balanced categories, hard cases included)
- No production SEFAZ batch from this worker
- Untracked iOS GeneratedPluginRegistrant left out of commit (junk)

## Scheduling rationale
A complete → orchestrator should spawn B (live match eval over the 100).

## Next focus
Spawn W-eval (or shards) against live API for all 100 queries; write match-eval report.
