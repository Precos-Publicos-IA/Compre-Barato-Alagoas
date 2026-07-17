# Autonomous dev cycle (imported)

Synced from 1st-rust-game + vinys-toolbelt: multi-role R1→R3, full-matrix-only residual, hardware-integrity orchestrator.

## Layout

| Path | Role |
|------|------|
| `skills/ui-viewport-qa/SKILL.md` | Process A/B/C (Alagoas stack + baseline vs matrix) |
| `skills/app-input-e2e/SKILL.md` | Input rules |
| `skills/orchestrator-loop/SKILL.md` | Orchestrator |
| `prompts/orchestrator-loop.md` | `/loop` paste |
| `status/session.md` | Live status |

| Path | Role |
|------|------|
| `e2e/qa_matrix.json` | Screens × formats (`expected_cells` 147 = full matrix target) |
| **`e2e/qa_success_criteria.json`** | **PASS/FAIL** |
| `e2e/screenshots/**/*_critique.md` | Critiques |

## Alagoas reality (read with skill)

- **Product UI is Flutter** (`frontend/`) — keep `flutter test` / `flutter build web` in A1/A2. Host may need Flutter SDK installed.
- **Baseline ship bar:** `npm run full:local` + post-deploy `npm run live` + criteria critiques (not suite exit 0 alone).
- **Full 147-cell matrix** is **aspirational** until multi-format runners land; document residual; review any `matrix:local` subset when present.

## Source note

Toolbelt `qa_success_criteria.json` (game) → adapted product criteria for Alagoas
screens. Process/order from `ui-viewport-qa` kept with VPS/Flutter path mapping.
