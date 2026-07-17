# W-ship report — A7 residual practical PASS ship

**Date:** 2026-07-17  
**Worker:** W-ship  
**Commit:** `0d4f923` (`0d4f9232b6b2492f184b716d264e3c680da84455`)  
**Branch:** `main` → `origin/main` (one push, no force, no amend)

## What shipped

17 files (+1012 / −121). Verified residual subset only.

### Included
| Area | Paths |
|------|--------|
| Flutter test fixes (W1) | `frontend/test/feedback_test.dart`, `frontend/test/search_flow_test.dart` — fake `searchStream` + `favoriteCnpjs`; scroll/ensureVisible to **Sim** |
| e2e matrix runner (W2) | `e2e/matrix_capture.js`, `e2e/run_matrix_local.sh`, `e2e/package.json` (`matrix` / `matrix:local` / `matrix:verify`), `e2e/README.md` |
| Critiques (md only) | `e2e/screenshots/viewports/matrix_critique.md`, `e2e/screenshots/web/e2e/video_critique.md` |
| Cycle docs (W3) | `AGENTS.md`, `e2e/qa_success_criteria.json`, `.grok/README.md`, skills `app-input-e2e` + `ui-viewport-qa`, session + W1–W3 reports |

### Excluded (as mandated)
- `frontend/ios/**` generated junk (left untracked)
- PNG / webm / stills under `e2e/screenshots/**`
- secrets / `.env`

## Commit message
```
fix(qa): A7 residual ship — flutter tests, matrix:local, cycle docs
```

## CI after push

### 1) CI/CD — test, build & deploy to VPS  
**Run:** https://github.com/Precos-Publicos-IA/Compre-Barato-Alagoas/actions/runs/29612861070  
**Conclusion:** **failure** (~9m)

| Job | Result |
|-----|--------|
| changes | success (3s) |
| e2e-local | **success** (46s) — full headless suite |
| test | skipped |
| deploy | **failure** (8m18s) |
| live-verify | skipped (deploy failed) |

**Deploy steps that passed:** Flutter setup, Build Flutter web + APK, Configure SSH, rsync frontend web + APK to VPS, SEFAZ token file write.

**Failing step:** `Ship changed parts to the VPS` — after frontend sync, `deploy/sync-sefaz-token.sh` recreated `deploy-api-1` and docker compose tried `compre-barato-alagoas-api:latest`, which **does not exist** on the VPS:

```
Image compre-barato-alagoas-api:latest pull access denied ...
Error response from daemon: No such image: compre-barato-alagoas-api:latest
```

- `CH_FRONTEND=true`, `CH_BACKEND=false` (API image not rebuilt this run).
- Disk free: 25744MB (not a disk abort).
- **Infra residual:** static frontend likely landed; API recreate path assumes `:latest` tag. Not introduced by this QA residual commit. **One-push mandate:** no follow-up fix pushed from W-ship.

### 2) Build CI e2e image  
**Run:** https://github.com/Precos-Publicos-IA/Compre-Barato-Alagoas/actions/runs/29612861134  
(See live status at report time / companion watch.)

## A7 ship bar

- Residual work committed and on `main`.
- Practical A7 close remains: flutter tests + matrix subset + docs baseline vs aspirational 147.
- Full green deploy blocked by VPS API image tag (`:latest` missing), not by the shipped residual content.

## Next (not W-ship)
- Ops: ensure VPS has a loadable API image tag (retag running image as `latest`, or make SEFAZ recreate use the running image digest/tag like `CH_DEPLOYCFG` path).
- Optional re-run deploy workflow once image fixed.

## Companion workflow (not deploy)

### Build CI e2e image · 29612861134
Status at W-ship close (~16m+): **in_progress** on step `Build and push (infrequent — recipe/schedule only)`.
URL: https://github.com/Precos-Publicos-IA/Compre-Barato-Alagoas/actions/runs/29612861134  
Prior successful runs of this workflow finished in ~30s–22m; this run is a long GHCR build/push, not blocking the residual ship content.

## Local post-ship artifacts (not pushed — one-push rule)
- `.grok/status/session.md` — ship checklist marked done
- `.grok/status/worker_wship_report.md` — this file
