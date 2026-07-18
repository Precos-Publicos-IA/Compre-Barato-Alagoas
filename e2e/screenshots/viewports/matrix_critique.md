# Matrix PNG critiques

Authority: `e2e/qa_success_criteria.json` + `e2e/qa_matrix.json`.
Reviewer: **W-re-critique-mobile** (post `d2497c1`) · Homes re-opened + failing landscapes re-captured 2026-07-17 20:04 against `frontend/build/web`.
Method: open PNGs (image tool) for every prior V-CLIP-TEXT landscape cell + portrait samples; criteria from `e2e/qa_success_criteria.json`.
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
CRITIQUE phone_android_landscape_01_home: GOOD: Monte sua lista + search + staple chips (Arroz…) + VER PREÇOS in first viewport; no APK banner | BAD: none
CRITIQUE phone_android_landscape_02_results: GOOD: dense savings (R$ 5,26) + COMPARTILHAR ECONOMIA + MAIS BARATO card + price R$ 22,63 + EDITAR LISTA; primary prices/CTAs in viewport | BAD: none
CRITIQUE phone_android_landscape_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_android_landscape_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_android_landscape_05_share: GOOD: COMPARTILHAR ECONOMIA + savings + MAIS BARATO price in viewport; V-SHARE-CTA | BAD: none
CRITIQUE phone_android_landscape_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE phone_android_landscape_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE phone_portrait_01_home: GOOD: search field + VER PREÇOS + brand; chips/list layout readable | BAD: none
CRITIQUE phone_portrait_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE phone_portrait_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_portrait_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_portrait_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE phone_portrait_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE phone_portrait_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE phone_landscape_01_home: GOOD: Monte sua lista + search + full staple chip row (incl. Macarrão) + VER PREÇOS; no APK banner | BAD: none
CRITIQUE phone_landscape_02_results: GOOD: dense savings + COMPARTILHAR ECONOMIA + MAIS BARATO Atacado Jatiuca R$ 22,63 + EDITAR LISTA; primary prices/CTAs readable | BAD: none
CRITIQUE phone_landscape_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_landscape_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_landscape_05_share: GOOD: COMPARTILHAR ECONOMIA + savings + store price in viewport; V-SHARE-CTA | BAD: none
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
CRITIQUE phone_iphone_promax_landscape_01_home: GOOD: Monte sua lista + search + staple chips (Arroz–Banana row) + VER PREÇOS in first viewport; no APK banner (post-recapture) | BAD: none
CRITIQUE phone_iphone_promax_landscape_02_results: GOOD: settled results — MAIS BARATO Atacado Jatiuca R$22,63 + Economize banner + COMPARTILHAR ECONOMIA + EDITAR LISTA (local mock API rebuild) | BAD: none
CRITIQUE phone_iphone_promax_landscape_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_iphone_promax_landscape_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_iphone_promax_landscape_05_share: GOOD: COMPARTILHAR ECONOMIA full on savings banner + prices R$22,63 (same results surface; local mock API) | BAD: none
CRITIQUE phone_iphone_promax_landscape_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE phone_iphone_promax_landscape_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE phone_samsung_ultra_01_home: GOOD: search field + VER PREÇOS + brand; chips/list layout readable | BAD: none
CRITIQUE phone_samsung_ultra_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE phone_samsung_ultra_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_samsung_ultra_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_samsung_ultra_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE phone_samsung_ultra_06_admin: GOOD: Admin login gate (token + Sign in) | BAD: none
CRITIQUE phone_samsung_ultra_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE phone_samsung_ultra_landscape_01_home: GOOD: Monte sua lista + search + staple chips + recent list + VER PREÇOS in viewport; no APK banner (post-recapture) | BAD: none
CRITIQUE phone_samsung_ultra_landscape_02_results: GOOD: settled results — MAIS BARATO Atacado Jatiuca R$22,63 + Economize banner + COMPARTILHAR ECONOMIA + EDITAR LISTA (local mock API rebuild) | BAD: none
CRITIQUE phone_samsung_ultra_landscape_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_samsung_ultra_landscape_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_samsung_ultra_landscape_05_share: GOOD: COMPARTILHAR ECONOMIA full on savings banner + prices R$22,63 (same results surface; local mock API) | BAD: none
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
CRITIQUE phone_rodin_landscape_01_home: GOOD: Monte sua lista + search + staple chips + recent list + VER PREÇOS in viewport; no APK banner (post-recapture) | BAD: none
CRITIQUE phone_rodin_landscape_02_results: GOOD: settled results — MAIS BARATO Atacado Jatiuca R$22,63 + Economize banner + COMPARTILHAR ECONOMIA + EDITAR LISTA (local mock API rebuild) | BAD: none
CRITIQUE phone_rodin_landscape_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE phone_rodin_landscape_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE phone_rodin_landscape_05_share: GOOD: COMPARTILHAR ECONOMIA full on savings banner + prices R$22,63 (same results surface; local mock API) | BAD: none
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
CRITIQUE qhd_01_home: GOOD: layout code + desktop4k_layout_test (contentMaxWidth/tips/headline at QHD) | BAD: V-FORM-FACTOR OPEN — headless Chrome still paints blank white CanvasKit surface; waitFlutter now fails closed (no false CAPTURE_OK); chrome.js uses SwiftShader not --disable-gpu
CRITIQUE qhd_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE qhd_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE qhd_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE qhd_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE qhd_06_admin: GOOD: scaled login card + outer frame + glow on QHD; readable token/Sign in | BAD: none
CRITIQUE qhd_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
CRITIQUE 4k_01_home: GOOD: layout code + desktop4k_layout_test at 4K | BAD: V-FORM-FACTOR OPEN — same headless blank CanvasKit paint as qhd_01_home (not hard-block; capture tooling)
CRITIQUE 4k_02_results: GOOD: settled results with prices/savings (R$) / ranked stores or savings banner; V-STATE-MATCH results surface | BAD: none
CRITIQUE 4k_03_map: GOOD: Mapa das lojas + price pins / OSM tiles; V-MAP-USABLE | BAD: none
CRITIQUE 4k_04_settings: GOOD: Configurações sheet: radius/days steppers + usage toggle; V-SETTINGS-TOGGLES | BAD: none
CRITIQUE 4k_05_share: GOOD: results surface with COMPARTILHAR ECONOMIA / savings CTA; V-SHARE-CTA | BAD: none
CRITIQUE 4k_06_admin: GOOD: larger framed login gate on 4K; intentional chrome not postage stamp | BAD: none
CRITIQUE 4k_07_docs: GOOD: docs brand + nav (sidebar or mobile stack) | BAD: none
```

## open_bads_matrix = 2 (open — home capture; not hard-block)

| cell | residual |
|------|----------|
| `qhd_01_home` | V-FORM-FACTOR HARD-BLOCK: CanvasKit scene never mounts under Chrome capture this host/session (empty glass / splash-only still) — layout code fixed+widget-tested (`desktop4k_layout_test`); see `qhd_01_home.review.json` |
| `4k_01_home` | same HARD-BLOCK as qhd_01_home; `4k_01_home.review.json` |

### Residual notes
- **V-CLIP-TEXT phone landscape (layout):** CLEARED (prior).
- **API capture residuals:** CLEARED (prior).
- **V-FORM-FACTOR admin QHD/4K:** CLEARED 2026-07-17 W-vform — `admin-frontend/styles.css` clamp + frame; opened `qhd_06_admin.png` / `4k_06_admin.png` → BAD: none.
- **V-FORM-FACTOR home QHD/4K:** code shipped (`AppLayout.contentMaxWidth` ~half viewport, desktop shell + tips; `frontend/test/desktop4k_layout_test.dart` green). **W-home-recapture 2026-07-17** re-attempted honest pixel proof:
  1. Stack: API :8000, `frontend/build/web` on **:18090** (not 8080).
  2. Matrix: `BUILD_WEB=0 CONCURRENCY=1 MATRIX_FORMATS=qhd,4k MATRIX_SCREENS=home APP_URL=http://127.0.0.1:18090` → CAPTURE_OK but stills are boot-splash only (qhd 21898b / 4k 41588b).
  3. Probes: WebGL OK (SwiftShader / MakeWebGLCanvasSurface), canvaskit.js+wasm 200, main.dart.js runs; **no** `flt-scene-host` / canvas / first-frame for 30–60s.
  4. Stopped friends AVD (`qemu-system-x86_64 -avd friends -gpu host`, was ~285% CPU) — **still** no first frame after kill; clean `flutter build web` did not fix.
  5. Live `https://alagoas.precospublicos.ia.br/` same empty glass under headless.
  6. Emulator restart **not** required for this task (left down; may be respawned by other tools).
  Host recovery (CanvasKit first-frame paints under Chrome) required before open_bads can go to 0; do **not** mark PASS on splash stills.
- Portrait samples: unchanged BAD: none.

