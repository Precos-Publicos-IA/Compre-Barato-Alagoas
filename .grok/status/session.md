# Session status

Last update: 2026-07-23T20:10Z W-b2-resmoke — B2-verify **DONE** (warm SLO pass post `9dd136b`)

## Project lock
**HARD** Alagoas only.

## Goal
Matching MVP M0–M4 shipped; B2 fetch hard-block **cleared** post accent-fold deploy; advance Phase 5 lexicon.

## Testing policy
Backend/function only for matching — no full UI matrix. Live smoke serial CONCURRENCY=1 only.

## Phase
**MVP measure loop DONE** (M0–M4). **B2-verify DONE** (warm staple SLO pass after resmoke). **M5 lexicon ACTIVE**.

## Must-complete
| # | Status |
|---|--------|
| A–K prior | **DONE** |
| **M0–M4** | **DONE** (M4 `cc2807f`) |
| **B2-verify** | **DONE** — W-b2-resmoke post-deploy: found **6/7**, fetch_fail **1/7** both passes; accent pairs 5/5 OK. Residual: **`leite` pure SEFAZ** (~55s). Artifacts `worker_w_b2_resmoke_*` |
| **M5** lexicon mining | **IN_PROGRESS** W-m5-lexicon (5-S1…5-S7) |
| Matching plan doc | **DONE** in `5a16961` |

## Workers
| ID | Task |
|----|------|
| W-m0…M4 | **DONE** |
| W-b2-verify | **HARD_BLOCKED** closed pre-deploy — report `worker_w_b2_verify_report.md` |
| W-b2-resmoke | **DONE** — `worker_w_b2_resmoke_report.md` + `worker_w_b2_resmoke_probes.json`; verdict **DONE_SLO_PASS** |
| W-m5-lexicon | **ACTIVE** Phase 5 mine_match_lexicon + opt-in load |

## Hardware (this cycle)
- Windowed CPU busy ~**3.1%** / 12s; loadavg ~0.38; **k10temp Tctl=46°C**; MemAvail ~21 GiB
- Headroom for 2 workers (1 live I/O serial + 1 code)

## Deploy note
- CI success for `9dd136b` accent-fold (~19:59Z); live health ok
- Live probes show `match_rules_version=2026-07-23-head-v1` + staple rewrites (`feijao carioca`, `ovos`, …) — VPS git SHA not host-proven

## B2 resmoke numbers (vs prior HARD_BLOCK)
| pass | prior found / fail | resmoke found / fail |
|------|--------------------|----------------------|
| pass1 | 0.14 / 0.86 | **0.86 / 0.14** |
| pass2 | 0.29 / 0.43 (+2×502) | **0.86 / 0.14** (0×502) |
| residual | accent/singular + SEFAZ | **leite only** (SEFAZ after `leite uht` rewrite) |

## Residual
- **`leite`** SEFAZ ~55s empty (external; not re-HARD_BLOCK of accent ship)
- Head weak tops; honest-100; offline residual 10 good→stricter
- P6 feedback wire; P7 model scorer after M5

## Loop note
Do **not** re-spawn M3/M4. B2 agent-owned fetch residual is closed; do not re-run full B2 HARD_BLOCK suite without new regression evidence.
