# Session status

Last update: lock hardened (workspace + repo); W-vform still owner of V-FORM

## Project lock
**HARD** — Alagoas only. Workspace `/code/alagoas/PROJECT_LOCK.md` + repo `PROJECT_LOCK.md`.
Refuse other projects (incl. `/code/1st-rust-game`). No half-done parking. Worker prompts must include lock one-liner.

## Goal
Must-complete open items until empty (then Done).

## Phase
A — V-FORM recapture in flight; process lock refresh done

## Hardware (note)
Re-sample each tick: 10–30s windowed CPU, k10temp Tctl (not acpitz). N=1 while matrix_capture heavy.

## Workers
| id | Status |
|----|--------|
| W-ship-hygiene | DONE `a83a285` |
| W-lock-refresh | **THIS TICK** — workspace PROJECT_LOCK + AGENTS; repo lock/AGENTS/orchestrator hardened (commit process only; do not touch V-FORM dirty UI) |
| W-vform | **RUNNING** `019f7271-8ff3-…` — owns QHD/4K V-FORM through open_bads 0 + commit |
| W-emulator-smoke | **OPEN** after #1; need emulator-5554 + CPU headroom |

## Must-complete
| # | Status |
|---|--------|
| 1 V-FORM open_bads 0 | **IN PROGRESS** (W-vform) |
| 2 Project lock + finish rules (workspace + repo + orchestrator) | **IN PROGRESS** → commit/push process files |
| 3 matrix_emulator smoke | **OPEN** (after #1) |
| 4 Human re-schedule `/loop` with latest paste | **OPEN** (after process ship) |

## Concurrency
- **N=1** product worker (W-vform) while capture burns CPU
- Process commit is light docs-only — do not stack second capture/emulator

## Next
1. Ship process lock files (no V-FORM product files in that commit)
2. Reap W-vform → open_bads 0 + push product fix
3. Emulator smoke when cool
4. Done only when 1+2+3 closed
