# Session status

Last update: 2026-07-23T20:15Z W-b2-verify — staple warm/fetch smoke **HARD_BLOCKED** (evidence closed; SLO not green)

## Project lock
**HARD** Alagoas only.

## Goal
Self-improving matching MVP complete; staple fetch **HARD_BLOCKED** with agent accent fix pending deploy + re-probe.

## Testing policy
Backend/function only for matching — no full UI matrix.

## Phase
**MVP measure loop DONE** — **B2-verify HARD_BLOCKED** (live fetch); next: deploy accent/staple fix + re-smoke; optional P5 lexicon

## Must-complete
| # | Status |
|---|--------|
| A–K prior | **DONE** |
| **M0** | **DONE** `5a16961` |
| **M1** | **DONE** `5a16961` |
| **M2** | **DONE** `56ff4a5` |
| **M3** | **DONE** `cf851c3` / `3ae1f52` |
| **M4** | **DONE** `cc2807f` — report `worker_w_m4_measure_report.md` |
| **B2-verify** | **HARD_BLOCKED** — live REGRESSED (pass1 found 0.14 / fail 0.86; pass2 found 0.29 / fail 0.43 + 502s). Reason: SEFAZ ~55s empties + accent miss (`feijão`≠`feijao` cache) + prewarm insufficient for accented/singular terms. Wiring `PREWARM_STAPLES` OK. Evidence: `worker_w_b2_verify_report.md`, `worker_w_b2_verify_probes.json`, `worker_w_b2_verify_accent_cmp.json`. Fix `9dd136b` needs **deploy + re-smoke** — **not** SLO DONE |
| Matching plan doc | **DONE** in `5a16961` |

## MVP-S1–S5
**CLOSED** (M0–M4 definitions met on main).

## Workers
| ID | Task |
|----|------|
| W-m0…M4 | **DONE** |
| W-b2-verify | **HARD_BLOCKED** (ticket closed with evidence; warm fetch SLO not met) — report `worker_w_b2_verify_report.md` |
| Loop-spawned duplicates (if any) | ignore if work already on main; do not re-open M3/M4/B2 verify suite |

## Open / next (spawn only if not already owned)
1. **Deploy** tip including `9dd136b` accent-fold + staple rewrite; confirm `PREWARM_STAPLES` prewarm
2. **Re-run** 7-staple serial smoke (CONCURRENCY=1, Maceió); if `leite` still ~55s → pure SEFAZ
3. **Post-deploy** `match_live_smoke.py` serial (when SEFAZ healthy) — M4 path
4. Optional **P5** lexicon miner when prioritized

## Residual
- **B2 fetch hard-block** until post-deploy re-probe (match track separate from fetch)
- Head weak tops (queijo snack, peito sopa, alho molho)
- Offline 10 “regressed good→bad” under stricter head (documented M4)
- Honest-100 re-eval; intermittent live **502** under serial staple load
- Plan P6 Flutter feedback wire, P7 model scorer

## Loop note
10m loop must re-read **git tip + report files on disk** before re-spawning M3/M4/B2. Status lag caused duplicate spawns — B2-verify is **HARD_BLOCKED with evidence**, not an open implement ticket; do not re-run 55s×N suite unless deploying re-verify.

## Hardware note
Prefer windowed CPU + k10temp; do not over-spawn when must-complete empty.
