# Session status

Last update: **W-live-ship DONE** — deploy green + live smoke; **A7 practical PASS** (mobile)

## Goal
~~Clear mobile capture BADs + deploy d2497c1~~ → **DONE**

## Phase
**B SUCCESS** · **A7 practical PASS** for mobile residual close

## Workers
| id | Status |
|----|--------|
| W-mobile-design | DONE `d2497c1` |
| W-re-critique-mobile | DONE open_bads **19→10**; V-CLIP landscape product **0** |
| W-capture-local-api | DONE — 6 API residuals CLEARED |
| **W-live-ship** | **DONE** run **29619545203** success · live stores>0 web |

## Metrics
| Metric | Count |
|--------|------:|
| open_bads_matrix | **4** (desktop V-FORM only) |
| open_bads_video | **0** |
| mobile V-CLIP product | **0** |
| API-capture residuals | **0** |
| CI deploy `d2497c1` | **green** |
| Live search (cold+popular) | **stores=5**, `data_source=web` |

## Residual (accepted A7 practical)
- qhd_01_home · qhd_06_admin · 4k_01_home · 4k_06_admin — V-FORM-FACTOR sparse QHD/4K (usable)

## Thermal
Use **k10temp Tctl** only (not acpitz).

## SEFAZ / prod path
`USE_MOCK_SEFAZ=false` **`USE_WEB_SEFAZ=true`** (official host still broken; token in secrets/)  
API image pin on this deploy: `b6ec7a8…` (frontend-only ship of mobile UI)

## Next (optional)
1. Desktop QHD/4K form polish (4 cells) or leave accepted residual
2. Push local `50f65cb` skill sync if desired
3. Phase C physical phone when device available
4. Re-enable official SEFAZ API when host fixed
