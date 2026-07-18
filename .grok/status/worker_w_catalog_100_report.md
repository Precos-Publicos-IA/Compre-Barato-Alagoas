# W-catalog-100 report

**Status:** DONE
**Worker:** W-catalog-100
**Date:** 2026-07-18

## Summary

Persisted a shared source-of-truth of **100** unique everyday PT-BR supermarket shopping-list query names (Alagoas/BR voice) for match-quality eval.

## Artifacts

| Path | Role |
|------|------|
| `backend/tests/fixtures/shopping_list_100.json` | Machine-readable (version, locale, region_hint, items[{id,query,category}]) |
| `backend/tests/fixtures/shopping_list_100.txt` | One query per line (100 lines) |

## Counts

- **Total items:** 100
- **Unique queries (after trim):** 100
- **Empty queries:** 0
- **locale:** pt-BR
- **region_hint:** Alagoas
- **version:** 1

## Category breakdown

| Category | Count |
|----------|------:|
| dairy | 12 |
| meat | 12 |
| oils | 12 |
| produce | 12 |
| staples | 12 |
| beverages | 10 |
| bakery | 8 |
| cleaning | 8 |
| hygiene | 6 |
| snacks | 6 |
| baby | 1 |
| pet | 1 |

## Hard cases included (prior eval pain points)

- óleo, ovo, ovos, açúcar, sal, café, macarrão, leite
- Related: óleo de soja, macarrão espaguete, leite integral/desnatado/em pó, café solúvel, feijão / feijão preto

## Notes

- Names are short list-style (what people type), not formal catalog titles.
- Balanced across staples, dairy/eggs, oils/condiments, meat, produce, bakery, beverages, snacks, cleaning, hygiene, baby/pet — not 80 arroz variants.
- **Did not** call production SEFAZ/API (eval is W-eval).
- **Did not** change relevance.py matching code.
