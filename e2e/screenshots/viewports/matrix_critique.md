# Matrix PNG critiques

Authority: `e2e/qa_success_criteria.json` + `e2e/qa_matrix.json`.
Reviewer: **W-matrix-fix** · Artifacts re-captured 2026-07-17 after `matrix_capture.js` true-state fix.
Method: open PNGs (image tool) across formats×screens; map size/hash checks; prior A6 open_bads as baseline.
**CAPTURE_OK alone is not A7.** Filename ≠ screen state proof.

## Capture fix summary
- Mock geolocation (CDP + navigator stub) so search leaves "Iniciando busca…"
- Absolute layout clicks (chips/field/⋮/VER PREÇOS); no multi-click that pops EDITAR LISTA
- Settings opened from home AppBar ⋮ → Configurações sheet
- Wait for `/api/v1/search` stream finish before results/map/share shots
- Landscape: keyboard add (chips below fold); APP_PORT avoids wrong app on :8080

## CRITIQUE lines (147)

```text
CRITIQUE phone_android_01_home: GOOD: search field + VER PREÇOS + brand; chips/list layout readable | BAD: none
CRITIQUE phone_android_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE phone_android_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_android_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_android_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE phone_android_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE phone_android_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE phone_android_landscape_01_home: GOOD: search field + VER PREÇOS + brand | BAD: V-CLIP-TEXT: staple chip row clipped/pushed under short PhoneLandscape height (field+banner fill viewport)
CRITIQUE phone_android_landscape_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: V-CLIP-TEXT: short landscape may crop store cards below fold (savings+COMPARTILHAR visible)
CRITIQUE phone_android_landscape_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_android_landscape_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_android_landscape_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: V-CLIP-TEXT: short landscape share cell shows savings CTA; store list may be below fold
CRITIQUE phone_android_landscape_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE phone_android_landscape_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE phone_portrait_01_home: GOOD: search field + VER PREÇOS + brand; chips/list layout readable | BAD: none
CRITIQUE phone_portrait_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE phone_portrait_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_portrait_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_portrait_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE phone_portrait_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE phone_portrait_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE phone_landscape_01_home: GOOD: search field + VER PREÇOS + brand | BAD: V-CLIP-TEXT: staple chip row clipped/pushed under short PhoneLandscape height (field+banner fill viewport)
CRITIQUE phone_landscape_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: V-CLIP-TEXT: short landscape may crop store cards below fold (savings+COMPARTILHAR visible)
CRITIQUE phone_landscape_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_landscape_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_landscape_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: V-CLIP-TEXT: short landscape share cell shows savings CTA; store list may be below fold
CRITIQUE phone_landscape_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE phone_landscape_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE phone_large_01_home: GOOD: search field + VER PREÇOS + brand; chips/list layout readable | BAD: none
CRITIQUE phone_large_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE phone_large_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_large_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_large_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE phone_large_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE phone_large_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE phone_iphone_promax_01_home: GOOD: search field + VER PREÇOS + brand; chips/list layout readable | BAD: none
CRITIQUE phone_iphone_promax_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE phone_iphone_promax_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_iphone_promax_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_iphone_promax_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE phone_iphone_promax_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE phone_iphone_promax_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE phone_iphone_promax_landscape_01_home: GOOD: search field + VER PREÇOS + brand | BAD: V-CLIP-TEXT: staple chip row clipped/pushed under short PhoneLandscape height (field+banner fill viewport)
CRITIQUE phone_iphone_promax_landscape_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: V-CLIP-TEXT: short landscape may crop store cards below fold (savings+COMPARTILHAR visible)
CRITIQUE phone_iphone_promax_landscape_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_iphone_promax_landscape_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_iphone_promax_landscape_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: V-CLIP-TEXT: short landscape share cell shows savings CTA; store list may be below fold
CRITIQUE phone_iphone_promax_landscape_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE phone_iphone_promax_landscape_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE phone_samsung_ultra_01_home: GOOD: search field + VER PREÇOS + brand; chips/list layout readable | BAD: none
CRITIQUE phone_samsung_ultra_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE phone_samsung_ultra_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_samsung_ultra_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_samsung_ultra_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE phone_samsung_ultra_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE phone_samsung_ultra_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE phone_samsung_ultra_landscape_01_home: GOOD: search field + VER PREÇOS + brand | BAD: V-CLIP-TEXT: staple chip row clipped/pushed under short PhoneLandscape height (field+banner fill viewport)
CRITIQUE phone_samsung_ultra_landscape_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: V-CLIP-TEXT: short landscape may crop store cards below fold (savings+COMPARTILHAR visible)
CRITIQUE phone_samsung_ultra_landscape_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_samsung_ultra_landscape_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_samsung_ultra_landscape_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: V-CLIP-TEXT: short landscape share cell shows savings CTA; store list may be below fold
CRITIQUE phone_samsung_ultra_landscape_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE phone_samsung_ultra_landscape_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE phone_rodin_01_home: GOOD: search field + VER PREÇOS + brand; chips/list layout readable | BAD: none
CRITIQUE phone_rodin_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE phone_rodin_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_rodin_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_rodin_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE phone_rodin_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE phone_rodin_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE phone_rodin_chrome_01_home: GOOD: search field + VER PREÇOS + brand; chips/list layout readable | BAD: none
CRITIQUE phone_rodin_chrome_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE phone_rodin_chrome_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_rodin_chrome_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_rodin_chrome_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE phone_rodin_chrome_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE phone_rodin_chrome_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE phone_rodin_landscape_01_home: GOOD: search field + VER PREÇOS + brand | BAD: V-CLIP-TEXT: staple chip row clipped/pushed under short PhoneLandscape height (field+banner fill viewport)
CRITIQUE phone_rodin_landscape_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: V-CLIP-TEXT: short landscape may crop store cards below fold (savings+COMPARTILHAR visible)
CRITIQUE phone_rodin_landscape_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_rodin_landscape_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_rodin_landscape_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: V-CLIP-TEXT: short landscape share cell shows savings CTA; store list may be below fold
CRITIQUE phone_rodin_landscape_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE phone_rodin_landscape_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE tablet_portrait_01_home: GOOD: search field + VER PREÇOS + brand; chips/list layout readable | BAD: none
CRITIQUE tablet_portrait_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE tablet_portrait_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE tablet_portrait_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE tablet_portrait_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE tablet_portrait_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE tablet_portrait_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE tablet_landscape_01_home: GOOD: search field + VER PREÇOS + brand; chips/list layout readable | BAD: none
CRITIQUE tablet_landscape_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE tablet_landscape_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE tablet_landscape_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE tablet_landscape_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE tablet_landscape_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE tablet_landscape_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE tablet_large_portrait_01_home: GOOD: search field + VER PREÇOS + brand; chips/list layout readable | BAD: none
CRITIQUE tablet_large_portrait_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE tablet_large_portrait_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE tablet_large_portrait_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE tablet_large_portrait_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE tablet_large_portrait_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE tablet_large_portrait_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE laptop_hd_01_home: GOOD: search field + VER PREÇOS + brand; chips/list layout readable | BAD: none
CRITIQUE laptop_hd_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE laptop_hd_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE laptop_hd_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE laptop_hd_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE laptop_hd_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE laptop_hd_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE laptop_scaled_01_home: GOOD: search field + VER PREÇOS + brand; chips/list layout readable | BAD: none
CRITIQUE laptop_scaled_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE laptop_scaled_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE laptop_scaled_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE laptop_scaled_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE laptop_scaled_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE laptop_scaled_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE laptop_720_01_home: GOOD: search field + VER PREÇOS + brand; chips/list layout readable | BAD: none
CRITIQUE laptop_720_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE laptop_720_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE laptop_720_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE laptop_720_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE laptop_720_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE laptop_720_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE 1080p_01_home: GOOD: search field + VER PREÇOS + brand; chips/list layout readable | BAD: none
CRITIQUE 1080p_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE 1080p_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE 1080p_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE 1080p_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE 1080p_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE 1080p_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE qhd_01_home: GOOD: search field + VER PREÇOS + brand | BAD: V-FORM-FACTOR: large empty canvas / sparse chrome on QHD-4K class (usable)
CRITIQUE qhd_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE qhd_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE qhd_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE qhd_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE qhd_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: V-FORM-FACTOR: tiny card in large QHD/4K canvas (usable)
CRITIQUE qhd_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE 4k_01_home: GOOD: search field + VER PREÇOS + brand | BAD: V-FORM-FACTOR: large empty canvas / sparse chrome on QHD-4K class (usable)
CRITIQUE 4k_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE 4k_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE 4k_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE 4k_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE 4k_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: V-FORM-FACTOR: tiny card in large QHD/4K canvas (usable)
CRITIQUE 4k_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
```

