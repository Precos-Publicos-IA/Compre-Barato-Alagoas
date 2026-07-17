# W-capture-local-api report — 2026-07-17

## Mission
Clear **6 open_bads** that were **API capture residuals** (not layout):
- `phone_iphone_promax_landscape_02_results` / `_05_share`
- `phone_samsung_ultra_landscape_02_results` / `_05_share`
- `phone_rodin_landscape_02_results` / `_05_share`

Root cause (re-critique): release `flutter build web` baked **production** `API_BASE_URL=https://alagoas.precospublicos.ia.br`; capture env got ClientException; homes already PASS V-CLIP.

## Actions
1. **Verified** `frontend/build/web/main.dart.js` contained only production host (no `127.0.0.1:8000`).
2. **Rebuilt** Flutter web:
   ```bash
   cd frontend && flutter build web --release \
     --dart-define=API_BASE_URL=http://127.0.0.1:8000 --no-wasm-dry-run
   ```
   Post-build: `main.dart.js` has `http://127.0.0.1:8000` (3 refs).
3. **Stack:** mock SEFAZ already on `:8000` (`use_mock_sefaz:true`); restarted static serve of `frontend/build/web` on **APP_PORT 18090**.
4. **Recapture** (matrix_capture only, RECORD_VIDEO=0):
   ```text
   MATRIX_FORMATS=phone_iphone_promax_landscape,phone_samsung_ultra_landscape,phone_rodin_landscape
   MATRIX_SCREENS=results,share,home
   APP_URL=http://127.0.0.1:18090 API_URL=http://127.0.0.1:8000
   ```
   **CAPTURE_OK 24/24** — all three formats: `results settle stores=true done=true status=200`.

## Visual review (opened each PNG)
| cell | bytes | evidence | verdict |
|------|------:|----------|---------|
| promax_landscape_02_results | 216020 | Economize R$5,26; Atacado Jatiuca **R$22,63**; **COMPARTILHAR ECONOMIA**; EDITAR LISTA | BAD: none |
| promax_landscape_05_share | 216020 | same surface; COMPARTILHAR full | BAD: none |
| samsung_ultra_landscape_02_results | 198854 | prices + COMPARTILHAR | BAD: none |
| samsung_ultra_landscape_05_share | 198854 | COMPARTILHAR full | BAD: none |
| rodin_landscape_02_results | 179986 | prices + COMPARTILHAR | BAD: none |
| rodin_landscape_05_share | 179986 | COMPARTILHAR full | BAD: none |

Previous error-UI PNGs were ~52–55 KB; new settled results ~180–216 KB.

## Artifacts updated
- `e2e/screenshots/viewports/phone_*_{02_results,05_share}.png` (this run)
- `e2e/screenshots/viewports/*.review.json` for the 6 cells (`opened:true`, `verdict:all_good`)
- `e2e/screenshots/viewports/matrix_critique.md` — 6 CRITIQUE lines → `BAD: none`; `open_bads_matrix = 4`
- `.grok/status/a6_open_bads.txt` — only QHD/4K V-FORM residual
- `.grok/status/session.md`

## Metrics
| Metric | Before | After |
|--------|-------:|------:|
| open_bads_matrix | 10 | **4** |
| API-capture residuals | 6 | **0** |
| desktop V-FORM residual | 4 | **4** (unchanged; not fixed) |

## Explicit non-claims
- Did **not** invent PASS without opening PNGs.
- Did **not** clear QHD/4K `V-FORM-FACTOR` residuals.
- Did **not** re-run full 147-cell matrix or video path for these units (RECORD_VIDEO=0; targeted residual close).
- Handled only API-env capture residual; product layout was already proven on android/phone_landscape results.

## Done criteria
**open_bads_matrix = 4 (desktop only)** ✓
