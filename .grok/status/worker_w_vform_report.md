# W-vform report — QHD/4K V-FORM-FACTOR

**Date:** 2026-07-17  
**Worker:** W-vform  
**Outcome:** admin BADs **closed** (2); home BADs **hard-blocked** (2) with evidence

## Code shipped

| File | Change |
|------|--------|
| `frontend/lib/core/layout.dart` | `contentMaxWidth`: QHD `(w*0.52).clamp(1180,1560)`; 4K `(w*0.48).clamp(1400,1920)` |
| `frontend/lib/features/search/search_screen.dart` | Desktop4k elevated product shell + `_DesktopTipsCard` + larger headline |
| `admin-frontend/styles.css` | Login card `clamp` width/type + min-width 2400 frame/glow |
| `frontend/web/index.html` | `flutter-view` / `flt-glass-pane` full-viewport CSS host |
| `frontend/test/desktop4k_layout_test.dart` | Asserts contentMaxWidth + QHD SearchScreen paints tips/headline |

## Tests
- `flutter test` — **all green** (68 tests incl. desktop4k layout)

## Capture / review

### Admin (CLOSED)
- Recapture `MATRIX_FORMATS=qhd,4k MATRIX_SCREENS=home,admin CONCURRENCY=1` with local stack
- Opened:
  - `e2e/screenshots/viewports/qhd_06_admin.png` — large framed card + glow, not postage stamp
  - `e2e/screenshots/viewports/4k_06_admin.png` — same, intentional gate chrome
- Sidecars: `qhd_06_admin.review.json`, `4k_06_admin.review.json` (`verdict: all_good`)
- Critique: `BAD: none` for both admin cells

### Home (HARD-BLOCK)
- Code + widget tests prove wider column + shell/tips at QHD/4K
- **Cannot honest-recapture product pixels:** headless Chrome reports `flutter-first-frame` but `flt-glass-pane` stays **empty** (no `flt-scene-host`, `canvas` count 0)
- Reproduced on:
  - local `APP_URL` (python/http.server + node static + HTTPS self-signed)
  - **live** `https://alagoas.precospublicos.ia.br/` under same headless
- Host evidence: `qemu-system-x86_64 -avd friends -gpu host` ~**265% CPU** during session (GPU thrash)
- Screenshots collapse to white + ghost outline CTA only (~22KB QHD / ~41KB 4K) — not valid layout proof

## open_bads_matrix
- **Before:** 4  
- **After:** **2 hard-block** (`qhd_01_home`, `4k_01_home`)  
- **Completable admin residual:** **0**

## Unblock home
1. Stop/pause host GPU-heavy emulator (or free GPU)
2. Confirm headless CanvasKit paints scene host (glass kids > 0)
3. `BUILD_WEB=0 CONCURRENCY=1 MATRIX_FORMATS=qhd,4k MATRIX_SCREENS=home bash e2e/run_matrix_local.sh`
4. Open PNGs → critique `BAD: none` → open_bads 0

## Not done
- Home pixel proof of V-FORM fix (environment)
- Full Phase A7 ship claim (2 hard-block remain)
