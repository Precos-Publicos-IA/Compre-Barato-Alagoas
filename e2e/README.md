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
| `npm run matrix:local` | Boot stack + **prioritized** multi-format PNGs (+ optional desktop VIDEO) |
| `npm run matrix` | Matrix capture against already-running URLs |
| `npm run matrix:verify` | Presence check for the prioritized subset only |

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

## Autonomous dev cycle / viewport matrix

Ship process for substantial UI work: [`.grok/skills/ui-viewport-qa/SKILL.md`](../.grok/skills/ui-viewport-qa/SKILL.md).

| File | Role |
|------|------|
| [`qa_matrix.json`](qa_matrix.json) | Screens × CSS formats (`expected_cells`: **147** full matrix) |
| [`qa_success_criteria.json`](qa_success_criteria.json) | **PASS/FAIL** criterion ids (open before critiques) |
| `screenshots/viewports/matrix_critique.md` | A6 PNG / baseline still critiques |
| `screenshots/web/e2e/video_critique.md` | A4b video critiques |

### Baseline ship bar vs full matrix

| Layer | Command / artifact | Gate? |
|-------|-------------------|-------|
| **Baseline local** | `npm run full:local` | **Required** before push (user-facing) |
| **Baseline live** | `npm run live` after deploy | **Required** post-deploy |
| **Criteria critiques** | Open `qa_success_criteria.json`; write GOOD/BAD on this-run stills | **Required** (CAPTURE_OK ≠ review) |
| **A1 Flutter** | `cd frontend && flutter test` when `frontend/` changes | **Required** (product UI is Flutter; host may need SDK) |
| **Matrix subset** | `matrix:local` / multi-format stills when a runner produces them | Review **present** cells under criteria |
| **Full 147-cell matrix** | Every screen × format VIDEO + quality-hold PNG | **Aspirational** until multi-format runners land (residual) |

Do **not** skip baseline capture or criteria critiques because the full matrix is
incomplete. Do **not** invent 147 CRITIQUE lines without pixels.

### Prioritized matrix runner (`matrix:local`)

`matrix_capture.js` reads `qa_matrix.json` and captures a **priority subset**
(default formats: `phone_portrait`, `phone_android`, `laptop_hd`, `1080p`) for
admin login, docs home, API `/health` document, and Flutter app home when
`APP_URL` is set or `frontend/build/web` exists. Desktop CDP screencast →
`screenshots/web/e2e/recordings/1080p_mouse.webm` when `RECORD_VIDEO=1` (default).

```bash
cd e2e && npm run matrix:local
# Expand later:
# MATRIX_FORMATS=all npm run matrix:local
# MATRIX_FORMATS=phone_portrait,tablet_portrait,1080p MATRIX_SCREENS=admin,docs npm run matrix
# npm run matrix:verify
```

Artifacts: `screenshots/viewports/{format}_{shot_suffix}.png`. Capture exit 0 is
**CAPTURE_OK only** — open images and write `matrix_critique.md` /
`video_critique.md` under `qa_success_criteria.json` before claiming review.
Path to full matrix: grow `MATRIX_FORMATS` / `MATRIX_SCREENS` (or `MATRIX_FORMATS=all`)
once Flutter web + remaining screens are wired.
