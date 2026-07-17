# W-matrix-fix report

**Date:** 2026-07-17  
**Worker:** W-matrix-fix  
**Scope:** `e2e/matrix_capture.js` + re-capture + re-critique (matrix + video)

## Before → after

| Metric | Before (A6/A4b) | After |
|--------|-----------------|-------|
| open_bads_matrix | **78** | **19** |
| open_bads_video | **4** | **0** |
| CAPTURE_OK cells | 147/147 | 147/147 |
| Dominant FAIL | V-STATE-MATCH ~72 | residual product only |

### Before pattern
Capture labeled wrong screens: settings/map/share often home; results spinner-only; 4k/qhd identical home hashes; videos hung on "Iniciando busca…" or truncated ~2s.

### After
All 21 formats reach **true states**:
- results: prices / savings / ranked stores
- map: Mapa das lojas + pins (multi-100KB–MB PNGs)
- settings: Configurações sheet with steppers + toggle
- share: COMPARTILHAR ECONOMIA
- desktop VIDEO: search→results with R$ prices (laptop_hd/720/qhd/4k/1080p)

## Fixes shipped (`e2e/matrix_capture.js`, `e2e/run_matrix_local.sh`)

1. **Geolocation mock** — CDP grant + `navigator.geolocation` stub (Maceió) so LocationService never freezes on "Iniciando busca…"
2. **Absolute layout hits** — chips ~y=320, field ~y=220, VER PREÇOS near bottom CSS px (not mid-canvas ratios that broke 4k)
3. **Single VER PREÇOS click** — multi-click was navigating results then immediately tapping EDITAR LISTA → home
4. **Settings from home** — ⋮ far-right + Configurações; avoid cloud sheet
5. **Wait for search stream** — listeners before Ver preços; wait `requestfinished` on `/api/v1/search`
6. **Landscape keyboard add** — chips below fold; type+Enter
7. **APP_PORT default 18090** — avoid hijacked :8080 (was serving wrong app "RUSTY DASHER")
8. **Video hold** — longer settle on results so continuous frames show prices

## Residual open_bads_matrix = 19 (product, not capture)

| Criterion | Count | Notes |
|-----------|------:|-------|
| V-CLIP-TEXT | 15 | PhoneLandscape short height: chips / store list below fold |
| V-FORM-FACTOR | 4 | QHD/4K sparse chrome (home/admin) |

No remaining V-STATE-MATCH / V-SETTINGS-TOGGLES / V-RESULTS-PRICES / V-MAP-USABLE / V-SHARE-CTA from wrong capture state.

## open_bads_video = 0

Present desktop `*_mouse.webm` all BAD: none (journey shows prices).  
Still missing: keyboard modality webm, handheld adb Phase A (out of this worker’s ship path unless emulator).

## Artifacts
- `e2e/screenshots/viewports/matrix_critique.md` — 147 CRITIQUE lines
- `e2e/screenshots/web/e2e/video_critique.md` — 6 VIDEO lines
- `.grok/status/a6_open_bads.txt` — 19 residual product rows

## A7
Not zero open_bads_matrix (19 product residuals). Capture quality gate largely cleared; residual V-CLIP-TEXT / V-FORM-FACTOR need product UX or acceptance as class residuals.
