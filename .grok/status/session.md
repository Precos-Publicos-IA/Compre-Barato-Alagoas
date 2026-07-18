# Session status

Last update: orchestrator /loop tick — spawned W-home-capture for open qhd/4k stills

## Project lock
**HARD** Alagoas only. Refuse foreign projects.

## Goal
open_bads 0 for qhd/4k home (honest pixels).

## Phase
A — home capture tooling / alternate stills

## Hardware (12s)
| Signal | Value | Action |
|--------|--------|--------|
| windowed CPU | **17.6%** | below 50% — spawn 1 worker |
| loadavg | 3.3 / 5.2 / 9.2 | OK |
| **Tctl k10temp** | **57°C** | under 80°C |
| MemAvailable | ~19 / 32 Gi | OK |
| app :18090 | 200 | stack up |
| api :8000 | 200 | OK |
| qemu friends | up | not our worker; leave alone |

## Workers
| id | Status |
|----|--------|
| W-home-capture | **STARTED** — honest qhd/4k home stills (not hard-block) |

## Must-complete
| # | Status |
|---|--------|
| 1 V-FORM home open_bads 0 | **IN PROGRESS** (W-home-capture) |
| 2 Project lock | **DONE** |
| 3 matrix_emulator smoke | **DONE** |
| 4 Human re-schedule `/loop` | **OPEN** (human) |

## Concurrency
**N=0 → N=1** (CPU 17.6%, completable #1 had no owner).

## Next
Reap W-home-capture → open_bads 0 or next concrete capture progress on main.
