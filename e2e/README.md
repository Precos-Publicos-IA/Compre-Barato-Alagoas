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

### Baseline vs full matrix

| Layer | Command / artifact | Gate? |
|-------|-------------------|-------|
| **Baseline local** | `npm run full:local` | **Always required** before push |
| **Baseline live** | `npm run live` after deploy | **Always required** post-deploy |
| **Criteria critiques** | Open `qa_success_criteria.json`; write GOOD/BAD on this-run stills | **Always required** (CAPTURE_OK ≠ review) |
| **A1 Flutter** | `cd frontend && flutter test` when `frontend/` changes | **Required** (product UI is Flutter; host may need SDK) |
| **Priority / debug subset** | `matrix:local` / `MATRIX_FORMATS=priority` | **Debug only** — review present cells; does **not** close 147 residual |
| **Full 147-cell matrix** | Every screen × format VIDEO + quality-hold PNG + A4b∥A6 | **Required** for residual close / full visual QA |

**If multi-format runners are missing or incomplete → install/finish them**, then
run full 147. Do **not** treat “no runners yet” as optional residual. Do **not**
skip baseline. Do **not** invent 147 CRITIQUE lines without pixels.

See `.grok/skills/ui-viewport-qa/SKILL.md` → *Baseline vs full matrix*.

### Matrix runner (`matrix:local` / `matrix`) — **full 147 by default**

`matrix_capture.js` reads `qa_matrix.json`. **Default is full matrix**
(`MATRIX_FORMATS=all` × all 7 screens = **147** cells) when Flutter web is
available (`APP_URL` or auto `flutter build web` + serve). Product screens:
home, results, map, settings, share (+ admin, docs).

| Command | Role |
|---------|------|
| `npm run matrix:local` | Full matrix (default all) + stack boot |
| `npm run matrix:full` | Full matrix + `matrix_emulator.js` handheld Phase A |
| `npm run matrix:priority` | **Debug/fast only** — not residual-close bar |
| `npm run matrix:desktop` | `touch:false` formats only |
| `npm run matrix:emulator` | Handheld adb path (stack must already be up) |
| `npm run matrix:verify` | Presence check for all 147 cells |

- **Desktop / laptop:** Puppeteer + CDP screencast → `recordings/{format}_mouse.webm`
- **Handheld layout assist:** Chrome device metrics PNGs in `matrix_capture.js`
- **Handheld ship-valid Phase A:** `matrix_emulator.js` — emulator +
  `adb shell screenrecord` + `adb shell input` → `recordings/{format}_touch.mp4`

```bash
cd e2e && npm run matrix:local          # full 147 path (default)
npm run matrix:full                     # + emulator handheld
npm run matrix:priority                 # debug subset only
npm run matrix:verify                   # A5 presence for 147
# CONCURRENCY=2 MATRIX_VIDEO_FORMATS=desktop RECORD_VIDEO=1
```

Artifacts: `screenshots/viewports/{format}_{shot_suffix}.png`,
`screenshots/web/e2e/recordings/`. Capture exit 0 is **CAPTURE_OK only** —
open images and write `matrix_critique.md` / `video_critique.md` under
`qa_success_criteria.json` before claiming review or A7.

