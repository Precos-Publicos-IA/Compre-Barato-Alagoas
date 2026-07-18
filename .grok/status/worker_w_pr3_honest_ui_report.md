# W-pr3 report — honest partial-basket hero & savings gate (PR3)

**Worker:** W-pr3  
**Date:** 2026-07-18  
**Plan:** `docs/improvement-plan-search-quality.md` W2.1–W2.5 / PR3  
**Status:** DONE (committed on `main`)

## Problem

Phone re-eval showed **“Economize até R$ 5,64”** while only **4/10** items had prices — overconfident primary savings on an incomplete basket.

## Change summary

| Area | What |
|------|------|
| `frontend/lib/features/results/savings.dart` | `BasketCoverage`, `computeCoverage`, `shouldShowPrimarySavings`, threshold **0.7** (`kPrimarySavingsCoverageThreshold`) |
| `frontend/lib/features/results/results_screen.dart` | Coverage-first hero: primary `_SavingsBanner` only when gate passes; else `_PartialCoverageBanner` (“Encontramos N de M…”) + share without R$ claim |
| `frontend/test/share_savings_test.dart` | Unit tests for coverage gate + phone 4/10 case |

### Gate rules

Primary “economize R$” hero **and** “COMPARTILHAR ECONOMIA” (with savings amount) only when:

1. `savings.amount > 0`, **and**
2. best-store coverage is **complete** (`found >= total`) **or** `found/total ≥ 0.7`

Otherwise:

- Hero: **“Encontramos N de M itens”** + “Compare só o que tem preço…”
- Share: **“COMPARTILHAR BUSCA”** with generic message (`savings = 0` → no “desconto de R$”)
- Store cards: existing “Faltam …” / missing chips unchanged

Copy/logic only — no visual system redesign.

## Tests (scoped)

```bash
cd frontend && flutter test test/share_savings_test.dart test/search_flow_test.dart
```

**Result:** all passed (18 tests).

Not run (per operator HARD): full UI matrix, `e2e full:local`, whole-app suites.

## Acceptance

| Criterion | Result |
|-----------|--------|
| Partial coverage no longer primary “Você pode economizar até R$…” | **PASS** — `shouldShowPrimarySavings` false for 4/10 even with R$ delta |
| Full / ≥70% still can show savings | **PASS** — 10/10 and 7/10 allow |
| Commit on main | **PASS** `65a7189` |
| No PR1 rework / catalog API / matrix | **honored** |

## Files touched

- `frontend/lib/features/results/savings.dart`
- `frontend/lib/features/results/results_screen.dart`
- `frontend/test/share_savings_test.dart`
- `.grok/status/session.md`
- `.grok/status/worker_w_pr3_honest_ui_report.md`
