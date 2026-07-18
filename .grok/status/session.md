# Session status

Last update: fixed false CAPTURE_OK + CanvasKit chrome flags; home pixel proof still open

## Project lock
**HARD** Alagoas only. Refuse other projects (Rusty Dasher etc.).

## Goal
Clear qhd/4k home V-FORM with honest pixels (not fake hard-block).

## Findings (this session)
1. `e2e/lib/chrome.js` had **`--disable-gpu`** — bad for CanvasKit. Now defaults to ANGLE+SwiftShader + `--enable-unsafe-swiftshader`.
2. `waitFlutter` treated empty `flt-glass-pane` as ready → **splash-only CAPTURE_OK**. Now requires **shadow-piercing canvas + non-white pixels**.
3. `index.html` no longer forces styles on `flt-glass-pane` (could interfere with host).
4. Headless Chrome still produces **blank white bitmaprenderer canvas** (surface exists, content white) on local+live — product layout remains proven by **widget tests** (QHD+4K). Matrix home cells stay **OPEN** until headless paints real UI (or alternate capture path lands).

## Must-complete
| # | Status |
|---|--------|
| 1 V-FORM home qhd/4k open_bads 0 | **OPEN** — layout code + widget tests green; honest capture gate shipped; headless paint still blank |
| 2 Project lock | **DONE** |
| 3 matrix_emulator smoke | **DONE** `d1a4245` |
| 4 Human re-schedule `/loop` | **OPEN** (human) |

## Not a hard-block
Empty CanvasKit in headless is a **capture tooling defect**, not “agents cannot work.” Keep iterating (Chrome flags / headed / alternate capture). Do not park as optional.

## Next
- Land chrome/waitFlutter fixes
- Continue until headless (or alternate) produces non-white qhd/4k home stills → critique BAD: none
