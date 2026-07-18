# Worker W-pr1 report — PR1 match package-class filters

**Date:** 2026-07-18  
**Worker:** W-pr1  
**Project lock:** Compre Barato Alagoas only  

## Goal
Fix wrong-SKU matches for cooking oil and eggs (phone eval 2026-07-18): coco 15 ml under Oleao, pasta MAC OVOS under Ovo, ranking crowning tiny packs.

## Changes

| File | Change |
|------|--------|
| backend/app/services/rag/relevance.py | Hard reject coco + <50 ml for plain oleo; MAC/MACARR/pasta as egg noise; ovo/ovos synonym; package-class ranks + priors; learn-guard helpers |
| backend/app/services/ranking.py | Best-offer key: package class then unit_price then freshness then package price (D1) |
| backend/app/services/normalization/quantity.py | Bare DZ/DUZIA -> 12 un |
| backend/app/services/llm/verifier.py | D5: min_score_to_learn=0.50 + in-class package check before RAG learn |
| backend/tests/test_relevance_quality.py | Goldens: reject coco/MAC; keep soja 900 ml, acucar 1 kg, bandeja |
| backend/tests/test_ranking.py | Package class beats cheap unparsed tiny oil; dozen over single egg |
| backend/tests/test_quantity.py | Bare DZ dozen |
| docs/improvement-plan-search-quality.md | Authoritative plan (tracked) |

## Acceptance probes

| Query | Description | Result |
|-------|-------------|--------|
| oleo | OLEO COCO COPRA 15ML | REJECT score < 0.2 |
| oleo | OLEO SOJA 900ML | KEEP score > 0.5 |
| ovo/ovos | MAC OVOS FURADINHO / MACARR C/OVOS | REJECT |
| ovo | OVOS BRANCOS BANDEJA C/12 | KEEP (ovo/ovos synonym) |
| acucar | ACUCAR CRISTAL 1KG | KEEP, class preferred |
| ranking oleo | 15 ml cheap package vs 900 ml | crowns 900 ml |

## Tests
Full suite green:
  cd backend && python3 -m pytest tests/ -q --tb=line

Focused also green: test_relevance_quality.py, test_ranking.py, test_quantity.py, test_rag_agents.py.

## Out of scope (not done)
- PR3 Flutter honest partial-basket UI
- Store catalog API
- PR2 match_score schema (optional follow-on)

## Commit
504eb38 on main.
