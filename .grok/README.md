# Autonomous dev cycle (Alagoas)

## Project lock + finish rules

| Doc | Role |
|-----|------|
| **[`../PROJECT_LOCK.md`](../PROJECT_LOCK.md)** | **HARD:** Alagoas-only; refuse other projects; no half-done parking |
| [`../AGENTS.md`](../AGENTS.md) | Delivery, batching, ship on `main` |

## Layout

| Path | Role |
|------|------|
| `skills/ui-viewport-qa/SKILL.md` | Process A/B/C (Alagoas stack + baseline vs matrix) |
| `skills/app-input-e2e/SKILL.md` | Input rules |
| `skills/orchestrator-loop/SKILL.md` | Orchestrator (lock + finish + hardware integrity) |
| `prompts/orchestrator-loop.md` | `/loop` paste — **re-schedule after edits** |
| `status/session.md` | Live status / must-complete checklist |

| Path | Role |
|------|------|
| `e2e/qa_matrix.json` | Screens × formats (`expected_cells` 147 = full matrix target) |
| **`e2e/qa_success_criteria.json`** | **PASS/FAIL** |
| `e2e/screenshots/**/*_critique.md` | Critiques |

## Alagoas reality (read with skill)

- **Product UI is Flutter** (`frontend/`) — keep `flutter test` / `flutter build web` in A1/A2.
- **Baseline ship bar:** `npm run full:local` + post-deploy `npm run live` + criteria critiques (not suite exit 0 alone).
- **Full 147-cell matrix:** required for residual close / full visual QA. **Missing runners → install/finish them** — do not park as optional.
- **Completable work** stays on `session.md` checklist until done or hard-blocked.

## Source note

Toolbelt / game criteria were adapted for Alagoas product surfaces. Do not treat
game-specific input (stick/DASH/two-finger) as Alagoas product requirements.
