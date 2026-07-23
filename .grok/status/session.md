# Session status

Last update: 2026-07-23T20:30Z W-m0-m1 — M0+M1 DONE (`5a16961`); backend-first testing

## Project lock
**HARD** Alagoas only.

## Goal
Self-improving matching MVP (`docs/self-improving-matching-plan.md` P0–P4) + staple fetch verification.

## Testing policy (session override)
**Not UI-focused.** Skip full `ui-viewport-qa` matrix / Flutter web matrix / A4–A7 visual ship path for matching work.
**Required:** backend pytest, API/function e2e (TestClient, scripts against local mock and/or live smoke serial), learn_policy/outcome_log unit tests.
**Optional only if path touches Flutter:** minimal `flutter test` for that file — never full viewport suite.

## Phase
**Active** — M0+M1 shipped; next M2 auto_label + B2-verify

## Must-complete
| # | Status |
|---|--------|
| A–K prior | **DONE** |
| **M0** match_rules_version + baseline | **DONE** `5a16961` W-m0-m1 |
| **M1** outcome log | **DONE** `5a16961` W-m0-m1 |
| **M2** auto_label | **QUEUED** after M0–M1 |
| **M3** learn_policy v2 | **QUEUED** after M2 |
| **M4** offline rescore + live smoke scripts | **QUEUED** after M3 |
| **B2-verify** staple warm/fetch smoke | **QUEUED** W-b2-verify |
| Commit `docs/self-improving-matching-plan.md` | **DONE** in `5a16961` |

## Workers
| ID | Task |
|----|------|
| W-m0-m1 | **DONE** `5a16961` — report `worker_w_m0_m1_report.md` |
| W-b2-verify | API serial staple smoke; prewarm evidence |

## Residual
- Head weak tops; honest-100; plan P5–P7 later

## Next focus
M0–M1 **done** → spawn M2 (labeler).
