# W-H-ship report — deploy G + scoped live smoke

**Status:** **H DONE**  
**Worker:** W-H-ship  
**Date:** 2026-07-18  
**Product SHA:** **`efca61d`** (`fix(match): block RAG cross-class rewrites causing egg/class bleed`)  
**Status tip at start:** `4ac9505` (docs stamp G DONE)

## 1. Confirm on origin/main

| Check | Result |
|-------|--------|
| `efca61d` ancestor of `origin/main` | **YES** |
| `origin/main` at start | `4ac9505` (includes `efca61d`) |
| Product commit message | `fix(match): block RAG cross-class rewrites causing egg/class bleed` |

## 2. CI / deploy

| Run | Commit | Conclusion | URL |
|-----|--------|------------|-----|
| **29652301027** | `efca61d` product fix | **success** | https://github.com/Precos-Publicos-IA/Compre-Barato-Alagoas/actions/runs/29652301027 |
| 29652307667 | `4ac9505` docs stamp | **success** | https://github.com/Precos-Publicos-IA/Compre-Barato-Alagoas/actions/runs/29652307667 |

Jobs on product run `29652301027` (all green):

- changes
- e2e-local
- test (pytest)
- deploy (API image + ship to VPS; Flutter web/APK skipped by path filter)
- live-verify

## 3. Optional Redis flush (done)

SSH: `viny-claude@146.0.76.230` with `~/.ssh/viny-claude`.

| Step | Result |
|------|--------|
| Before | **99** keys `rag:effective_for:*` |
| Confirmed poison | e.g. peito/farinha/pão → `ovos` (970); queijo → `ovos` (776); sabão em pó → `leite` (58) |
| After `DEL` scan | **0** keys |
| DBSIZE after | 1026 (other keys intact) |

Lookup filter would have blocked poison anyway; clean slate avoids stale ZSETs.

## 4. Scoped live smoke (CONCURRENCY=1)

**Not** full 100 eval. Probes only (post-deploy, post-flush):

API: `https://alagoas.precospublicos.ia.br`  
Artifact: `.grok/status/h_ship_live_smoke.json`  
Summary: **pass=7 fail=0**

| Query | HTTP | Top line | `search_rewrites` | Asserts |
|-------|------|----------|-------------------|---------|
| peito de frango | 200 | CF. PEITO FRANGO | → `peito frango` | no OVOS BRANCOS top; no poison rewrite |
| farinha de trigo | 200 | FARINHA TRIGO FARINA | → `farinha trigo` | same |
| pão | 200 | PAO SIRIO MINI | → `pao frances` (benign) | same |
| queijo | 200 | PAO DE QUEIJO | (none) | no egg rewrite / no OVOS top |
| papel higiênico | 200 | PAPEL HIGIENICO PIMPO NEUTRO | (none) | **not** papel toalha |
| salsicha | 200 | SALSICHA KG | (none) | no → sal |
| sabão em pó | 200 | SABAO EM PO BRISA LAVANDA 400G | (none) | no → leite |

Assert rules applied:

- No `OVOS BRANCOS` as top for non-egg queries
- No `papel toalha` preferred for `papel higiênico`
- No cross-class rewrite to ovos/sal/leite (or papel toalha for higiênico) in `metrics.search_rewrites`

### Soft residual (not H fail)

`queijo` top line `PAO DE QUEIJO` is cheese-adjacent bread, not the G egg/class poison theme. Out of H scope.

## 5. Explicit non-goals (respected)

- No full 100 live eval
- No full matrix
- No lab IPs committed

## Acceptance

| Criterion | Status |
|-----------|--------|
| `efca61d` on origin/main | **YES** |
| CI/deploy green for product push | **YES** run `29652301027` |
| Scoped smoke 7/7 | **YES** |
| Redis flush optional | **DONE** (99→0) |
| Report + session H DONE + push | **YES** (this commit) |
