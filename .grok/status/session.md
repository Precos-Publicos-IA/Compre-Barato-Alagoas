# Session status

Last update: 2026-07-18 **H DONE** — `efca61d` deployed + scoped smoke PASS

## Project lock
**HARD** Alagoas only.

## Goal
Honest match quality: F measured; G fixed RAG poison; H shipped and smoked.

## Phase
**Idle** — mission complete for A–H must-complete chain.

## Workers
| ID | Status |
|----|--------|
| F honest eval | **DONE** |
| G improve | **DONE** `efca61d` |
| **W-H-ship** | **DONE** CI `29652301027` + smoke 7/7 |

## Must-complete
| # | Status |
|---|--------|
| A–E | **DONE** |
| F honest 100 | **DONE** pass=71 wrong=20 missing=9 found=91 |
| G RAG/class bleed fix | **DONE** `efca61d` |
| **H** ship G + smoke | **DONE** — deploy green + scoped live smoke PASS |

## H evidence
- Product on main: `efca61d`
- CI/deploy: **success** https://github.com/Precos-Publicos-IA/Compre-Barato-Alagoas/actions/runs/29652301027
- Docs stamp run: success `29652307667` (`4ac9505`)
- Redis: flushed 99 `rag:effective_for:*` → 0 (SSH)
- Smoke: peito de frango, farinha de trigo, pão, queijo, papel higiênico, salsicha, sabão em pó → **7/7 PASS** (no OVOS BRANCOS top; higiênico≠toalha; no rewrite to ovos/sal/leite)
- Artifacts: `.grok/status/h_ship_live_smoke.json`, `worker_w_h_ship_report.md`

## Root cause fixed in G (live verified in H)
RAG cross-class rewrites (peito→ovos, salsicha→sal, sabão→leite, higiênico→toalha) blocked; prod Redis poison ZSETs cleared.

## Residual (not must-complete)
- 9 true SEFAZ `missing_after_retry` data gaps from F (sal, bolacha, cerveja, achocolatado, detergente, amaciante, desinfetante, sabonete, shampoo)
- Soft: `queijo` can still top `PAO DE QUEIJO` (not egg bleed)

## Next focus
Idle unless user opens new work. Do **not** start full 100 re-eval without explicit ask.
