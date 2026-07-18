# Browser function re-eval (no phone required)

**Date:** 2026-07-18  
**Operator:** Phone not required — browser is enough for functionality QA.

## Method
Puppeteer against live `https://alagoas.precospublicos.ia.br`:
1. App loads + Flutter mounts
2. Deployed `main.dart.js` contains PR3 copy (`Encontramos`, `COMPARTILHAR BUSCA` / `ECONOMIA`)
3. Same-origin `POST /api/v1/search` for `Óleo`, `Ovo`, `Açúcar` (Maceió)
4. Share list deep link loads

Screenshots: `e2e/screenshots/func-01-home.png`, `func-02-share-list.png`, `func-03-home-end.png`

## Results — **11/11 PASS**

| Check | Result |
|-------|--------|
| App 200 + Flutter | PASS |
| PR3 strings in bundle | PASS |
| Search 200, 5 stores | PASS |
| No coco 15 ml as óleo | PASS (0) |
| No MAC pasta as ovo | PASS (0) |
| Cooking oil + eggs present | PASS (oil=5, egg=5) |
| Share list URL | PASS |

Sample top lines: `OLEO DE SOJA SINHA 500 ML`, `OVOS UND`, `ACUCAR CAETE BRANCO 1 KG`.  
`match_rate=1.0` on this run (all 3 items found at some stores).

## Phone
Optional only. No adb install needed for function acceptance.
