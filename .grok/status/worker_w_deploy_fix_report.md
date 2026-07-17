# W-deploy-fix report

**Status:** DONE  
**Commits:** `d37a924` (partial; broken quote), `585c1f0` (final, green)  
**Date:** 2026-07-17

## Root cause
Frontend-only / static deploys set `RECREATE_API=1` in `deploy/sync-sefaz-token.sh` so the API reloads `secrets/sefaz.env`. Compose uses `image: ${API_IMAGE:-compre-barato-alagoas-api:latest}` but CI only loads sha tags (`compre-barato-alagoas-api:<sha>`) and prunes others — **`:latest` is often absent on the VPS**. Recreate tried to pull/use `:latest` and failed:

```
Image compre-barato-alagoas-api:latest pull access denied ...
Error response from daemon: No such image: compre-barato-alagoas-api:latest
```

That left `deploy-api-1` gone (failed recreate after remove), which also broke a naive `docker inspect deploy-api-1` path until fallback to local sha tags.

## Fix (minimal)
1. **`deploy/sync-sefaz-token.sh`** — On recreate, pin `API_IMAGE` from:
   - caller env, else
   - container `Config.Image`, else
   - newest local `compre-barato-alagoas-api` tag ≠ `:latest`  
   Abort clearly if none / image not on host. Never bare `:latest` fallback.
2. **`.github/workflows/deploy.yml`** — `resolve_remote_api_image()` for deploycfg restart and static token-sync pin (same priority).
3. **`deploy/remote-update.sh`** — Refuse missing `API_IMAGE` on host before `compose up`.

Security model unchanged: token length only logged; `sefaz.env` mode 600; FILE fallback 644 for non-root appuser.

## Files changed
- `/code/alagoas/Compre-Barato-Alagoas/deploy/sync-sefaz-token.sh`
- `/code/alagoas/Compre-Barato-Alagoas/deploy/remote-update.sh`
- `/code/alagoas/Compre-Barato-Alagoas/.github/workflows/deploy.yml`

## CI
| Run | SHA | Result |
|-----|-----|--------|
| [29612861070](https://github.com/Precos-Publicos-IA/Compre-Barato-Alagoas/actions/runs/29612861070) | `0d4f923` | FAIL — original `:latest` bug |
| [29613853257](https://github.com/Precos-Publicos-IA/Compre-Barato-Alagoas/actions/runs/29613853257) | `d37a924` | FAIL — bash quote bug (`|| true` inside nested `"$(...)"`) |
| [29614078346](https://github.com/Precos-Publicos-IA/Compre-Barato-Alagoas/actions/runs/29614078346) | `585c1f0` | **SUCCESS** deploy + live-verify |

Evidence from green run:
- `Resolved API_IMAGE=compre-barato-alagoas-api:b5cbfff48badae641325ea802204df70d973c77f`
- SEFAZ secrets written (token not logged)
- `Starting stack with API_IMAGE=...b5cbfff...` → Healthy

## Residual risks
- First boot with **no** local API image and no backend build still cannot recreate API (by design — clear ABORT).
- `remote-update` still defaults env to `:latest` if unset for manual use, but aborts if that tag is missing.
- Frontend-only path with pin was exercised via deploycfg full restart after prior damage; pure frontend-only pin path is covered in script logic and should be fine next static deploy.
- Left `frontend/ios/**` untracked junk alone; did not redo QA residual commit.
