# W-ship-D report — CI/deploy watch + scoped re-eval

**Status:** **D DONE**  
**Worker:** W-ship-D  
**Date:** 2026-07-18  
**Product SHA:** `5853031` (`fix(match): P0 relevance gates from match_eval_100 wrong_class`)  
**Tip SHA:** `0b0ca88` (docs stamp; includes `5853031` as ancestor)

## 1. Git / origin

| Check | Result |
|-------|--------|
| Branch | `main` |
| `HEAD` == `origin/main` | **YES** (`0b0ca88`) |
| `5853031` ancestor of HEAD | **YES** |
| Dirty tree | only local status/session + gitignored eval shards (not product) |

## 2. CI / deploy for `5853031`

| Run | SHA | Conclusion | URL |
|-----|-----|------------|-----|
| **Product** `29650180694` | `5853031` | **success** | https://github.com/Precos-Publicos-IA/Compre-Barato-Alagoas/actions/runs/29650180694 |
| Docs stamp `29650184336` | `0b0ca88` | **success** | https://github.com/Precos-Publicos-IA/Compre-Barato-Alagoas/actions/runs/29650184336 |

### Product run jobs (`29650180694`)

| Job | Result |
|-----|--------|
| changes | success |
| test (pytest) | success |
| e2e-local | success |
| deploy (API image → VPS) | success (~2m; Flutter skipped — backend-only path) |
| live-verify | success (~36s) |

**Deploy note:** API image rebuilt and shipped; Flutter web/APK skipped (path filter — match fix is backend).

## 3. Scoped re-eval

### 3a. Offline re-score (primary)

Re-scored stored `top_lines` from `.grok/status/match_eval_100.json` with current `score_description(user, term, desc)` on tree at `5853031` / `0b0ca88`. **No live API.**

| Metric | Value |
|--------|------:|
| wrong_class input | **27** |
| Fixed on-class new top | **8** |
| Emptied (junk/eggs correctly dropped) | **19** |
| Residual wrong_class after re-score | **0** |

**Fixed on-class (examples):**

| Query | Old top | New top |
|-------|---------|---------|
| feijão / feijão preto | TEMPE.PARA FEIJAO… | FEIJAO PT T1 1KG OF3 |
| açúcar / açúcar demerara | BIGBIG ZERO ACUCAR… | ACUCAR CRISTAL ESPECIAL FORMOSO 30KG |
| óleo / óleo de soja | OLEO SATURADO 1LT | OLEO DE SOJA SOYA 900ML |
| café / café solúvel | Coracao, Cafe, Canela | CAFE P |

**Emptied correctly:** egg cross-bleed on farinha/queijo/pão/água/etc.; sal snacks-only set → empty (better than wrong class).

**Critical staples offline (subset):**

| Query | Offline new top | Notes |
|-------|-----------------|-------|
| óleo | OLEO DE SOJA SOYA 900ML | fixed |
| feijão | FEIJAO PT T1 1KG OF3 | fixed |
| açúcar | ACUCAR CRISTAL… 30KG | class OK; pack-size residual |
| café | CAFE P | weak but on-class |
| ovo | OVOS EXTRA STA MARIA LUNA UN | was already pass |
| sal | empty | snacks rejected; needs salt SEFAZ coverage |
| farinha / pão | empty | egg junk dropped; needs real coverage |

### 3b. pytest goldens

```text
pytest tests/test_relevance_quality.py  → 27 passed
```

### 3c. Live probe (attempted — **429**)

Target: 8 critical queries `sal, óleo, feijão, açúcar, café, farinha, pão, ovo` via `POST /api/v1/search` (Maceió).

| Result | Detail |
|--------|--------|
| First query `sal` | **HTTP 429** in 584ms |
| Body | `{"detail":"Limite diário de buscas atingido. Tente novamente amanhã."}` |
| Further probes | **STOPPED** (task: do not burn quota) |
| Artifact | `.grok/status/ship_d_live_probe.json` |

**Reliance for D:** offline re-score (0 residual wrong_class) + CI green (pytest + e2e-local + deploy + live-verify) + prior C offline report. Live product behavior after deploy cannot be re-sampled until daily search budget resets; cache TTL may still serve pre-fix payloads for a while.

## 4. Out of scope (as tasked)

- Full 100 live re-eval
- Full 147-cell matrix
- Phone / integration_test

## 5. Residual (not D blockers)

1. **Daily rate limit** — live match probes blocked until tomorrow.
2. **Coverage empties** (arroz/leite/macarrão/produce/farinha/pão after egg filter) — SEFAZ coverage / fetch, not relevance gate.
3. **Sugar 30 kg** industrial pack preferred among cristal lines when no 1 kg in set.
4. **sal** empty when only snack heads in fixture/cache.
5. **Cache** may hold pre-`5853031` web payloads until TTL.

## Acceptance

| Criterion | Status |
|-----------|--------|
| main == origin/main includes 5853031 | **YES** |
| CI/deploy success for product push | **YES** run `29650180694` |
| Scoped offline re-eval | **YES** 8 fixed / 19 emptied / 0 residual |
| Live probe if not 429 | **429** documented; offline + CI relied on |
| Report this file | **YES** |
| session.md D DONE | **YES** (updated with this ship) |
