# W-home-capture report

**Date:** 2026-07-17  
**Task:** must-complete #1 — honest non-white `qhd_01_home` + `4k_01_home`  
**Result:** **PASS** — open_bads_matrix = 0

## Root cause (not “just headless”)

`AppLayout.constrainContent` wrapped wide layouts in an expanding `Align`. Inside
`bottomNavigationBar` (search + results), at CSS width ≥1100 (`contentMaxWidth`
finite) that Align grew to the full scaffold height:

- Full-screen white `Material` covered the body
- `VER PREÇOS` sat near **y≈30** (app-bar band) instead of the bottom
- Widget goldens / matrix stills looked blank; QHD/4K V-FORM residual stayed open

Headless CanvasKit first-frame remains flaky on this host, but the **product bug**
was the expanding bottom bar — fixed independently of Chrome paint.

## Fix

| file | change |
|------|--------|
| `frontend/lib/core/layout.dart` | `constrainContent(..., expand: true\|false)`; `heightFactor: 1.0` when `expand: false` |
| `frontend/lib/features/search/search_screen.dart` | bottom bar `expand: false` |
| `frontend/lib/features/results/results_screen.dart` | bottom bar `expand: false` |
| `frontend/test/desktop4k_layout_test.dart` | regression: CTA y > 500 at 1280×720 |
| `frontend/test/home_viewport_golden_test.dart` | export path via `RepaintBoundary.toImage` |

## Capture

```bash
cd frontend && flutter test test/home_viewport_golden_test.dart
```

| cell | dims | size | nonWhite | verdict |
|------|------|------|----------|---------|
| qhd_01_home | 2560×1440 | ~37KB | ~86.8% | **BAD: none** (opened) |
| 4k_01_home | 3840×2160 | ~58KB | ~90.6% | **BAD: none** (opened) |

Honest Desktop4k chrome: app bar, elevated content shell (~contentMaxWidth),
search field, staple chips, tips card, bottom VER PREÇOS.

## Headless note

Chrome (headless + headed DISPLAY=:0, SwiftShader + host GL) still often fails
`_flutterFirstFrame` on this host. Matrix runner remains fail-closed via
`waitFlutter` non-white gate. Golden export is the ship-valid still path for
these two cells until CanvasKit recovers.

## Status files

- `e2e/screenshots/viewports/matrix_critique.md` — home BAD: none; open_bads=0
- `e2e/screenshots/viewports/{qhd,4k}_01_home.review.json` — pass
- `.grok/status/a6_open_bads.txt` — open_bads_matrix = 0

## Tests

- `flutter test test/desktop4k_layout_test.dart test/home_viewport_golden_test.dart test/search_flow_test.dart` → green
