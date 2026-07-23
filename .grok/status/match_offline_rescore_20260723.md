# Offline rescore notes (Phase 4)

- **When:** 2026-07-23T19:52:40.983285+00:00
- **Input:** `/code/alagoas/Compre-Barato-Alagoas/backend/tests/fixtures/match_offline_tops.json`
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

## 4-S3 gate

- Live-bad (wrong_class) → emptied: **20**; still_bad: **0**
- Poison pairs all ok: **True** (failed=0)
- regressed_good_to_bad: **10** (live `pass` tops now hard-rejected; often stricter head on weak prior tops, not necessarily true quality loss — list residuals in notes when >0)

**4-S3 PASS:** pre-head wrong_class tops emptied (0 still_bad); poison pairs hard-reject or keep as expected.
Documented residual: 10 live-pass rows now reject on top1 (stricter scorer vs honest-eval heuristic). Bound accepted for Phase 4.

## Residual live-pass → offline bad (documented bound)

| query | top1 now | score | why |
|-------|----------|------:|-----|
| manteiga | `PIPOCA CORINGA SABOR MANTEIGA FD 10X20X15G` | 0.04 | head reject |
| requeijão | `SALG SNAKS GRATICIA 27G REQUEIJAO` | 0.04 | head reject |
| presunto | `SALG MILHO FLITS SABOR PRESUNTO 28GR` | 0.04 | head reject |
| atum | `WHISKAS  SH 85G AD ATUM 1` | 0.04 | head reject |
| cenoura | `PAO DE CENOURA 25G` | 0.04 | head reject |
| limão | `SUCO DE LIMAO CORTESIA` | 0.04 | head reject |
| laranja | `SUCO DE LARANJA CORTESIA` | 0.04 | head reject |
| abóbora | `PLUTONITA CABECA DE ABOBORA C/42 UN` | 0.04 | head reject |
| amendoim | `DOCE DE AMENDOIM SANTA HELENA PACOQUITA 15G` | 0.04 | head reject |
| creme dental | `CRE.DENTAL ORAL-B 3D` | 0.04 | head reject |
