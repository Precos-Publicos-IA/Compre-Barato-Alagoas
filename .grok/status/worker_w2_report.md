# Worker W2 report — matrix + continuous VIDEO

**Date:** 2026-07-17  
**Goal:** close residuals “full multi-format matrix not automated” and “no continuous VIDEO” as far as practical (Flutter/web + admin/docs).

## Delivered

### 1. Multi-viewport capture path

| File | Role |
|------|------|
| `e2e/matrix_capture.js` | Reads `qa_matrix.json`; priority formats; quality-hold PNGs; optional CDP screencast → webm |
| `e2e/run_matrix_local.sh` | Same boot pattern as `run_local.sh` (API+admin+docs); serves Flutter web if `frontend/build/web` exists |
| `e2e/package.json` | `matrix`, `matrix:local`, `matrix:verify` |
| `e2e/README.md` | Documented commands + expansion knobs |

**Default priority formats:** `phone_portrait`, `phone_android`, `laptop_hd`, `1080p`  
**Default screens:** admin (`06_admin`), docs (`07_docs`), api health (`api_health`); + `home` when `APP_URL` set  
**Expand:** `MATRIX_FORMATS=all` or comma ids; `MATRIX_SCREENS=…`; `RECORD_VIDEO=0|1`

### 2. Run result (CAPTURE_OK)

```text
npm run matrix:local  →  25/25 checks passed
12 viewport PNGs under e2e/screenshots/viewports/
1 continuous webm: e2e/screenshots/web/e2e/recordings/1080p_mouse.webm (36 frames, ~571KB)
stills: e2e/screenshots/web/e2e/stills/1080p_mouse/frame_000..002.jpg
Flutter home skipped (no build/web, flutter not on PATH this host)
```

### 3. Review (A6 + A4b)

- Opened all 12 PNGs + 3 video stills with image tool.
- Wrote this-run lines in:
  - `e2e/screenshots/viewports/matrix_critique.md`
  - `e2e/screenshots/web/e2e/video_critique.md`
- **open_bads_matrix:** 0 (for captured subset)  
- **open_bads_video:** 0 (for `1080p_mouse`)  
- Full 147 `A-MATRIX-COMPLETE` still residual (documented; not rubber-stamped).

### 4. Residuals status

| Residual | Status after W2 |
|----------|-----------------|
| No multi-format matrix runner | **Closed practically** — runner + 12-cell priority path; clear expand knobs |
| Full 147 cells automated | **Still open** (by design — prioritized subset) |
| No continuous VIDEO | **Closed practically** for desktop 1080p docs→admin CDP webm |
| Flutter search→results video / home cells | **Open** until W1 flutter build + re-run with APP_URL |

### 5. Product code

Minimal / none — e2e tooling + critiques + docs only. No deploy, no force-push.

## Commands for orchestrator / later expansion

```bash
cd e2e && npm run matrix:local
# After flutter build web:
# APP_URL=http://127.0.0.1:8080 npm run matrix:local
# Full format list (admin/docs/api only):
# MATRIX_FORMATS=all npm run matrix:local
# Presence only:
# npm run matrix:verify
```
