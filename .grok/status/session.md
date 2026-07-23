# Session status

Last update: 2026-07-23T19:52Z W-b2-verify HARD_BLOCK + agent fix

## Project lock
**HARD** Alagoas only.

## Goal
Self-improving matching MVP (`docs/self-improving-matching-plan.md` P0–P4) + staple fetch verification.

## Testing policy (session override)
**Not UI-focused.** Skip full `ui-viewport-qa` matrix / Flutter web matrix / A4–A7 visual ship path for matching work.
**Required:** backend pytest, API/function e2e (TestClient, scripts against local mock and/or live smoke serial), learn_policy/outcome_log unit tests.
**Optional only if path touches Flutter:** minimal `flutter test` for that file — never full viewport suite.

## Phase
**Active** — M0+M1+M2+M3 shipped; **B2-verify DONE HARD_BLOCK**; next **M4** + deploy B2 accent/staple rewrite fix

## Must-complete
| # | Status |
|---|--------|
| A–K prior | **DONE** |
| **M0** match_rules_version + baseline | **DONE** `5a16961` W-m0-m1 |
| **M1** outcome log | **DONE** `5a16961` W-m0-m1 |
| **M2** auto_label | **DONE** `56ff4a5` W-m2-label — report `worker_w_m2_label_report.md` |
| **M3** learn_policy v2 | **DONE** `3ae1f52` (feature `cf851c3`) W-m3-learn — report `worker_w_m3_learn_report.md` |
| **M4** offline rescore + live smoke scripts | **QUEUED** next |
| **B2-verify** staple warm/fetch smoke | **DONE — HARD_BLOCK SEFAZ** (live REGRESSED vs baseline; accent/ovo agent fix in tree, needs deploy) — report `worker_w_b2_verify_report.md` |
| Commit `docs/self-improving-matching-plan.md` | **DONE** in `5a16961` |

## Workers
| ID | Task |
|----|------|
| W-m0-m1 | **DONE** `5a16961` — report `worker_w_m0_m1_report.md` |
| W-m2-label | **DONE** `56ff4a5` — Phase 2 auto_label; report `worker_w_m2_label_report.md` |
| W-m3-learn | **DONE** `3ae1f52` — Phase 3 learn_policy v2; report `worker_w_m3_learn_report.md` |
| W-b2-verify | **DONE** HARD_BLOCK live SEFAZ; accent cache + staple static rewrite fix; report `worker_w_b2_verify_report.md` |
| W-m4-measure | **ACTIVE** Phase 4 offline rescore + live smoke scripts |

## Residual
- Head weak tops; honest-100; plan P5–P7 later
- **B2 hard-block:** re-probe after deploy of accent/staple rewrite; if `leite` still ~55s fail → SEFAZ only
- Intermittent live **502** under serial staple load (gateway)

## Next focus
- Spawn/finish **M4** (offline rescore + serial live smoke scripts)
- Deploy B2 agent fix + VPS prewarm; re-run 7-staple serial smoke
