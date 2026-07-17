# W-ship-hygiene report

**Date:** 2026-07-17  
**Worker:** W-ship-hygiene  
**Status:** DONE  
**Commit:** `a83a285` (`a83a285db1fb2fe791d87d9e1b571eac31a7a36a`)  
**Also pushed:** `286b24f` (prior local A7 status commit)  
**Branch:** `main` → `origin/main`

## Goal

Commit and push intentional process/hygiene already complete on disk so PROJECT_LOCK is not half-unshipped. Leave unfinished V-FORM product UI uncommitted (W-vform owns).

## Included (shipped)

| Path | Why |
|------|-----|
| `PROJECT_LOCK.md` | HARD project lock + finish rules |
| `AGENTS.md` | Lock section + finish rules + matrix residual wording |
| `.grok/README.md` | Point at lock; full-matrix not optional |
| `.grok/skills/orchestrator-loop/SKILL.md` | Lock/finish in skill |
| `.grok/prompts/orchestrator-loop.md` | `/loop` paste with lock + finish |
| `.grok/status/session.md` | Live must-complete checklist |
| `.grok/status/worker_w_*.md` (completed reports) | A4b, A6, capture-local-api, deploy-fix, live-verify, re-critique-mobile, wship; mobile_design SHA fill |
| `e2e/matrix_emulator.js` | Handheld Phase A runner (intentional, ready) |
| `e2e/package.json` | `matrix:emulator`, `matrix:full`, `matrix:priority`, etc. |
| `e2e/README.md` | Baseline vs full matrix docs |
| `e2e/lib/chrome.js` | `protocolTimeout` for long matrix |
| `e2e/screenshots/viewports/matrix_critique.md` | open_bads_matrix = 4 (desktop V-FORM only) |
| `e2e/screenshots/viewports/*.review.json` | Per-cell review notes (promax/rodin/samsung landscape) |

## Excluded (left dirty — intentional)

| Path | Why |
|------|-----|
| `frontend/lib/core/layout.dart` | Incomplete V-FORM mid-edit (contentMaxWidth QHD/4K) — **W-vform** |
| `frontend/lib/features/search/search_screen.dart` | Same V-FORM shell tweak — **W-vform** |
| `admin-frontend/styles.css` | Login card clamp for QHD/4K — same unfinished V-FORM batch — **W-vform** |
| `frontend/ios/**` generated junk | Flutter scaffold junk; never ship |

No secrets / `.env` included.

## CI

| Run | URL | Result |
|-----|-----|--------|
| CI/CD `29621098045` | https://github.com/Precos-Publicos-IA/Compre-Barato-Alagoas/actions/runs/29621098045 | **success** |

Jobs:
- `changes` — success
- `e2e-local` — success (~39s; AGENTS.md + e2e/** path filter)
- `test` / `deploy` / `live-verify` — **skipped** (no backend/frontend/admin/docs/deploycfg paths)

**Note:** Not a product VPS redeploy. Lock/docs/e2e hygiene only. Prior product ship remains `d2497c1` live.

## Origin lock rules

- `PROJECT_LOCK.md` on `main` at `a83a285`
- Orchestrator prompt/skill on origin; operator should re-schedule `/loop` paste (must-complete #4 human)

## Residual for session

1. V-FORM qhd/4k (4 open BADs) — W-vform when host CPU allows  
2. ~~Git hygiene~~ — **DONE** this worker  
3. matrix_emulator smoke or hard-block evidence — still OPEN  

## Commit message

```
chore: project lock + finish rules; ship hygiene artifacts
```
