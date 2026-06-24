# e2e — headless browser suite

Puppeteer drives real **Chrome/Chromium** with **simulated user input** and
**screenshots**. See [`AGENTS.md`](../AGENTS.md) for when this is mandatory
(local before PR, live after deploy).

| Command | Use |
|---------|-----|
| `npm run full:local` | Mock backend + admin + docs; full DOM/API suite (PR gate) |
| `npm run full` | Same suite against already-running URLs |
| `npm run live` | Production app/API/docs (+ optional admin) post-deploy |
| `npm run smoke` | Lighter live app + API shape check |
| `npm run admin_smoke` | Admin SPA gate + `esc()` presence (#134); optional `ADMIN_TOKEN` |

## iPhone / Safari / WebKit limitation (issue #16)

Mobile coverage in `full.js` / `smoke.js` / `live.js` uses a **Chromium** viewport
(`390×820`, `isMobile: true`, `hasTouch: true`) — **not** Safari or WebKit.
That approximates an iPhone-sized layout but **does not** exercise:

- Safe-area / notch / home-indicator quirks (`env(safe-area-inset-*)`, `dvh`)
- `-webkit-` scrolling / rubber-banding / `100vh` bugs
- Safari-only PWA **Add to Home Screen** / standalone install path
- iOS permission prompts (mic, speech, location) in Safari or WKWebView
- Input focus zoom when `font-size` &lt; 16px

**What to do instead for iPhone-only risk:**

1. After deploy (or before merge for high-risk CSS/PWA/iOS work), open a
   **[iPhone Safari / WebKit checklist](../.github/ISSUE_TEMPLATE/iphone-safari-checklist.md)**
   issue and run it on a real device.
2. Structural guards (Linux-friendly, no Xcode):
   ```bash
   python3 scripts/verify_ios_webkit_e2e.py   # docs + template + ios/ in-scope
   python3 scripts/verify_ios_info_plist.py   # when Info.plist exists (#5/#10)
   ```
3. Optional future: Playwright `webkit` on Linux as a **proxy** (still not full
   iOS Safari); document any such job here if added. Native app QA remains
   `frontend/integration_test/` on device/simulator (Mac).

## Local (dev machine)

```bash
cd e2e && npm install
npx puppeteer browsers install chrome   # once if needed
npm run full:local
npm run live                            # after deploy
```

## CI — published image only (standard GHCR + job `container:`)

Best practice (GitHub docs: *Running jobs in a container* + GHCR publish):

| Workflow | When it runs | What it does |
|----------|--------------|--------------|
| **`ci-image.yml`** | `main` push **only if** `e2e/Dockerfile.ci` / `e2e/package.json` change, weekly schedule, or **workflow_dispatch** | **Build + push** `ghcr.io/precos-publicos-ia/compre-barato-alagoas/ci-e2e:latest` (+ sha tag) |
| **`deploy.yml`** (`test`, `e2e-local`, `live-verify`) | Every relevant PR/main run | **`container: image: …ci-e2e:latest`** — Actions **pulls** the image; steps are only checkout + run. **No `docker build` / no save-load artifact** |

Bootstrap once (needs `packages: write` on the publish workflow, package visibility allowing the repo to read):

1. Actions → **Build CI e2e image** → **Run workflow** on `main`  
2. In GHCR package settings, allow the repo to pull (inherit access / public as you prefer)  
3. Later PRs only pull — fast and stable

If a job fails with “pull access denied” / missing image, **do not** add a build step to `deploy.yml`; re-run the publish workflow.

Screenshots land in `screenshots/` (gitignored). Exit non-zero on any failed check.

## Ops / contract probes (#278)

Lightweight checks without a browser (Node 18+ `fetch`):

```bash
# Against local mock API (from e2e/ or any cwd)
API_URL=http://127.0.0.1:8000 OPS_EXPECT_MOCKS=true OPS_REQUIRE_CLIENT_CONFIG=false \
  node ops_probes.js

# Against production app host (strict mocks off + security.txt + client-config once deployed)
API_URL=https://alagoas.precospublicos.ia.br APP_URL=https://alagoas.precospublicos.ia.br \
  OPS_FORBID_MOCKS=true OPS_REQUIRE_CLIENT_CONFIG=true OPS_REQUIRE_SECURITY_TXT=true \
  node ops_probes.js
```

`run_local.sh` runs `ops_probes.js` first with `OPS_EXPECT_MOCKS=true` and
`OPS_REQUIRE_CLIENT_CONFIG=false` so main without `GET /api/v1/client-config` still works;
flip `OPS_REQUIRE_CLIENT_CONFIG=true` after that route is live (PR #271 area).
