# Session status

Last update: orchestrator reaped W-emulator-smoke DONE; spawned W-home-recapture

## Project lock
**HARD** Alagoas only. Refuse foreign trees.

## Goal
Must-complete until empty or hard-blocked with evidence.

## Phase
A — close remaining home V-FORM pixel proof

## Hardware (12s)
| Signal | Value | Action |
|--------|--------|--------|
| windowed CPU | **8.0%** | headroom — spawn home recapture |
| loadavg | 1.8 / 4.1 / 7.8 | cool |
| **Tctl k10temp** | **50°C** | cool |
| qemu AVD friends | still up (`-gpu host`) | try capture first; kill only if needed |

## Workers
| id | Status |
|----|--------|
| W-vform | **DONE** `77c58a5` |
| W-emulator-smoke | **DONE** `d1a4245` — 7/7 on emulator-5554 |
| W-home-recapture | **STARTED** — close qhd/4k home open_bads |

## Must-complete
| # | Status |
|---|--------|
| 1 V-FORM open_bads 0 | **IN PROGRESS** residual home only (admin cleared); W-home-recapture |
| 2 Project lock | **DONE** |
| 3 matrix_emulator smoke | **DONE** `d1a4245` |
| 4 Human re-schedule `/loop` | **OPEN** |

## Concurrency
**N=1** W-home-recapture only.

## Next
1. Reap W-home-recapture → #1 DONE or hard-block evidence
2. Session Done when #1 closed/hard-blocked + #3 done (#4 is human)
