# W-emulator-smoke report — matrix_emulator smoke

**Status:** DONE (green minimal smoke on `emulator-5554`)  
**Date:** 2026-07-17  
**Worker:** W-emulator-smoke (must-complete #3)

## Result

| Field | Value |
|-------|--------|
| Exit code | **0** |
| CAPTURE_OK | 7/7 checks, 3/3 cells present |
| ADB serial | `emulator-5554` (`sdk_gphone64_x86_64`, AVD friends) |
| Format | `phone_android` (360×800 CSS, wm 720×1600 dens=320) |
| Screens | `home`, `admin`, `docs` |
| RECORD_VIDEO | 1 → `phone_android_touch.mp4` (~1.3 MiB) |

## Command (repro)

Stack already up (did not kill foreign processes):

- API `127.0.0.1:8000` (health 200)
- Admin `0.0.0.0:8081`
- Docs `0.0.0.0:8082`
- Flutter web Alagoas: `python3 -m http.server 18090` → `frontend/build/web` (**not** :8080)

```bash
cd e2e
ADB_SERIAL=emulator-5554 \
APP_URL=http://127.0.0.1:18090 \
APP_PORT=18090 \
API_PORT=8000 ADMIN_PORT=8081 DOCS_PORT=8082 \
MATRIX_FORMATS=phone_android \
MATRIX_SCREENS=home,admin,docs \
RECORD_VIDEO=1 \
npm run matrix:emulator
```

Key log lines:

```
PASS  emulator device present — emulator-5554
PASS  adb reverse ports — 18090,8000,8081,8082
PASS  wm phone_android — 720x1600 dens=320 land=false
PASS  screencap phone_android_01_home.png — 171929b
PASS  screencap phone_android_06_admin.png — 54774b
PASS  screencap phone_android_07_docs.png — 105300b
PASS  screenrecord phone_android_touch.mp4 — 1357710b
7/7 checks (CAPTURE_OK)
Cells present: 3; missing: 0
```

## Artifacts (gitignored runtime)

- `e2e/screenshots/viewports/phone_android_01_home.png` — real Compre Barato home (search + chips + VER PREÇOS)
- `e2e/screenshots/viewports/phone_android_06_admin.png` — Admin panel sign-in
- `e2e/screenshots/viewports/phone_android_07_docs.png` — docs sidebar
- `e2e/screenshots/web/e2e/recordings/phone_android_touch.mp4`
- `e2e/screenshots/web/phone/emulator_results.json` (`ok: true`)

## Fixes landed (runner only)

`e2e/matrix_emulator.js`: removed unconditional `KEYCODE_BACK` after Chrome open. On this AVD, BACK exited Chrome into Google Calendar fre → false “home” PNGs. Re-assert URL + longer CanvasKit settle instead.

## Host notes (not blockers)

1. **Port 8080 occupied by foreign tree** (`/code/1st-rust-game` `python3 -m http.server 8080` → “RUSTY DASHER”). Left running per lock (no kill). Smoke used `APP_PORT=18090` / existing Alagoas web serve. Default `APP_URL` alone is wrong while that server holds 8080.
2. **Minimal smoke only** — one handheld format × 3 screens. Not full 15 touch formats / full product journey matrix. Runner proven for adb reverse, wm size, Chrome VIEW intent, screencap, screenrecord pull.
3. CAPTURE_OK ≠ A7 visual residual close.

## Project lock

Work confined to `/code/alagoas/Compre-Barato-Alagoas`. No foreign product edits. Did not kill foreign qemu/game servers.
