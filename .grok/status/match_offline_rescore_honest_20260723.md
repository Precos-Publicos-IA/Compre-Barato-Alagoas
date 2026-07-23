# Offline rescore notes (Phase 4)

- **When:** 2026-07-23T19:51:58.386864+00:00
- **Input:** `/code/alagoas/Compre-Barato-Alagoas/.grok/status/match_eval_100_honest.json`
- **min_keep:** 0.35

## Counts (4-S2)

| metric | value |
|--------|------:|
| n | 91 |
| still_bad | 0 |
| now_empty_or_reject | 20 |
| regressed_good_to_bad | 10 |
| good_to_good | 61 |
| poison_pairs_all_ok | True |

## Transitions

- `bad→now_empty_or_reject`: 20
- `good→good`: 55
- `good→now_empty_or_reject`: 2
- `good→still_bad`: 8
- `good→weak`: 6

## Poison pairs (4-S3)

- **OK** `queijo` → `PAO DE QUEIJO CONGELADO 1KG` (expect=reject_or_empty, score=0.04, align=reject, label=bad)
- **OK** `peito de frango` → `OVOS BRANCOS UND` (expect=reject_or_empty, score=0.04, align=reject, label=bad)
- **OK** `peito de frango` → `PASTEL DE FRANGO` (expect=reject_or_empty, score=0.04, align=reject, label=bad)
- **OK** `frango` → `PASTEL DE FRANGO` (expect=reject_or_empty, score=0.04, align=reject, label=bad)
- **OK** `ovo` → `MACARRAO COM OVOS 500G` (expect=reject_or_empty, score=0.04, align=reject, label=bad)
- **OK** `queijo` → `QUEIJO MUSSARELA KG` (expect=keep_good, score=0.5, align=ok, label=good)
- **OK** `peito de frango` → `PEITO DE FRANGO KG` (expect=keep_good, score=0.5, align=ok, label=good)
- **OK** `arroz` → `ARROZ BRANCO 1KG` (expect=keep_good, score=0.92, align=ok, label=good)

**4-S3 residual:** regressed_good_to_bad=10; poison_failed=0
