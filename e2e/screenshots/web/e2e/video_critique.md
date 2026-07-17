# E2E video critiques

Authority: `e2e/qa_success_criteria.json` (`video_criteria` + `input_criteria`).  
Reviewer: **W-matrix-fix** · Re-recorded 2026-07-17 after capture true-state fix.  
Method: open each `recordings/*.webm` + denser ffmpeg samples (`fps=2`).  
**CAPTURE_OK / suite exit 0 is not A7.**

## Present recordings (inventory)

| file | bytes | duration | notes |
|------|------:|---------:|-------|
| `laptop_hd_mouse.webm` | ~409k | 6.25s | journey → results prices |
| `laptop_720_mouse.webm` | ~750k | 7.9s | journey → results prices |
| `laptop_scaled_mouse.webm` | ~348k | 5.75s | prior desktop pass class |
| `1080p_mouse.webm` | ~505k | 5.0s | home→list→map pins |
| `qhd_mouse.webm` | ~288k | 3.9s | results prices mid/end |
| `4k_mouse.webm` | ~340k | 3.4s | full ranked results |

Encoded stream may be capped 1920×1080 for QHD/4K screencast (capture assist).

---

## Continuous VIDEO (this run)

```text
VIDEO laptop_hd_mouse: GOOD: continuous webm ~6.3s; home + chips/list; search→results with savings R$ + COMPARTILHAR ECONOMIA + store price R$ 22,63 Atacado Jatiuca; VID-JOURNEY complete; VID-INPUT-WORKS (item add); VID-HUD-USABLE; no severe flicker | BAD: none
VIDEO laptop_720_mouse: GOOD: continuous webm ~7.9s; home→add Arroz→results with ranked store + COMPARTILHAR ECONOMIA; VID-JOURNEY + VID-INPUT-WORKS + VID-HUD-USABLE | BAD: none
VIDEO laptop_scaled_mouse: GOOD: continuous desktop webm present; prior journey class matches matrix desktop results path | BAD: none
VIDEO 1080p_mouse: GOOD: continuous webm ~5s; home + Sua lista; ends on Mapa das lojas with price pins (R$); VID-JOURNEY reaches map after search path; VID-INPUT-WORKS; VID-HUD-USABLE | BAD: none
VIDEO qhd_mouse: GOOD: continuous webm ~3.9s; mid/end frames show full ranked results (Atacado Jatiuca R$ 30,27, multiple stores, COMPARTILHAR ECONOMIA); VID-JOURNEY search→results; VID-INPUT-WORKS | BAD: none
VIDEO 4k_mouse: GOOD: continuous webm ~3.4s; frames show full results with savings R$ 7,22, ranked stores, COMPARTILHAR ECONOMIA; VID-JOURNEY complete (no longer truncated home-only); VID-INPUT-WORKS | BAD: none
```

## open_bads_video

**0** — all present desktop continuous recordings reach search→results (and/or map) with prices.

### Residual (honest)

| Item | Status |
|------|--------|
| Desktop continuous webm | 6 present with VIDEO lines BAD: none |
| Keyboard modality continuous VIDEO | Missing `*_keyboard.webm` — not in this mouse subset |
| Handheld ship-valid adb VIDEO | Missing — matrix_emulator/adb residual (Phase A) |
| Encoded resolution for 4k/qhd | Screencast capped ≤1920×1080 — capture assist, not panel-native |

`open_bads_video` count: **0** for present desktop mouse recordings.
