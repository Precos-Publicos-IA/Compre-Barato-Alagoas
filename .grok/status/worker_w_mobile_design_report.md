# W-mobile-design report

**Date:** 2026-07-17  
**Goal:** Serious mobile consumer-app UI (not stock Flutter Material) + phone landscape usability  
**Status:** DONE (local verified; commit below)

## Screens changed

| Surface | Files | What changed |
|---------|-------|--------------|
| Design system | `frontend/lib/core/theme.dart`, `layout.dart`, `staple_icons.dart` | Custom `AppColors` / `AppRadii` / `AppSpacing` (not bare `fromSeed`); typography scale; soft card shadows; short-height / phone-landscape helpers; Material icon map for staples (no emoji tofu) |
| Home / search | `search_screen.dart`, `apk_banner.dart` | Hero + subtitle; elevated search field with + / mic; staple tiles with icons; basket cards; premium bottom CTA with count badge; landscape hides APK banner, compact title “Monte sua lista”, horizontal staple row |
| Results | `results_screen.dart`, `store_card.dart` | Gradient savings hero; dense short-height savings row; gold accent bar + “MAIS BARATO” badge; structured store cards; rewrite banners hidden on short height so winner stays above fold |
| Settings | `settings_sheet.dart` | Card groups, steppers, consistent primary chrome |
| Resilience | `providers.dart` | Offline fallback staples if `/suggestions` fails |
| E2E assist | `e2e/matrix_capture.js` | `homeLayout` + `flutterAddItem` retuned for new chrome (chip/field/+ on short landscape) |

## Before / after (mobile residual)

### Before (open_bads phone-related)
- 15× `V-CLIP-TEXT` phone landscape (home chips / results stores under fold)
- UI looked like generic M3 seed starter (plain AppBar, outline field, emoji ActionChips, flat mint cards)

### After (this-run phone PNGs opened)
| Cell | Verdict |
|------|---------|
| `phone_portrait_01_home` | **PASS** — hero, elevated field, icon staple tiles, muted install strip, CTA |
| `phone_portrait_02_results` | **PASS** — gradient savings, winner gold strip, price hierarchy, actions |
| `phone_landscape_01_home` | **PASS** — chips + field + CTA in first viewport (no APK banner) |
| `phone_landscape_02_results` | **PASS** — dense savings + MAIS BARATO card + EDITAR LISTA; no rewrite clutter |
| `phone_android_landscape_02_results` | **PASS** — same dense layout on 360h |

**Residual mobile V-CLIP-TEXT:** cleared for reviewed phone landscape cells (home chips + results winner/CTA).  
**Not in scope this ship:** QHD/4K `V-FORM-FACTOR` (desktop sparsity) — left as-is per user mobile focus.

## Verification

- `flutter test` → **66/66 green**
- `flutter build web --release` → **OK** (production `API_BASE_URL` default)
- Matrix phone subset capture (portrait + landscape home/results/share) → CAPTURE_OK with results settle on landscape after e2e layout retune
- Labels preserved: `VER PREÇOS`, `EDITAR LISTA`, `MAIS BARATO`, `COMPARTILHAR ECONOMIA`

## Screenshot paths (this-run)

```
e2e/screenshots/viewports/phone_portrait_01_home.png
e2e/screenshots/viewports/phone_portrait_02_results.png
e2e/screenshots/viewports/phone_landscape_01_home.png
e2e/screenshots/viewports/phone_landscape_02_results.png
e2e/screenshots/viewports/phone_android_01_home.png
e2e/screenshots/viewports/phone_android_02_results.png
e2e/screenshots/viewports/phone_android_landscape_01_home.png
e2e/screenshots/viewports/phone_android_landscape_02_results.png
```

## Commit

- **SHA:** `d2497c1580392869a53e76c0bb5428a7b47efd53` (`d2497c1`)
- **Branch:** `main` (pushed)
- **Message:** feat(ui): serious mobile product design for Compre Barato

## Follow-ups (optional, not blocking mobile ship)

- Broader handheld re-capture (promax/ultra/rodin landscape) for full A6 table refresh
- Desktop QHD/4k form-factor residual still open (user deprioritized)
- Some staple Material glyphs are approximate (e.g. feijão/óleos); fine for no-tofu, can refine later
