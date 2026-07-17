# W-A4b report — continuous VIDEO review

**Worker:** W-A4b  
**Date:** 2026-07-17  
**Scope:** Video-only review of present desktop recordings. No re-capture. Did not edit `matrix_critique.md` (W-A6 owns).

## Criteria opened

- `e2e/qa_success_criteria.json` → `video_criteria` (VID-JOURNEY, VID-INPUT-WORKS, VID-NO-FLICKER, VID-HUD-USABLE, VID-VISUAL-SAME-AS-MATRIX)
- `input_criteria` where path reaches them (I-SEARCH-SUBMIT, I-KEYBOARD-DESKTOP)

## Inventory reviewed

| recording | size | duration | stills opened |
|-----------|-----:|---------:|---------------|
| `e2e/screenshots/web/e2e/recordings/laptop_hd_mouse.webm` | 4.5MB | 67.5s | frame_000–045 + end samples t≈55–67 |
| `e2e/screenshots/web/e2e/recordings/laptop_720_mouse.webm` | 2.2MB | 28.1s | frame_000–018 + dense fps=1 |
| `e2e/screenshots/web/e2e/recordings/1080p_mouse.webm` | 403KB | 3.9s | frame_000–002 + dense fps=2 (8 frames) |
| `e2e/screenshots/web/e2e/recordings/qhd_mouse.webm` | 197KB | 2.1s | frame_000–001 + dense (4) |
| `e2e/screenshots/web/e2e/recordings/4k_mouse.webm` | 97KB | 1.9s | frame_000–001 + dense (4) |

No `*_touch.webm` / adb screenrecord present.

## VIDEO lines written

File: `e2e/screenshots/web/e2e/video_critique.md` (rewritten for this-run continuous webms).

| line | result |
|------|--------|
| `VIDEO laptop_hd_mouse` | **BAD** VID-JOURNEY (+ VID-VISUAL-SAME-AS-MATRIX): hangs "Iniciando busca…" full remaining ~60s after list build |
| `VIDEO laptop_720_mouse` | **BAD** VID-JOURNEY (+ I-SEARCH-SUBMIT incomplete): types "a", then hangs on search load |
| `VIDEO 1080p_mouse` | **GOOD / BAD: none** — boot → chip óleo → ranked results (R$ prices, Atacado Jatiuca, etc.) |
| `VIDEO qhd_mouse` | **BAD** VID-JOURNEY + VID-INPUT-WORKS — truncated ~2s, ends on home |
| `VIDEO 4k_mouse` | **BAD** VID-JOURNEY + VID-INPUT-WORKS — truncated ~1.9s, ends on home |

## open_bads_video

- **4 / 5** present continuous recordings FAIL at least one blocker video criterion.
- **1 / 5** PASS (`1080p_mouse` only).
- Dominant failure class: **VID-JOURNEY** (search never completes to results on laptop_hd/720; 4k/qhd never start journey).
- Secondary: truncated high-res captures (4k/qhd), incomplete I-SEARCH-SUBMIT.

## Residuals (honest — not invented VIDEO)

1. **Handheld ship-valid adb VIDEO** (`matrix_emulator.js` + `adb screenrecord` + `adb shell input`) — **still missing**. Not this worker’s capture job; do not fake `VIDEO *_touch` lines.
2. No keyboard-modality continuous webms.
3. A7 blocked on open VIDEO BADs + missing handheld continuous path until fixed or user-accepted with IDs listed.

## Artifacts updated

- `e2e/screenshots/web/e2e/video_critique.md`
- `.grok/status/worker_w_a4b_report.md` (this file)
- `.grok/status/session.md` (A4b progress)

## Done criteria

- [x] Every present recording has a VIDEO line with still/frame evidence
- [x] open_bads_video reported
- [x] No rubber-stamp BAD:none on hung/truncated journeys
- [x] Handheld adb gap noted as residual, not faked
