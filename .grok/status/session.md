# Session status

Last update: W-home-recapture DONE — #1 hard-blocked with fresh evidence (not PASS)

## Project lock
**HARD** Alagoas only. Refuse foreign trees.

## Goal
Must-complete until empty or hard-blocked with evidence.

## Phase
A residual closed as **hard-block** (home V-FORM pixels)

## Hardware (end of W-home-recapture)
| Signal | Value | Action |
|--------|--------|--------|
| windowed CPU | cool at start (~8%) | tried capture |
| Tctl | ~50°C at start | tried capture |
| qemu friends | **killed** mid-task (was ~285% CPU `-gpu host`); restart not required | still no CanvasKit first frame after kill |

## Workers
| id | Status |
|----|--------|
| W-vform | **DONE** `77c58a5` |
| W-emulator-smoke | **DONE** `d1a4245` — 7/7 on emulator-5554 |
| W-home-recapture | **DONE** — hard-block re-documented; report `worker_w_home_recapture_report.md` |

## Must-complete
| # | Status |
|---|--------|
| 1 V-FORM open_bads 0 | **HARD-BLOCK** residual home only — open_bads_matrix=2; evidence in matrix_critique + review sidecars + a6_open_bads |
| 2 Project lock | **DONE** |
| 3 matrix_emulator smoke | **DONE** `d1a4245` |
| 4 Human re-schedule `/loop` | **OPEN** |

## Concurrency
**N=0** no active workers.

## Next
1. Session **Done** for agent must-complete list except human #4 (hard-block on #1 is documented).
2. Later: when host Chrome paints Flutter first frame again, re-run `MATRIX_FORMATS=qhd,4k MATRIX_SCREENS=home` on :18090 and clear open_bads.
