---
name: app-input-e2e
description: >
  Enforce full keyboard, mouse, and touch support on every product surface for
  Compre Barato Alagoas. Use when changing UI, search, results, map, settings,
  admin, docs, voice, share, or window scaling; when the user mentions controls,
  keyboard, mouse, touch, e2e, input, or playtesting; or runs /app-input-e2e.
  Adapted from latest autonomous-dev-cycle game-input-e2e (2026-07-17).
---

# App input E2E (Compre Barato Alagoas)

## Hard rule

**Every user-facing surface must work with keyboard, mouse, AND touch** where the
platform allows. No dead-ends where only one input works. Treat regressions as
blockers before claiming "done".

## Parallelism & tasks

**Authority:** **`ui-viewport-qa`** → *Parallel vs serial* (criteria 1–9, task map).

**PASS/FAIL authority:** **`e2e/qa_success_criteria.json`** — open before any
CRITIQUE/VIDEO line; cite criterion ids on BAD lines.

**Short form — parallel OK:** matrix units (`CONCURRENCY=<N>`); pipeline A4b ∥ A6
per finished unit; critique batches; build wait overlapping read-only work.

**Short form — serial:** tests → build/serve → A4; all reviews → A7 → push →
deploy → live phone. Patch → rebuild → full retest.

**Chain rule:** when a step finishes, start the next required step. **Trust
gates:** true A7 PASS → Phase B without waiting for the user. Commit on **`main`**
after A7 (see `AGENTS.md`); do not reintroduce PR spam.

## Target surfaces

Every format in `e2e/qa_matrix.json`. Never treat 1366×768 as tablet.

| Class | Typical CSS | Notes |
|-------|-------------|-------|
| Desktop4k | 2560×1440, 3840×2160 | Comfortable UI |
| Desktop1080 | 1280×720 … 1920×1080, **1366×768** | Keyboard/mouse |
| Tablet V/H | 768×1024, 1024×768, 820×1180 | Touch-first |
| Phone V/H | 360×800, 390×844, 430×932 + landscapes | Primary audience |

## Screens checklist

| Screen | Keyboard | Mouse | Touch |
|--------|----------|-------|-------|
| Home / search | Type; Enter/submit | Click + submit | Tap field, type, submit |
| Results | Focus actions; Esc back | Click store/share | Targets ≥48px |
| Map | Focus / Esc | Pan/zoom clickable | Drag; clear of notches |
| Settings / privacy | Focus toggles | Click toggles/links | Fat-finger safe |
| Share / cloud | Activate CTA | Click share | Tap share |
| Admin | Token + Enter | Full click path | Best-effort tablet |
| Docs | Tab links | Click nav | Tap nav |

### Product notes

- Search: paste + IME (pt-BR).
- Voice: optional; never block text search.
- Location denied: degrade gracefully.
- Admin: keyboard login + mouse required.
- Product UI copy is pt-BR.

## When you change input or UI

1. Prefer shared helpers in `frontend/lib/core/` and feature folders.
2. Keyboard + pointer on desktop; touch targets ≥48 CSS px on handheld.
3. Flutter web: focus + semantics.
4. Readable at phone landscape and laptop_hd.
5. Do not clip prices, store names, or primary CTAs.

## Visual QA

Enforced by **`ui-viewport-qa`** (process) + **`e2e/qa_success_criteria.json`**
(PASS/FAIL). Ship order: Phase A (local matrix pipeline) → Phase B (push main +
deploy.yml) → Phase C (physical phone if present).

```bash
(cd backend && pytest -q)                 # when backend/ changes
# Flutter is product UI — keep in A1. Host may need Flutter SDK installed.
(cd frontend && flutter test)             # required when frontend/ changes
(cd frontend && flutter build web --release)
cd e2e && npm install && npm run full:local   # baseline ship bar (+ criteria critiques)
# Full 147-cell matrix is aspirational until runners land; see ui-viewport-qa.
# A7 then: git push origin main; gh run watch; npm run live
```

## Do not ship if

- Phase A incomplete (critiques/criteria gate skipped)
- Search cannot submit via keyboard
- Results spinner forever / blank after search
- Prices/CTAs unreadable on phone landscape
- Touch cannot start search or open map/settings
- Open criterion BADs in critiques

## Product note

Unit prices and rankings stay honest when fixing UI — do not hide data age or
empty states just to pass layout.
