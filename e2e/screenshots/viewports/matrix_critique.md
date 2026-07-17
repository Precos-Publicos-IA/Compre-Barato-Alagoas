# Matrix PNG critiques

Authority: `e2e/qa_success_criteria.json`.  
Run: **2026-07-17** W2 `npm run matrix:local` (prioritized subset — not full 147).  
Capture: `e2e/matrix_capture.js` → `screenshots/viewports/{format}_{shot_suffix}.png`.  
Formats: `phone_portrait`, `phone_android`, `laptop_hd`, `1080p`. Surfaces: admin login, docs home, API `/health` document. Flutter `01_home` skipped (no `frontend/build/web`, no APP_URL).

Every line below was written after opening **this-run** PNGs with the image tool and walking `review_checklist_by_screen` for admin/docs (api_health is supplemental document capture).

```text
CRITIQUE phone_portrait_06_admin: GOOD: login gate centered; Admin panel title, token field, Sign in CTA readable; phone form factor | BAD: none
CRITIQUE phone_portrait_07_docs: GOOD: brand logo+title, mobile nav sections (Overview…User feedback) readable; not blank | BAD: none
CRITIQUE phone_portrait_api_health: GOOD: JSON status=ok development mock flags visible at top | BAD: none
CRITIQUE phone_android_06_admin: GOOD: same admin gate at 360×800; token+Sign in unclipped | BAD: none
CRITIQUE phone_android_07_docs: GOOD: brand + stacked docs nav readable on Android CSS viewport | BAD: none
CRITIQUE phone_android_api_health: GOOD: health JSON status=ok readable | BAD: none
CRITIQUE laptop_hd_06_admin: GOOD: desktop admin gate (not tablet chrome); V-ADMIN-GATE; text crisp at 1366×768 | BAD: none
CRITIQUE laptop_hd_07_docs: GOOD: sidebar brand+nav + Overview body; V-DOCS-NAV; laptop_hd not misclassified as tablet | BAD: none
CRITIQUE laptop_hd_api_health: GOOD: health JSON single line status=ok | BAD: none
CRITIQUE 1080p_06_admin: GOOD: full-HD admin login gate; panel in viewport; V-ADMIN-GATE | BAD: none
CRITIQUE 1080p_07_docs: GOOD: full sidebar + Overview/The problem body; links/callouts readable | BAD: none
CRITIQUE 1080p_api_health: GOOD: health JSON status=ok on dark document | BAD: none
```

### Coverage note (honest residual)

| Scope | Status |
|-------|--------|
| Priority 4 formats × admin/docs/api | **12 cells captured + reviewed** |
| Full `expected_cells` 147 | **Not complete** — expand via `MATRIX_FORMATS=all` + more `MATRIX_SCREENS` + Flutter web for `01_home`–`05_share` |
| Flutter app screens (home/results/map/settings/share) | **Not in this run** — needs `flutter build web` + APP_URL |
| Handheld ship path | Chrome viewport only (layout assist). Phase A handheld ship still requires Android emulator + adb per skill |

`A-MATRIX-COMPLETE` for 147 remains open; prioritized path + expansion knobs close the “no multi-format runner” residual as far as practical without inventing empty cells.
