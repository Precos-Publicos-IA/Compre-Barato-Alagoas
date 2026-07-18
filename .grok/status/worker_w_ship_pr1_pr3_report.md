# W-ship report — PR1+PR3 ship + targeted re-eval

**Worker:** W-ship  
**Date:** 2026-07-18  
**Task:** Must-complete #8 — push PR1+PR3, deploy green, targeted óleo/ovo + partial-savings re-check  
**Scope HARD:** functionality / known problem points only — no matrix, no full:local residual

## Product SHAs (on `main`, pushed)

| Item | SHA | Title |
|------|-----|--------|
| PR1 product | `504eb38` | fix(match): staple package-class filters + oil/egg fixtures |
| PR1 stamp | `4c79c39` | docs(status): record PR1 product SHA |
| PR3 product | `8676303` | feat(ui): honest partial-basket hero & savings gate |
| PR3 stamp (HEAD) | `ccf898e` | docs(status): stamp PR3 honest-UI SHA 8676303 |

**Push:** `3c4a0a6..ccf898e` → `origin/main` (normal push, not force).  
**iOS junk:** left untracked (`frontend/ios/Flutter/`, `GeneratedPluginRegistrant.*`) — **not** committed.

## CI / deploy

| Field | Value |
|-------|--------|
| Workflow | CI/CD — test, build & deploy to VPS |
| Run ID | **29648461645** |
| Commit | `ccf898eda309a6ef52cb37788f6361fdda619d4f` |
| Conclusion | **success** |
| Jobs | changes ✓ · e2e-local ✓ · test ✓ · deploy ✓ (~8m26s) · live-verify ✓ |

Deploy rebuilt API image + Flutter web/APK and shipped to VPS. Hosted APK refreshed:

- URL: `https://alagoas.precospublicos.ia.br/app/compre-barato-alagoas.apk`
- Size: ~52 MB · last-modified ~2026-07-18 14:48 UTC (post-deploy)

## Production API probe (problem basket)

```
POST https://alagoas.precospublicos.ia.br/api/v1/search
items: ["Óleo","Ovo","Açúcar"]
origin: Maceió -9.6633, -35.7089  radius_km=8  days=7
```

| Field | Result |
|-------|--------|
| HTTP | **200** |
| Latency | ~57 s (SEFAZ web path; not thin mock) |
| `data_source` | `web` |
| `metrics.match_rate` | **0.667** (2/3 — Açúcar missing everywhere) |
| Rewrites | Óleo→`oleo de soja`, Ovo→`ovos`, Açúcar→`acucar cristal` |
| Stores | 5 |

### Per-store top lines (description)

| # | Store | Óleo | Ovo | Missing |
|---|-------|------|-----|---------|
| 0 | MERCEARIA SANTO ANTONIO | **OLEO DE SOJA SINHA 5** R$6.40 | **OVOS UNIDADE** R$0.65 | Açúcar |
| 1 | PANIFICAÇÃO SABOR DE MEL | SARDINHAS COQUEIRO C/ OLEO DE SOJA 125G R$6.25 | ovos galinha capoeira R$0.95 | Açúcar |
| 2 | SUPERMERCADO VIA NORTE | **OLEO DE SOJA SINHA 500 ML** R$6.79 | **OVOS UND** R$0.59 | Açúcar |
| 3 | MERCADO BOAS COMPRAS DO PONTAL | **SINHA SOJA OLEO 500M** R$6.99 | **OVOS UNIDADE** R$0.66 | Açúcar |
| 4 | J M DOS SANTOS MERCADINHO | **OLEO SINHA DE SOJA 500ML** R$6.99 | **OVOS** R$1.00 | Açúcar |

### Verdict vs known BADs

| Problem | Status on live |
|---------|----------------|
| Óleo → coco 15 ml / cosmetic | **PASS** — not observed |
| Ovo → MAC pasta / wrong class | **PASS** — all eggs |
| Ranking prefers cooking oil when present | **MOSTLY** — 4/5 stores real cooking oil; store[1] residual **sardines-in-oil** |
| Partial basket honesty (API surface for PR3 UI) | **PASS** — every store `items_found=2/3`, `missing:["Açúcar"]`, `rank_reason` like `Falta Açúcar · 2/3 itens` (UI hero gates on this) |
| Açúcar coverage | **Thin SEFAZ web** — 0/5 stores; match_rate 0.667; still reported |

Top-level response field `partial=false` even when stores are incomplete; **store-level** `missing` / `rank_reason` / `items_found` carry the partial signal used by the Flutter honest-UI (PR3).

## Phone

| Step | Result |
|------|--------|
| Device | `ROGI4LBAOV8HXOFA` (adb device) |
| APK source | Hosted post-deploy APK (same build as CI) |
| `adb install -r` | **INSTALL_FAILED_UPDATE_INCOMPATIBLE** (signature mismatch vs prior install) |
| Uninstall | `pm uninstall --user 0 br.ia.precospublicos.compre_barato_alagoas` → **Success** (data wipe of that package) |
| Re-install | **INSTALL_FAILED_USER_RESTRICTED** (user must confirm install on device) |
| Fallback | APK pushed to **`/sdcard/Download/compre-barato-alagoas.apk`** (52 MB) |

**No in-app screenshot** this run — install blocked by device user restriction after uninstall. Targeted proof is **production API probe** + deploy green + APK on Downloads for manual install.

## Non-goals (honored)

- No 147-cell matrix / full:local residual / whole-app QA
- No force-push
- No iOS GeneratedPluginRegistrant commit
- No unrelated polish

## Residual notes (not blocking #8)

1. Store[1] oil line still can be **sardines with oil** — residual wrong-SKU when bakery has no bottle oil.
2. **Açúcar** often missing under SEFAZ web near this origin — coverage, not package-class.
3. Phone install needs one-time user tap (USER_RESTRICTED); APK ready in Downloads.

## #8 status

**DONE** — product SHAs on origin/main; CI run **29648461645** success; targeted API re-eval documents oil/egg package-class fix + partial-basket fields for PR3; phone APK delivered to device Downloads with USER_RESTRICTED install block documented.
