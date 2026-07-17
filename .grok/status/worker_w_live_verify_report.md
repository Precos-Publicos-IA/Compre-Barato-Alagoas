# W-live-verify report

**Status:** DONE — production healthy after fix  
**Date:** 2026-07-17  
**Final ship:** `b6ec7a8` (also intermediate `d974916`)

## Verdict
**Healthy: YES** (with SEFAZ via Economiza **website**, not mock, not official JSON API)

Green CI alone was **not** enough for `585c1f0`: live-verify only hit cached popular terms; cold searches were empty or 504.

## What CI run 29614078346 (`585c1f0`) actually checked
- Path filter: deploycfg only (no backend image rebuild)
- Deploy: pinned existing image `compre-barato-alagoas-api:b5cbfff…`, SEFAZ token sync, stack healthy
- live-verify (`e2e/live.js`): app 200 + Flutter mount, `/health` ok, suggestions n=12, search `arroz`/`feijao` stores=5 (qty scaling), consent, feedback, docs, admin gate
- **Did not** cache-bust or assert SEFAZ source / cold path

## Independent live probes (before fix)
| Check | Result |
|-------|--------|
| https://alagoas.precospublicos.ia.br/ | 200 Flutter shell |
| `/health` | 200 `{"status":"ok"}` (prod strips mock flags — by design) |
| docs / admin | 200 |
| Popular search | 200 stores=5, CNPJ `web:*`, real AL store names (not mock Super Pajucara) |
| Cold search (radius/days bust) | `data_source=sefaz`, **stores=0**, ~16s (official API timeout) |
| Official host probe (no secrets) | TLS SAN = `acessoaplicativo.hom.sefaz.al.gov.br`; HTTPS path 404; HTTP 403 |

Root cause: AppToken present → `RoutingSefazClient` always hit dead `api.sefaz.al.gov.br`; errors swallowed → empty baskets. Cache still served old **web** results for popular terms → false green.

## Fixes shipped
1. **`d974916`** — `RoutingSefazClient` falls back to website when official API raises; raise item deadline; unit test
2. **`b6ec7a8`** — deploy token-sync sets `USE_WEB_SEFAZ=true` while official host is broken (token still in `secrets/`); shorter API timeout defaults; nginx vhost template `proxy_*_timeout 120s` (manual apply on VPS — pipeline does not reload nginx)

## Post-fix evidence (`b6ec7a8` / run 29615123621)
CI: https://github.com/Precos-Publicos-IA/Compre-Barato-Alagoas/actions/runs/29615123621 — success (test, e2e-local, deploy, live-verify)

Deploy log (no secrets):
- `Loaded image: compre-barato-alagoas-api:b6ec7a806a18e625784b44bfef704ca33515e940`
- `USE_MOCK_SEFAZ=false USE_WEB_SEFAZ=true (official API host broken; token kept in secrets/)`
- `Starting stack with API_IMAGE=…b6ec7a8…` → Healthy

Independent HTTP (after deploy):
| Check | Result |
|-------|--------|
| app / health / docs / admin | 200 |
| suggestions | n=12 |
| popular `arroz`+`feijao` | 200, **src=web**, stores=5, ~0.6s |
| cold `cafe` r14 d5 | 200, **src=web**, stores=5, ~51s |
| cold `banana prata` r12 d4 | 200, **src=web**, stores=5, ~18s |
| cold `macarrao` r11 d3 | 200, **src=web**, stores=5, ~53s |

Not mock: store names e.g. MERCADINHO DO AMIGÃO, HATSU IZAKAYA, PRECO BOM; CNPJ prefix `web:`.

## Residual / ops follow-ups
- **Re-enable official API** when SEFAZ fixes host: set `USE_WEB_SEFAZ=false` in VPS `.env` (or flip sync script) and redeploy; routing fallback remains as safety net
- **Apply nginx 120s timeouts** on VPS by hand (`deploy/nginx/alagoas.precospublicos.ia.br.conf`) — live currently survives cold web ~50s under default 60s but multi-item cold is tight
- live-verify still does not cold-bust SEFAZ (optional hardening)
- No VPS SSH from this worker; public HTTP + CI logs only
- Left `frontend/ios/**` untracked junk alone

## Commits
| SHA | Note |
|-----|------|
| `d974916` | API→web fallback in factory |
| `b6ec7a8` | Force web on deploy + timeouts + nginx template |
