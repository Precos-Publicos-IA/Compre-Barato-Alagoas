# W-live-ship report

**Status:** DONE — deploy green + live smoke PASS  
**Date:** 2026-07-17T23:19Z  
**Worker:** W-live-ship  
**Shipped SHA (CI):** `d2497c1` (`d2497c1580392869a53e76c0bb5428a7b47efd53`)  
**Local tip note:** `50f65cb` skill sync is local-only (ahead of origin); not in this deploy.

## Verdict
**Phase B: SUCCESS.** Mobile UI `d2497c1` is live on production.  
**A7 practical: PASS** for mobile residual close (user mobile-focused).  
Residual open BADs: **4× desktop V-FORM-FACTOR only** (QHD/4K home+admin sparse canvas — usable).

## CI/CD
| Field | Value |
|-------|--------|
| Run | [29619545203](https://github.com/Precos-Publicos-IA/Compre-Barato-Alagoas/actions/runs/29619545203) |
| Title | feat(ui): serious mobile product design for Compre Barato |
| Conclusion | **success** |
| Jobs | changes ✓ · e2e-local ✓ · test skipped · deploy ✓ (~15m) · live-verify ✓ (33s) |

### Deploy shape
- Path filter: **frontend + e2e** (no backend image rebuild this run).
- Flutter web + APK built and rsynced to VPS.
- Token-sync recreated API with pin  
  `API_IMAGE=compre-barato-alagoas-api:b6ec7a806a18e625784b44bfef704ca33515e940`  
  (existing healthy image; not bare `:latest`).
- SEFAZ env (deploy log, no secrets):  
  **`USE_MOCK_SEFAZ=false` `USE_WEB_SEFAZ=true`**  
  (official API host still broken; AppToken kept in `secrets/`, cleared from shared `.env`).

### CI live-verify (`e2e/live.js`)
**14/14 live checks passed**, including:
- live app 200 + Flutter mounted
- health + request-id
- suggestions n=12
- search status=200 **stores=5** + qty scaling
- consent, feedback, docs, admin gate

## Independent live smoke (public HTTPS only)
Host: `https://alagoas.precospublicos.ia.br`  
No secrets printed / no SSH.

| Check | Result |
|-------|--------|
| `GET /` | **HTTP 200** ~0.6s, Flutter shell markers present |
| `GET /health` | **HTTP 200** `{"status":"ok"}` |
| popular `POST /api/v1/search` `["3 arroz","feijao"]` | **200**, **stores=5**, **data_source=web**, ~2.4s |
| cold `cafe solúvel`+`banana prata` r12 d4 | **200**, **stores=5**, **data_source=web**, ~56s |
| cold `macarrao parafuso` r11 d3 | **200**, **stores=5**, **data_source=web**, ~0.6s |

Not mock: real AL store names (e.g. MERCADINHO DO AMIGÃO, BARRATEIRO, PRECO BOM); CNPJ kind prefix `web:`.

### USE_WEB_SEFAZ path
Production remains on **Economiza AL website** SEFAZ path (`USE_WEB_SEFAZ=true`), not official JSON API, not mock. Confirmed by:
1. Deploy token-sync log line `USE_WEB_SEFAZ=true`
2. Search responses `data_source=web` + `web:` CNPJ prefix on popular **and** cold probes

## A7 practical residual list
`open_bads_matrix = 4` (desktop only; mobile product V-CLIP = 0; video = 0; API-capture residuals = 0):

| Cell | BAD |
|------|-----|
| qhd_01_home | V-FORM-FACTOR: large empty / sparse chrome (usable) |
| qhd_06_admin | V-FORM-FACTOR: tiny card in large canvas (usable) |
| 4k_01_home | V-FORM-FACTOR: large empty / sparse chrome (usable) |
| 4k_06_admin | V-FORM-FACTOR: tiny card in large canvas (usable) |

Accepted for A7 practical (mobile residual close). Desktop QHD/4K form polish deferred.

## Phase B result
| Item | Status |
|------|--------|
| Deploy CI green for `d2497c1`+ | **PASS** (run 29619545203) |
| App HTTP 200 | **PASS** |
| Health | **PASS** |
| Search stores>0 (popular + cold) | **PASS** (5/5 web) |
| USE_WEB_SEFAZ noted | **true** (forced while official host dead) |
| A7 practical mobile close | **PASS** w/ 4 desktop V-FORM residual |

## Not done / follow-ups (non-blocking)
- Local unpushed `50f65cb` skill sync (optional later push)
- Official SEFAZ API re-enable when host fixed → set `USE_WEB_SEFAZ=false` + redeploy
- Desktop QHD/4K density polish (4 residual cells)
- Optional: nginx 120s proxy timeouts still manual on VPS for multi-item cold web
- Physical phone Phase C still out of GHA (annotation on live-verify)

## Commits / tree
- No code fix needed (green ship).
- Did not force-add `frontend/ios/**` junk.
- Status files updated: `session.md`, this report.
