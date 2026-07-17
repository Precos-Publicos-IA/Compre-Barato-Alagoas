# E2E video critiques

Authority: `e2e/qa_success_criteria.json`.  
Run: **2026-07-17** W2 `npm run matrix:local` with `RECORD_VIDEO=1`.

## Continuous VIDEO (this run)

Artifact: `e2e/screenshots/web/e2e/recordings/1080p_mouse.webm` (~571KB, CDP screencast → ffmpeg vp8).  
Stills opened: `e2e/screenshots/web/e2e/stills/1080p_mouse/frame_000.jpg` (docs home), `frame_001.jpg` (Architecture after nav click), `frame_002.jpg` (admin gate with password dots after keyboard type).

```text
VIDEO 1080p_mouse: GOOD: continuous webm; docs home → Architecture/API nav changes main pane; admin login gate; keyboard type fills token (VID-INPUT-WORKS); no freeze/severe flicker in stills | BAD: none
```

Criteria checked on stills + capture path: `VID-JOURNEY` (docs→admin desktop journey for surfaces available without Flutter web), `VID-INPUT-WORKS`, `VID-NO-FLICKER`, `VID-HUD-USABLE`, `VID-VISUAL-SAME-AS-MATRIX` (matches 1080p_07_docs / 1080p_06_admin matrix cells), `I-NAV-PRIMARY`, `I-KEYBOARD-DESKTOP`.

## Prior baseline (still valid as historical CAPTURE notes; not this-run continuous video)

```text
VIDEO desktop1280_mouse_full_local: GOOD: admin login/tabs, docs nav, API search stores=5, qty scaling (full.js stills path) | BAD: none
VIDEO live_production_journey: GOOD: app 200 + flutter mounted, health, suggestions, search stores=5, qty scaling, consent, feedback, docs, admin gate (live.js stills path) | BAD: none
```

## Residual (honest)

| Item | Status |
|------|--------|
| Continuous desktop webm | **Closed for 1080p mouse docs→admin journey** |
| Flutter search→results continuous VIDEO | Open until APP_URL / Flutter web in matrix path |
| Per-matrix-unit VIDEO for all 21 formats | Open — expand `RECORD_VIDEO` + format loop later |
| Phone continuous VIDEO (emulator screenrecord) | Out of scope for this Puppeteer path; Phase A handheld skill |

`no continuous VIDEO` residual closed as far as practical for admin/docs desktop primary journey.
