# e2e — headless browser smoke test

A small [Puppeteer](https://pptr.dev/) harness that boots the **web app** in a real
(headless) Chrome and exercises the **API** from inside the page. It catches things unit
tests and on-device tap-tests can't: broken web builds, missing assets, CORS/CSP
surprises, console/page errors, and API response-shape regressions (including the
requested-quantity scaling).

> The user app is Flutter web (CanvasKit), which renders into a `<canvas>`. Reliable
> tap-by-tap driving isn't possible from the DOM, so full UI flows live in the Flutter
> `frontend/integration_test/` suite (run on-device). This harness is the browser-level
> **smoke** complement.

## Run against production
```bash
cd e2e && npm install            # uses system Chrome; no Chromium download needed
PUPPETEER_SKIP_DOWNLOAD=1 npm install   # if you want to skip the bundled Chromium
npm run smoke                    # APP_URL defaults to the live site
```

## Run against a local stack
```bash
# 1) backend with no external deps (fakeredis + mocks)
cd backend && python run_local.py            # http://127.0.0.1:8000

# 2) a local web build pointed at that backend
cd frontend && flutter build web --release \
  --dart-define=API_BASE_URL=http://127.0.0.1:8000
python3 -m http.server 8080 --directory build/web   # http://127.0.0.1:8080

# 3) the smoke test
cd e2e && APP_URL=http://127.0.0.1:8080 API_URL=http://127.0.0.1:8000 npm run smoke
```

Screenshots are written to `e2e/screenshots/`. Exit code is non-zero if any check fails.
