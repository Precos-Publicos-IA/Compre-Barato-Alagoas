# W-re-critique-mobile report

**Date:** 2026-07-17  
**Role:** Honest re-critique of phone landscape V-CLIP-TEXT after `d2497c1`  
**Status:** DONE

## Scope
- Opened every cell previously BAD with **V-CLIP-TEXT** in `e2e/screenshots/viewports/matrix_critique.md` (15 landscape home/results/share across 5 formats)
- Portrait samples: `phone_portrait_01_home`, `phone_portrait_02_results`
- Criteria: `e2e/qa_success_criteria.json` (V-CLIP-TEXT, V-HOME-SEARCH, V-RESULTS-PRICES, V-SHARE-CTA, V-STATE-MATCH, V-FORM-FACTOR)
- QHD/4K V-FORM-FACTOR left as-is (desktop deprioritized; not re-opened to clear)

## Artifact freshness
| Set | mtime vs `d2497c1` (20:01) | Action |
|-----|---------------------------|--------|
| phone_android_landscape + phone_landscape home/results/share | ~19:58–19:59 (post-redesign subset capture) | Opened as-is |
| promax / samsung_ultra / rodin landscape | stale / incomplete prior shots | **Re-captured** 20:04 against `frontend/build/web` on :17990 |

## Verdict by cell

### Home (all 5 PhoneLandscape) — **V-CLIP-TEXT CLEARED**
| cell | evidence |
|------|----------|
| phone_android_landscape_01_home | chips + field + VER PREÇOS; no APK banner |
| phone_landscape_01_home | full chip row incl. Macarrão + CTA |
| phone_iphone_promax_landscape_01_home | chips Arroz–Banana + field + CTA (post-recapture) |
| phone_samsung_ultra_landscape_01_home | chips + recent + CTA |
| phone_rodin_landscape_01_home | chips + recent + CTA |

### Results / share — mixed
| cell | verdict | note |
|------|---------|------|
| phone_android_landscape_02/05 | **BAD: none** | R$ savings, COMPARTILHAR, MAIS BARATO, EDITAR LISTA in viewport |
| phone_landscape_02/05 | **BAD: none** | same dense results layout |
| promax/samsung/rodin _02_results | **BAD: V-STATE-MATCH** | ClientException to `https://alagoas.precospúblicos.ia.br/api/v1/search/stream` — not settled prices |
| promax/samsung/rodin _05_share | **BAD: V-SHARE-CTA** | no COMPARTILHAR; same error surface |

**Not product V-CLIP-TEXT:** error copy and CTAs (Tentar de novo / EDITAR LISTA) are fully readable. Failure is capture/API reachability (release web build bakes production API; this env cannot fetch it). Layout density for results is proven on android + phone_landscape PNGs that still show full prices.

### Portrait samples
- home: staple grid + elevated search + VER PREÇOS — still GOOD / BAD: none  
- results: full savings hero + prices + actions — still GOOD / BAD: none  

### QHD/4K (unchanged)
- qhd_01_home, qhd_06_admin, 4k_01_home, 4k_06_admin — V-FORM-FACTOR residual kept

## open_bads_matrix

| before | after |
|-------:|------:|
| 19 (15 V-CLIP landscape + 4 FORM) | **10** (6 API-state landscape + 4 FORM) |

**Product V-CLIP-TEXT phone landscape residual: 0**

## Remaining product / process gaps (do not invent PASS)
1. **6 capture BADs** on promax/samsung/rodin results+share until re-capture with a reachable API (local `API_BASE_URL` dart-define, or network path to production).
2. **4 desktop V-FORM-FACTOR** on QHD/4K home/admin — product residual, user deprioritized.
3. Horizontal chip overflow (partial last chip) is intentional scroll row — not counted as V-CLIP-TEXT of primary prices/CTAs.

## Files updated
- `e2e/screenshots/viewports/matrix_critique.md` (CRITIQUE lines + open_bads table)
- `.grok/status/a6_open_bads.txt`
- `.grok/status/session.md`
- `.grok/status/worker_w_re_critique_mobile_report.md` (this file)
- Re-captured PNGs under `e2e/screenshots/viewports/phone_{iphone_promax,samsung_ultra,rodin}_landscape_{01_home,02_results,05_share}.png`

## Final count
**open_bads_matrix = 10** (matches critique file BAD lines after edits)
