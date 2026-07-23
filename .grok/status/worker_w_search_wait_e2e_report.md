# Search wait UI — focused e2e report

**Date:** 2026-07-23T12:23Z  
**Worker:** search_wait e2e (not full matrix / ui-viewport-qa)  
**Result:** **PASS** — exit 0, 10/10 checks

## Goal

Validate the new search wait surface (rotating phrases, ETA ~5/10 min, notification promise) on Flutter web against local mock API, with artificial search delay so the loading UI is visible.

## Servers (left running; tidy note)

| Role | URL | PID | Command |
|------|-----|-----|---------|
| Mock API | `http://127.0.0.1:8000` | **26608** | `python3 run_local.py` (health: `data_source=mock`, `use_mock_sefaz=true`) |
| Flutter web static | `http://127.0.0.1:8090` | **27135** | `python3 -m http.server 8090` serving `frontend/build/web` |

Build was pre-existing with `--dart-define=API_BASE_URL=http://127.0.0.1:8000`.

## Commands

```bash
# Preflight (already up)
curl -s http://127.0.0.1:8000/health
# → {"status":"ok",...,"use_mock_sefaz":true}

# Focused smoke (phone portrait 390×844)
cd /code/alagoas/Compre-Barato-Alagoas
APP_URL=http://127.0.0.1:8090 API_URL=http://127.0.0.1:8000 \
  node e2e/search_wait_smoke.js
# exit 0
```

Script: [`e2e/search_wait_smoke.js`](../../e2e/search_wait_smoke.js)

Behavior:
- Puppeteer via `e2e/lib/chrome.js` (SwiftShader / CanvasKit-safe flags)
- Maceió geolocation stub (same pattern as `matrix_capture.js`)
- Request interception delays **first** `/api/v1/search*` by **7.5s** (follow-ups passthrough so results settle)
- `flutterAddItem` + `flutterTapVerPrecos` layout heuristics; one retry with adjusted Y if no search traffic
- Screenshots at ~1.5s and ~5s into loading, then after stream settle

## Pass / fail table

| Check | Result | Detail |
|-------|--------|--------|
| mock API healthy | **PASS** | source=mock, use_mock_sefaz=true |
| web app responds 200 | **PASS** | status 200 |
| flutter mounted + painted | **PASS** | flutter-view + non-white canvas |
| search request seen | **PASS** | hits=2 (`/api/v1/search/stream`) |
| loading shot non-empty | **PASS** | 118605 B |
| phrase-rotate shot non-empty | **PASS** | 118916 B |
| results shot non-empty | **PASS** | 296499 B |
| search finished after delay | **PASS** | finished=2 pending=0 |
| no severe page errors | **PASS** | clean |
| console errors tolerable | **PASS** | clean |

**10/10 passed (0 hard fails). Exit code 0.**

## Screenshot paths

| File | When | Size |
|------|------|------|
| [`e2e/screenshots/wait-01-loading.png`](../../e2e/screenshots/wait-01-loading.png) | ~1.5s into loading | 118605 B |
| [`e2e/screenshots/wait-02-phrase-rotate.png`](../../e2e/screenshots/wait-02-phrase-rotate.png) | ~5s into loading | 118916 B |
| [`e2e/screenshots/wait-03-results.png`](../../e2e/screenshots/wait-03-results.png) | after delayed stream settled | 296499 B |

## Vision review (read_file on each PNG)

### wait-01-loading.png (~1.5s)

- **Phrase visible:** “Procurando últimas compras…” (first of `kSearchWaitPhrases`) — **yes**
- **Server status line:** “Iniciando busca…” under the rotating title — present
- **Explainer:** NFC-e copy + “Tempo estimado: cerca de 5 min.” — **yes**
- **ETA chip:** yellow pill “Tempo estimado: ~5 min” with clock icon — **yes**
- **Notification promise (web):** card with bell — “Quando a busca terminar, o resultado aparece nesta tela. Tempo estimado: cerca de 5 min.” — correct `isWeb` branch (no OS push promise)
- **Footer note:** “Os primeiros resultados aparecem assim que cada item for encontrado.” — **yes**
- **Layout:** centered spinner in soft green tile, AppBar “Compre Barato Alagoas”, bottom **EDITAR LISTA** — no overflow/clip; generous whitespace OK for phone portrait
- Spinner arc may look like a single pixel in a still (animation frame) — not a product bug

### wait-02-phrase-rotate.png (~5s)

- **Phrase rotated:** “Encontrando preços atualizados…” (index 1; period 3.2s → expected by ~5s) — **yes, rotation works**
- ETA chip, explainer, web notify card, EDITAR LISTA unchanged — **stable chrome**
- Spinner more fully drawn (arc) — loading still active while intercept holds stream

### wait-03-results.png (post-delay)

- **Left loading UI** — full results surface rendered
- Savings banner: “Você pode economizar até **R$ 5,26**” / Atacado Jatiuca
- “Como buscamos” / Arroz mapping present
- Store card “MAIS BARATO” Atacado Jatiuca R$ 22,63, product line, map/Uber/99/address actions
- Map icon in AppBar, EDITAR LISTA bottom bar
- Confirms delayed search completed and UI left the wait state

## Residual issues / notes

1. **Double stream request:** Flutter fires `/api/v1/search/stream` twice in this path (hits=2). Smoke delays only the first so a second request does not re-stick loading another 7.5s. Not a wait-copy bug; possible provider/rebuild noise worth a later look if it shows up in real SEFAZ timing.
2. **Web notify copy:** Correctly avoids promising push notifications; mobile branch not exercised in this Puppeteer run.
3. **ETA for 1 item is 5 min:** Matches `estimateSearchEtaMinutes` (itemCount &lt; 6 → 5). 10-min bucket not covered in this smoke.
4. **Not full matrix:** Single format phone_portrait 390×844 only, by design.
5. **Servers left up** (PIDs above) for further local work; no deploy/push.

## Verdict

Search wait UI e2e **PASS**. Rotating phrases, ~5 min ETA chip, web notification promise, and post-search results all verified by screenshot vision + harness asserts.
