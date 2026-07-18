# W-deploy-live report

**Status:** DONE — deploy green + live smoke PASS  
**Date:** 2026-07-18T02:24Z  
**Worker:** W-deploy-live  
**Product SHA (CI):** `0c38cb6` (`0c38cb6fe3f4e818c03f5b24505522db5b1c9d12`)  
**Title:** fix(ui): stop bottom bar covering wide home (QHD/4K form factor)

## Verdict
**Phase B: SUCCESS.** Bottom-bar / QHD-4K home fix is deployed and verified live.

## CI/CD — product fix run
| Field | Value |
|-------|--------|
| Run | [29626602645](https://github.com/Precos-Publicos-IA/Compre-Barato-Alagoas/actions/runs/29626602645) |
| headSha | `0c38cb6fe3f4e818c03f5b24505522db5b1c9d12` |
| Conclusion | **success** |
| Jobs | changes ✓ · e2e-local ✓ · test skipped · deploy ✓ (~8m) · live-verify ✓ (~35s) |

### Deploy shape
- Path filter: **frontend** (Flutter web + APK rebuild; API image build skipped).
- Ship: rsync static assets to VPS; token-sync recreated API; static-only change (no full stack restart beyond token path).
- `main.dart.js` on production: HTTP 200, `content-length: 3099257`, **Last-Modified: Sat, 18 Jul 2026 02:14:34 GMT** (within deploy window).

### Follow-on status pushes (same gate window)
| Run | SHA / title | Conclusion | Notes |
|-----|-------------|------------|-------|
| 29626614960 | `bd61e09` reaped W-home-capture | **cancelled** | supersession; product deploy already running |
| 29626708577 | `cf4dc0d` spawn W-deploy-live | **success** | docs/status only — deploy/live-verify skipped |

## CI live-verify (`e2e/live.js` on GHA)
**14/14 live checks passed** (run 29626602645 job `live-verify`):
- live app 200 + Flutter mounted
- health + request-id
- suggestions n=12
- search status=200 **stores=5** + qty scaling
- consent, feedback, docs, admin gate (token unset → gate only)

Artifact: `e2e-screenshots-live` id `8424151618`.

## Independent live smoke (public HTTPS)
Host: `https://alagoas.precospublicos.ia.br`  
Command (local, env cleaned of local APP_URL/ADMIN_TOKEN):

```bash
cd e2e && env -u APP_URL -u API_URL -u DOCS_URL -u ADMIN_URL -u ADMIN_TOKEN -u LIVE_ADMIN_TOKEN \
  npm run live
```

| Check | Result |
|-------|--------|
| Suite | **14/14 PASS**, exit 0 |
| APP_URL | `https://alagoas.precospublicos.ia.br` |
| Docs / Admin | production hosts |
| Screenshots | `e2e/screenshots/live-01-app-home.png` … `live-04-admin-gate.png` (gitignored runtime) |

### Public probes (no secrets)
| Probe | Result |
|-------|--------|
| `GET /` | **HTTP 200** ~0.6s, Flutter shell (`flutter_bootstrap.js`) |
| `GET /health` | **HTTP 200** `{"status":"ok"}` |
| `POST /api/v1/search` `{"items":["3 arroz","feijao"]}` | **200**, **stores=5**, **data_source=web** |
| Store sample | MERCADINHO DO AMIGÃO, CNPJ prefix `web:` |

Not mock: real AL store names; SEFAZ path remains **Economiza AL website** (`data_source=web`).

### Note on first local attempt
First `npm run live` without unsetting env hit **localhost** (`APP_URL=http://127.0.0.1:18090` leftover from matrix). Second attempt against production with stale `ADMIN_TOKEN` failed optional admin login (13/14). Clean prod env → **14/14**. CI never had this issue.

## Optional bottom-bar fix on live (no false visual claim)
- Product change is Flutter `AppLayout.constrainContent(expand: false)` for bottom bars (`frontend/lib/core/layout.dart`).
- Compiled `main.dart.js` was **redeployed** (new Last-Modified in deploy window).
- Live suite confirms Flutter mounted + home screenshot captured at 390×820.
- **Not claimed:** pixel proof of QHD/4K bottom-bar geometry on production (would need wide-viewport live matrix / device). Local open_bads_matrix was already 0 with goldens for that fix.

## Phase B result
| Item | Status |
|------|--------|
| Deploy CI green for `0c38cb6` | **PASS** (run 29626602645) |
| CI live-verify 14/14 | **PASS** |
| Independent `npm run live` vs production | **PASS** 14/14 |
| App HTTP 200 + Flutter | **PASS** |
| Health | **PASS** |
| Search stores>0 web | **PASS** (5/5) |
| Hard block | **none** |

## Next for orchestrator
- Reap W-deploy-live → Phase B **closed**.
- Must-complete #5 DONE; agent idle unless human re-schedules `/loop` (#4 human).
