# W-A6 report — matrix PNG review

**Date:** 2026-07-17  
**Worker:** W-A6  
**Authority:** `e2e/qa_success_criteria.json` + `e2e/qa_matrix.json`  
**Artifact:** `e2e/screenshots/viewports/matrix_critique.md`

## Counts

| Metric | Value |
|--------|-------|
| expected_cells | **147** |
| PNGs present non-empty | **147** / 147 |
| CRITIQUE lines written | **147** / 147 |
| BAD: none | **69** |
| **open_bads** | **78** |
| api_health extras | 4 (optional; not in expected_cells) |

## open_bads (78) — by criterion (co-occurring ok)

| Criterion | Approx lines citing |
|-----------|---------------------|
| V-STATE-MATCH | ~72 |
| V-SETTINGS-TOGGLES | 21 (all formats) |
| V-RESULTS-PRICES | ~19 |
| V-MAP-USABLE | ~17 |
| V-SHARE-CTA | ~15 |
| V-CLIP-TEXT | 2 (landscape chip rows) |
| V-FORM-FACTOR | 4 (QHD/4K sparse home/admin) |

Full list: `.grok/status/a6_open_bads.txt`

## Sample evidence (opened pixels)

### GOOD examples
- `phone_android_03_map` / `phone_portrait_03_map` / `phone_rodin_03_map`: **Mapa das lojas** + price pins (R$).
- `phone_android_05_share` / `phone_portrait_05_share` / `laptop_hd_02_results`: savings card + **COMPARTILHAR ECONOMIA** + ranked store prices.
- `*_06_admin` (all 21): Admin panel token + Sign in gate.
- `*_07_docs` (all 21): brand + nav (mobile stack or desktop sidebar).
- Most `*_01_home`: search field + **VER PREÇOS**.

### BAD examples (not rubber-stamp)
- `phone_android_02_results`, `phone_portrait_02_results`, `1080p_02_results`, `laptop_720_02_results`: spinner **Iniciando busca…** only → **V-RESULTS-PRICES** + **V-STATE-MATCH**.
- `phone_android_04_settings`, `tablet_portrait_04_settings`, `laptop_hd_04_settings`, all other settings: **home search** UI → **V-STATE-MATCH** + **V-SETTINGS-TOGGLES**.
- `laptop_hd_03_map`, `phone_iphone_promax_03_map`: results/share list labeled map → **V-MAP-USABLE**.
- `phone_landscape_01_home` / `phone_android_landscape_01_home`: short landscape clips staple chips → **V-CLIP-TEXT**.
- `4k_02_results`…`4k_05_share` **identical hash to `4k_01_home`** → mass **V-STATE-MATCH**.
- `qhd_02`…`05` identical home-with-list → same class.

## Method
1. Opened criteria + matrix JSON; confirmed 21 formats × 7 screens = 147.
2. Verified 147 PNGs on disk non-empty; mapped MD5 identical groups.
3. Opened representative PNGs with image tool across every format class and every screen id (home/results/map/settings/share/admin/docs); propagated judgments to identical-hash siblings and same-pattern formats after spot-check.
4. Wrote one CRITIQUE line per cell with GOOD + BAD (criterion ids when failing).

## A7 implication
**PRE-PROD REVIEW cannot PASS** while 78 open_bads remain (many blocker/major: V-STATE-MATCH, V-RESULTS-PRICES, V-MAP-USABLE, V-SETTINGS-TOGGLES).  
Next: fix capture quality-holds / navigation (results settle, open map, open settings sheet, share path) → re-capture failed cells → re-A6. Do **not** invent BAD: none.

## Conflict note
Only W-A6 wrote `matrix_critique.md`. Did not touch `video_critique.md` (W-A4b).
