# W1 Report — Flutter unit tests

**Status:** DONE (green)  
**When:** 2026-07-17T20:53Z

## Flutter SDK

| Field | Value |
|-------|--------|
| Path | `/home/viny/flutter` |
| Binary | `/home/viny/flutter/bin/flutter` |
| Version | Flutter **3.44.6** (channel **stable**) |
| Dart | **3.12.2** |
| Install | `git clone -b stable --depth 1` → user-local |
| PATH | Appended `export PATH="$HOME/flutter/bin:$PATH"` to `~/.bashrc` |

Doctor notes (non-blocking for unit tests): Android SDK not configured on this host; Chrome + Linux desktop OK.

## Commands

```bash
export PATH="/home/viny/flutter/bin:$PATH"
cd frontend && flutter pub get && flutter test
```

## Test summary

| Metric | Value |
|--------|--------|
| Result | **All tests passed** |
| Count | **+66** |
| Failures | 0 |
| Skips | **none** |
| Suites | 15 files under `frontend/test/` |

## Fixes (minimal, tests only)

1. **`favoriteCnpjs` signature** — fakes in `feedback_test.dart` and `search_flow_test.dart` lagged `ApiClient.search` after favorites landed.
2. **`searchStream` override** — production `searchControllerProvider` calls `searchStream` (NDJSON); fakes only overrode `search`, so widgets hit real HTTP → test binding 400. Fakes now delegate `searchStream` → `search`.
3. **Feedback tap hit-test** — `Sim` was under bottom `EDITAR LISTA` bar after scroll; ensure visible on `Sim` before tap.

No product/lib changes.

## Residual / not in scope

- Android toolchain for APK/emulator builds still missing here (unit tests do not need it).
- Full UI matrix / Flutter web home stills remain W2/e2e territory.