## open_bads_matrix = 19

| cell | residual |
|------|----------|
| `phone_android_landscape_01_home` | V-CLIP-TEXT: staple chip row clipped/pushed under short PhoneLandscape height (f |
| `phone_android_landscape_02_results` | V-CLIP-TEXT: short landscape may crop store cards below fold (savings+COMPARTILH |
| `phone_android_landscape_05_share` | V-CLIP-TEXT: short landscape share cell shows savings CTA; store list may be bel |
| `phone_landscape_01_home` | V-CLIP-TEXT: staple chip row clipped/pushed under short PhoneLandscape height (f |
| `phone_landscape_02_results` | V-CLIP-TEXT: short landscape may crop store cards below fold (savings+COMPARTILH |
| `phone_landscape_05_share` | V-CLIP-TEXT: short landscape share cell shows savings CTA; store list may be bel |
| `phone_iphone_promax_landscape_01_home` | V-CLIP-TEXT: staple chip row clipped/pushed under short PhoneLandscape height (f |
| `phone_iphone_promax_landscape_02_results` | V-CLIP-TEXT: short landscape may crop store cards below fold (savings+COMPARTILH |
| `phone_iphone_promax_landscape_05_share` | V-CLIP-TEXT: short landscape share cell shows savings CTA; store list may be bel |
| `phone_samsung_ultra_landscape_01_home` | V-CLIP-TEXT: staple chip row clipped/pushed under short PhoneLandscape height (f |
| `phone_samsung_ultra_landscape_02_results` | V-CLIP-TEXT: short landscape may crop store cards below fold (savings+COMPARTILH |
| `phone_samsung_ultra_landscape_05_share` | V-CLIP-TEXT: short landscape share cell shows savings CTA; store list may be bel |
| `phone_rodin_landscape_01_home` | V-CLIP-TEXT: staple chip row clipped/pushed under short PhoneLandscape height (f |
| `phone_rodin_landscape_02_results` | V-CLIP-TEXT: short landscape may crop store cards below fold (savings+COMPARTILH |
| `phone_rodin_landscape_05_share` | V-CLIP-TEXT: short landscape share cell shows savings CTA; store list may be bel |
| `qhd_01_home` | V-FORM-FACTOR: large empty canvas / sparse chrome on QHD-4K class (usable) |
| `qhd_06_admin` | V-FORM-FACTOR: tiny card in large QHD/4K canvas (usable) |
| `4k_01_home` | V-FORM-FACTOR: large empty canvas / sparse chrome on QHD-4K class (usable) |
| `4k_06_admin` | V-FORM-FACTOR: tiny card in large QHD/4K canvas (usable) |

### Residual product notes (not capture)
- **V-CLIP-TEXT** on PhoneLandscape home/results: short CSS height (~360–440) — product layout residual
- **V-FORM-FACTOR** on QHD/4K home/admin: sparse large canvas — product residual
- Capture path now reaches true states for results/map/settings/share on all 21 formats

