# W-home-recapture report

**Date:** 2026-07-17  
**Task:** Close must-complete #1 residual — QHD/4K home V-FORM recapture  
**Result:** **HARD-BLOCK** re-documented with fresh probe + recapture evidence (not honest PASS)

## Stack confirmed
- API `http://127.0.0.1:8000` → 200
- App serve `python3 -m http.server 18090` → `frontend/build/web` (NOT 8080)
- Rebuild: `flutter build web --release --dart-define=API_BASE_URL=http://127.0.0.1:8000` (clean rebuild also tried)

## Capture run
```bash
cd e2e
BUILD_WEB=0 CONCURRENCY=1 MATRIX_FORMATS=qhd,4k MATRIX_SCREENS=home \
APP_URL=http://127.0.0.1:18090 APP_PORT=18090 RECORD_VIDEO=0 \
bash run_matrix_local.sh
```
- Exit 0 CAPTURE_OK: `qhd_01_home` 21898b, `4k_01_home` 41588b
- CAPTURE_OK ≠ visual pass (`waitFlutter` accepts empty `flt-glass-pane`)

## Vision / pixel review
| cell | dims | size | white% | opened |
|------|------|------|--------|--------|
| qhd_01_home | 2560×1440 | 21898b | 98.9% | splash bar only (VER PREÇOS); no SearchScreen |
| 4k_01_home | 3840×2160 | 41588b | 99.0% | same splash-only |

## CanvasKit probes (honest retries)
| attempt | result |
|---------|--------|
| QHD headless Chrome 121 + SwiftShader (qemu UP ~285% CPU) | glass children=0, canvas=0; WebGL context thrash / intermittent `LateInitializationError` |
| Matrix recapture qemu UP | CAPTURE_OK splash stills |
| **Kill** friends AVD qemu (`adb emu kill` + `kill` pid 171356) | qemu DOWN |
| Re-probe after kill (swiftshader/egl/desktop-gpu/disable-gpu, headed Chrome 150) | still no first frame; WebGL MakeWebGLCanvasSurface **OK**; flutterCanvasKit true |
| Live HTTPS headless | same empty glass |
| Clean flutter rebuild + re-serve | no change |

### Probe invariants (local release on :18090)
- `flutter-view` present, `flt-glass-pane` **empty** (no scene host)
- `document.querySelectorAll('canvas').length === 0`
- `window._flutterFirstFrame === false` for 30–60s+
- Assets 200: main.dart.js, canvaskit.js/wasm (gstatic chromium variant), fonts, AssetManifest

## Emulator
- Stopped friends AVD for GPU headroom; **restart not required** for this task.
- Did not kill foreign trees (Rusty Dasher :8080 left alone).

## Artifacts updated
- `e2e/screenshots/viewports/matrix_critique.md` — home cells HARD-BLOCK fresh notes
- `e2e/screenshots/viewports/qhd_01_home.review.json`, `4k_01_home.review.json`
- `.grok/status/a6_open_bads.txt`
- `.grok/status/session.md` — #1 HARD-BLOCK
- Splash-class PNGs left in place (honest fail evidence; not claimed PASS)

## open_bads
```
open_bads_matrix = 2 (hard-block)
qhd_01_home
4k_01_home
```
Completable agent work on #1 is exhausted until host/environment paints Flutter CanvasKit first frame under Chrome again.

## Code note (unchanged)
Layout fix remains valid from `77c58a5` / widget tests; this residual is **capture-environment**, not missing contentMaxWidth code.
