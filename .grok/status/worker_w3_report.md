# Worker W3 report — cycle docs alignment

**Status:** DONE  
**Scope:** docs only (skills + AGENTS + e2e README + `.grok` status)  
**No product feature work. No git push.**

## Goal

Align autonomous-dev-cycle language with Alagoas reality:

1. Flutter **is** the product UI — keep Flutter in A1/A2.
2. A1 requires `flutter test` when `frontend/` changes; host may need Flutter SDK.
3. Full **147-cell** matrix is **aspirational**; baseline ship bar stays
   `full:local` + `live` + criteria critiques; review `matrix:local` subset when present.

## Files touched

| Path | Change |
|------|--------|
| `.grok/skills/ui-viewport-qa/SKILL.md` | Stack map; baseline vs 147 table; A1 SDK note; ship order; Phase A checklist split; A7; commands; fix loop; Do not ship; Phase B push wording |
| `.grok/skills/app-input-e2e/SKILL.md` | A1 Flutter/SDK one-liner + baseline vs matrix pointer |
| `AGENTS.md` | Commit verification + How to run: A1 Flutter, baseline ship bar vs residual |
| `e2e/README.md` | Baseline ship bar vs full matrix table |
| `.grok/README.md` | Alagoas reality blurb (Flutter, baseline, 147 aspirational) |
| `e2e/qa_success_criteria.json` | `agent_instructions` one-line baseline/Flutter note |
| `.grok/status/session.md` | W3 marked DONE |
| `.grok/status/worker_w3_report.md` | This report |

## Decisions recorded

### A1 / Flutter (kept)

- Product UI = Flutter `frontend/`.
- A1 remains **`pytest` + `flutter test`** in the cycle (layer-aware: run for changed layers or full cycle).
- Explicit: **required when `frontend/` changes**.
- Explicit: **host may need Flutter SDK** (`flutter` on PATH); install stable if missing.
- **Do not remove Flutter from A1/A2.**

### Baseline vs full matrix

| Layer | Ship gate today? |
|-------|------------------|
| `npm run full:local` | Yes |
| `npm run live` (post-deploy) | Yes |
| Criteria critiques on this-run artifacts | Yes |
| A1 for changed layers (`flutter test` for frontend) | Yes |
| Any present `matrix:local` / subset cells | Review required for those cells |
| Full 147 (`e2e/qa_matrix.json` `expected_cells`) | **Aspirational residual** until multi-format runners land |

Rules agents must follow:

- CAPTURE_OK ≠ A7.
- Do not invent 147 CRITIQUE lines without pixels.
- Do not drop baseline gates because 147 is incomplete.
- When matrix runners land, close residual and require full matrix again.

## Out of scope (other workers)

- W1: install Flutter SDK + run `flutter test` green.
- W2: implement multi-format stills / VIDEO capture + critique lines.

## Verification

- Docs re-read for internal consistency on A1 Flutter retention and baseline/147 split.
- No product code changes.
- No `git push`.
