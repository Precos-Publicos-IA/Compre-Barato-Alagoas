# Session status

Last update: 2026-07-23T23:00Z W-m3-learn — M3 DONE `3ae1f52` (feature `cf851c3` + wrong_item multi-target)

## Project lock
**HARD** Alagoas only.

## Goal
Self-improving matching MVP (`docs/self-improving-matching-plan.md` P0–P4) + staple fetch verification.

## Testing policy (session override)
**Not UI-focused.** Skip full `ui-viewport-qa` matrix / Flutter web matrix / A4–A7 visual ship path for matching work.
**Required:** backend pytest, API/function e2e (TestClient, scripts against local mock and/or live smoke serial), learn_policy/outcome_log unit tests.
**Optional only if path touches Flutter:** minimal `flutter test` for that file — never full viewport suite.

## Phase
**Active** — M0+M1+M2+M3 shipped; next **M4** offline rescore + live smoke; B2-verify not claimed done

## Must-complete
| # | Status |
|---|--------|
| A–K prior | **DONE** |
| **M0** match_rules_version + baseline | **DONE** `5a16961` W-m0-m1 |
| **M1** outcome log | **DONE** `5a16961` W-m0-m1 |
| **M2** auto_label | **DONE** `56ff4a5` W-m2-label — report `worker_w_m2_label_report.md` |
| **M3** learn_policy v2 | **DONE** `3ae1f52` (feature `cf851c3`) W-m3-learn — report `worker_w_m3_learn_report.md` |
| **M4** offline rescore + live smoke scripts | **QUEUED** next |
| **B2-verify** staple warm/fetch smoke | **IN_PROGRESS / not claimed** — probes may exist as untracked JSON; do not mark DONE without report |
| Commit `docs/self-improving-matching-plan.md` | **DONE** in `5a16961` |

## Workers
| ID | Task |
|----|------|
| W-m0-m1 | **DONE** `5a16961` — report `worker_w_m0_m1_report.md` |
| W-m2-label | **DONE** `56ff4a5` — Phase 2 auto_label; report `worker_w_m2_label_report.md` |
| W-m3-learn | **DONE** `3ae1f52` — Phase 3 learn_policy v2; report `worker_w_m3_learn_report.md` |
| W-b2-verify | serial live staple probes — leave status alone until report lands |

## Residual
- Head weak tops; honest-100; plan P5–P7 later
- B2 warm p95 / fetch_fail vs baseline after probes complete

## Next focus
- Spawn **M4** (offline rescore + serial live smoke scripts)
- When B2 probes JSON is complete → write `worker_w_b2_verify_report.md` + close or hard-block with evidence
