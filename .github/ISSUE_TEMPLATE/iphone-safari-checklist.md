---
name: iPhone Safari / WebKit checklist
about: Manual QA on real iPhone Safari or WKWebView (CI uses Chromium only — issue #16)
title: "iPhone QA: "
labels: bug
---

<!--
CI headless e2e (e2e/full.js, smoke.js, live.js) runs Puppeteer/Chrome with
isMobile + 390x820 — NOT Safari/WebKit. Use this checklist after deploy or when
touching safe-area, PWA, forms, or iOS permissions. Close when all items pass
or are waived with reason.
-->

## Environment
- [ ] Device / iOS version: _______________
- [ ] Safari (and/or Add to Home Screen PWA)
- [ ] URL: `https://alagoas.precospublicos.ia.br` (or staging)

## Layout & safe area
- [ ] No content clipped under notch / status bar / home indicator (safe-area insets)
- [ ] `100vh` / full-height screens scroll correctly (prefer `dvh` / `-webkit-fill-available` behavior)
- [ ] Fixed headers/footers do not cover primary actions
- [ ] Tap targets usable with thumb (no mis-taps on edge controls)

## Forms & zoom
- [ ] Inputs with `font-size` >= 16px (or equivalent) — no unwanted focus zoom on iOS
- [ ] Keyboard does not permanently hide submit / primary CTA
- [ ] Voice / search field usable in Safari if applicable (web may lack mic depending on context)

## PWA / install
- [ ] Share -> **Add to Home Screen** works; icon + title sensible
- [ ] Standalone mode: no broken nav; back/share still reachable
- [ ] Offline/error states acceptable (no white flash / infinite spinner only)

## Permissions & links (Safari / app context)
- [ ] Location fallback sensible when denied (Maceio default / approximate)
- [ ] External maps / Uber / 99 open or fall back to HTTPS (no silent no-op)
- [ ] Shared `/abrir` links open correctly (web or app if installed)

## Docs / admin (if changed)
- [ ] `docs.alagoas...` sidebar usable on narrow Safari
- [ ] `admin.alagoas...` login + tabs usable; fixed chrome respects safe-area

## Evidence
- Screenshots or short notes: _______________
- Related PR / issue: _______________

## Waivers
List any skipped items and why (e.g. feature not on web): _______________
