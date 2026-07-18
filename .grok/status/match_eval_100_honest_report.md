# Honest match eval — shopping_list_100

- **Worker:** `W-eval-honest`
- **API:** `https://alagoas.precospublicos.ia.br`
- **Evaluated at (UTC):** 2026-07-18T16:28:44.310715+00:00
- **Concurrency:** 1 (max 2)
- **Retry backoff (s):** 3.0
- **Timeout (s):** 150.0
- **Fixture:** `/code/alagoas/Compre-Barato-Alagoas/backend/tests/fixtures/shopping_list_100.json`

## Summary

| Metric | Count |
|--------|------:|
| total | 100 |
| pass | 71 |
| wrong_class | 20 |
| missing_after_retry | 9 |
| upstream_error | 0 |
| found_count | 91 |
| retried_count | 9 |

### Latency (ms)

- p50: 11262.0
- p95: 22986.05
- min/max: 198 / 24374
- mean: 7852.36

### By category

| category | total | pass | wrong_class | missing_after_retry | upstream_error |
|----------|------:|-----:|------------:|--------------------:|---------------:|
| baby | 1 | 1 | 0 | 0 | 0 |
| bakery | 8 | 3 | 4 | 1 | 0 |
| beverages | 10 | 6 | 2 | 2 | 0 |
| cleaning | 8 | 2 | 3 | 3 | 0 |
| dairy | 12 | 10 | 2 | 0 | 0 |
| hygiene | 6 | 3 | 1 | 2 | 0 |
| meat | 12 | 10 | 2 | 0 | 0 |
| oils | 12 | 10 | 2 | 0 | 0 |
| pet | 1 | 1 | 0 | 0 | 0 |
| produce | 12 | 12 | 0 | 0 | 0 |
| snacks | 6 | 4 | 2 | 0 | 0 |
| staples | 12 | 9 | 2 | 1 | 0 |

## Failures / non-pass

- **id=6** `sal` → `missing_after_retry` http=200 ds=web stores=0 mr=0.0 retried=True   
- **id=7** `farinha de trigo` → `wrong_class` http=200 ds=web stores=5 mr=1.0 retried=False top=OVOS BRANCOS UND  reason=cross-query bleed: eggs returned for non-egg query
- **id=8** `farinha de mandioca` → `wrong_class` http=200 ds=web stores=5 mr=1.0 retried=False top=OVOS BRANCOS UND  reason=cross-query bleed: eggs returned for non-egg query
- **id=21** `queijo` → `wrong_class` http=200 ds=web stores=5 mr=1.0 retried=False top=OVOS BRANCOS UND  reason=cross-query bleed: eggs returned for non-egg query
- **id=22** `queijo mussarela` → `wrong_class` http=200 ds=web stores=5 mr=1.0 retried=False top=OVOS BRANCOS UND  reason=cross-query bleed: eggs returned for non-egg query
- **id=29** `molho de tomate` → `wrong_class` http=200 ds=web stores=5 mr=1.0 retried=False top=OVOS BRANCOS UND  reason=cross-query bleed: eggs returned for non-egg query
- **id=36** `caldo de galinha` → `wrong_class` http=200 ds=web stores=5 mr=1.0 retried=False top=OVOS BRANCOS UND  reason=cross-query bleed: eggs returned for non-egg query
- **id=38** `peito de frango` → `wrong_class` http=200 ds=web stores=5 mr=1.0 retried=False top=OVOS BRANCOS UND  reason=cross-query bleed: eggs returned for non-egg query
- **id=42** `salsicha` → `wrong_class` http=200 ds=web stores=2 mr=1.0 retried=False top=Pipoca Bokus sal 30g  reason=generic: description has no primary intent token
- **id=61** `pão` → `wrong_class` http=200 ds=web stores=5 mr=1.0 retried=False top=OVOS BRANCOS UND  reason=cross-query bleed: eggs returned for non-egg query
- **id=62** `pão de forma` → `wrong_class` http=200 ds=web stores=5 mr=1.0 retried=False top=OVOS BRANCOS UND  reason=cross-query bleed: eggs returned for non-egg query
- **id=63** `pão francês` → `wrong_class` http=200 ds=web stores=5 mr=1.0 retried=False top=OVOS BRANCOS UND  reason=cross-query bleed: eggs returned for non-egg query
- **id=66** `bolacha` → `missing_after_retry` http=200 ds=web stores=0 mr=0.0 retried=True   
- **id=68** `pão de queijo` → `wrong_class` http=200 ds=web stores=5 mr=1.0 retried=False top=OVOS BRANCOS UND  reason=cross-query bleed: eggs returned for non-egg query
- **id=71** `água` → `wrong_class` http=200 ds=web stores=5 mr=1.0 retried=False top=OVOS BRANCOS UND  reason=cross-query bleed: eggs returned for non-egg query
- **id=75** `cerveja` → `missing_after_retry` http=200 ds=web stores=0 mr=0.0 retried=True   
- **id=77** `achocolatado` → `missing_after_retry` http=200 ds=web stores=0 mr=0.0 retried=True   
- **id=78** `água de coco` → `wrong_class` http=200 ds=web stores=5 mr=1.0 retried=False top=OVOS BRANCOS UND  reason=cross-query bleed: eggs returned for non-egg query
- **id=79** `salgadinho` → `wrong_class` http=200 ds=web stores=2 mr=1.0 retried=False top=Pipoca Bokus sal 30g  reason=generic: description has no primary intent token
- **id=84** `barra de cereal` → `wrong_class` http=200 ds=web stores=5 mr=1.0 retried=False top=OVOS BRANCOS UND  reason=cross-query bleed: eggs returned for non-egg query
- **id=85** `sabão em pó` → `wrong_class` http=200 ds=web stores=5 mr=1.0 retried=False top=COCADA LEITE  reason=generic: description has no primary intent token
- **id=86** `detergente` → `missing_after_retry` http=200 ds=web stores=0 mr=0.0 retried=True   
- **id=87** `água sanitária` → `wrong_class` http=200 ds=web stores=5 mr=1.0 retried=False top=OVOS BRANCOS UND  reason=cross-query bleed: eggs returned for non-egg query
- **id=88** `amaciante` → `missing_after_retry` http=200 ds=web stores=0 mr=0.0 retried=True   
- **id=89** `desinfetante` → `missing_after_retry` http=200 ds=web stores=0 mr=0.0 retried=True   
- **id=92** `saco de lixo` → `wrong_class` http=200 ds=web stores=5 mr=1.0 retried=False top=OVOS BRANCOS UND  reason=cross-query bleed: eggs returned for non-egg query
- **id=93** `sabonete` → `missing_after_retry` http=200 ds=web stores=0 mr=0.0 retried=True   
- **id=94** `shampoo` → `missing_after_retry` http=200 ds=web stores=0 mr=0.0 retried=True   
- **id=96** `papel higiênico` → `wrong_class` http=200 ds=web stores=5 mr=1.0 retried=False top=PAPEL TOALHA MALU 2 ROLOS 100FOLHAS  reason=generic: description has no primary intent token

## Methodology notes

- Serial/low concurrency only (default 1, cap 2) — avoids SEFAZ stampede false empties.
- One retry on empty stores or match_rate=0 after short backoff; `missing_after_retry` only after that retry fails to find items.
- `upstream_error` = HTTP 429/5xx/non-200 or transport/timeout (not product missing).
- Prior parallel eval `f7ef373` is INVALID for coverage; do not compare raw missing rates to it.

