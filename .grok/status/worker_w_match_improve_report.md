# W-match-improve report — P0 wrong_class relevance fixes

**Status:** **C DONE**  
**Worker:** W-match-improve  
**Date:** 2026-07-18  
**Evidence in:** `.grok/status/match_eval_100.json`, `worker_w_eval_100_report.md`  
**Prior PR1:** package-class óleo/ovo `504eb38`

## Product SHA

Recorded after commit in this cycle (see `session.md` **C DONE** line).

## Scope delivered

| Theme | Fix | Result (offline re-score of live top_lines) |
|-------|-----|-----------------------------------------------|
| **T1 Egg cross-bleed** | Hard reject egg SKUs when intent is not ovo/ovos; tighten web soft-pass floor | Eggs score 0 / ≤0.04 for non-egg queries → **dropped** (empty better than wrong eggs) |
| **sal snacks** | Salt staple + snack reject (`pipoca`/`castanha`/`S SAL`/`SALG…`); strict token match (no sal⊂salg) | Snacks ≤0.04; keeps `SAL REFINADO … 1KG` |
| **óleo saturado** | Reject saturado / mist / sard-atum-em-óleo; cooking type + early `oleo` | Live tops → **OLEO DE SOJA SOYA 900ML** |
| **feijão tempero** | Reject tempe/tempeiro/tempero; bean must be early primary | Live tops → **FEIJAO PT T1 1KG** |
| **açúcar candy** | Reject zero-açúcar / BIGBIG / festa sachet | Live tops → **ACUCAR CRISTAL…** (30 kg still present in set — class size residual) |
| **café junk** | Reject caramelo(s); spice-mix without coffee product cues | Live tops → **CAFE / CAFE P** (weak but not caramel/spice) |

**Out of scope (as tasked):** inventing SEFAZ coverage for empty produce; full matrix; live 100 re-eval (429).

## Code changes

| Path | Change |
|------|--------|
| `backend/app/services/rag/relevance.py` | PR2 hard rejects, stricter `_primary_index` / `_token_matches_word`, sal staple, noise caramelos/tempeiro/bigbig, farinha/barra allow when asked |
| `backend/app/services/sefaz/web_client.py` | Soft filter floor 0.20; drop last-resort ≤0.05 junk that re-introduced bleed |
| `backend/tests/test_relevance_quality.py` | Goldens from eval descriptions (egg bleed, sal, óleo, feijão, açúcar, café + filters) |

## Tests

```text
pytest tests/test_relevance_quality.py tests/test_ranking.py  → green
pytest -q (full backend) → green
```

## Offline re-score (wrong_class = 27, fixtures only)

Re-scored **stored** `top_lines` with new `score_description` (no live API).

| Outcome | Count | Notes |
|---------|------:|-------|
| Class-trap fixed (new top is on-class) | **8** | feijão×2, açúcar×2, óleo×2, café×2 |
| Eggs / junk correctly **emptied** | **16** | farinha, queijo, pão×4, água×2, molho, caldo, peito, barra, sanitária, saco, + sal snacks-only / salsicha / salgadinho when only junk in set |
| Residual class issues in fixture | **~1–3** | e.g. açúcar industrial 30 kg still highest among kept cristal lines (package-class sort residual, not wrong product class); café weak `CAFE P` |

**User-facing lie fixed:** non-egg queries no longer **rank** eggs when only eggs were returned — filter returns empty. Live egg bleed was ranking eggs; relevance now refuses them. Upstream still needs real farinha/queijo/pão cards from SEFAZ (coverage / cache / rewrite — not this worker).

## Residual (not C blockers)

1. **Coverage empties** (arroz/leite/macarrão/produce) — T3 from eval; separate from class filter.
2. **Sugar 30 kg** industrial pack still preferred among cristal if no 1 kg line in the set — package_class demotes but ranking of multi-store lines may need household size sort when both present.
3. **sal** with only snack SEFAZ head → empty (correct); needs table-salt hits in SEFAZ fetch variants.
4. **Cache** may still hold pre-fix web payloads until TTL; deploy + natural expiry (or flush) for live verify.

## Acceptance checklist

| Criterion | Status |
|-----------|--------|
| pytest green for relevance/ranking touched | **YES** |
| Commit product fix + tests | **YES** (see session SHA) |
| Report this file | **YES** |
| session.md C DONE + SHA | **YES** |
| Push if practical | attempted with commit |
| Offline re-score wrong_class | **YES** (this section) |
