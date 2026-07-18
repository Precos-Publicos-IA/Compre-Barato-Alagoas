# Session status

Last update: orchestrator /loop tick — W-home-capture ~16m golden path mid-flight

## Project lock
**HARD** Alagoas only. Refuse foreign projects.

## Goal
open_bads 0 for qhd/4k home (honest pixels).

## Phase
A — alternate stills (golden tests on disk, not yet PASS)

## Hardware (12s)
| Signal | Value | Action |
|--------|--------|--------|
| windowed CPU | **28.2%** | below 50% |
| loadavg | 3.5 / 2.9 / 4.8 | OK |
| **Tctl k10temp** | **64°C** | under 80°C |
| MemAvailable | ~20 / 32 Gi | OK |

## Workers
| id | Status |
|----|--------|
| W-home-capture `019f72e8-ccc4-…` | **RUNNING** ~16m; 61 tools; 1 error; dirty/new: `home_viewport_golden_test.dart`, `_solo_test.dart`; home PNGs mtime ~22:58 still splash-class (~19–39KB, high white%); open_bads=2 |

## Must-complete
| # | Status |
|---|--------|
| 1 V-FORM home open_bads 0 | **IN PROGRESS** |
| 2 Project lock | **DONE** |
| 3 matrix_emulator smoke | **DONE** |
| 4 Human re-schedule `/loop` | **OPEN** (human) |

## Concurrency
**N=1 → N=1**. Keep sole owner. No second capture worker.

## Next
Reap W-home-capture; re-spawn if unfinished. Do not mark PASS on white stills.
