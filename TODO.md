# Compre Barato Alagoas — launch / product checklist

Tracking for the **public product** (not agent session status). Check items off as we go.
Agent delivery process lives under `.grok/` (autonomous dev cycle).

## Product

- [x] MVP live: search list → ranked stores → unit prices (SEFAZ public data)
- [x] Flutter app (web + Android); iOS scaffold in progress
- [x] Admin panel + docs site
- [x] Privacy / LGPD docs + opt-out for anonymous usage stats
- [ ] SEFAZ AppToken in production (GitHub secret → VPS `secrets/sefaz_app_token` on deploy)
- [ ] Zero-result UX: suggestions + honest empty states for spoken/typo queries
- [ ] Full viewport matrix green (see `e2e/qa_matrix.json`) with video + PNG critiques
- [ ] Physical-device Phase C routine documented for lab phones
- [ ] Optional: richer semantic cache / RAG pre-warm for scale

## Quality / ops

- [x] pytest + flutter unit tests
- [x] Headless e2e (`e2e/full:local`, `e2e/live`)
- [x] CI deploy to VPS on push to `main`
- [x] Security posture docs; OpenAPI UI off in production app nginx
- [ ] Matrix capture runners (per format VIDEO + quality-hold PNGs) beyond baseline suite
- [ ] iPhone Safari checklist run after high-risk web/PWA changes

## Brand & distribution

- [x] Live app: https://alagoas.precospublicos.ia.br
- [x] Docs: https://docs.alagoas.precospublicos.ia.br
- [ ] Android package distribution hardening / store path (as needed)
- [ ] iOS full Xcode target when ready

## Done (baseline)

- [x] Public repo + private ops repo split
- [x] MIT license + English developer docs
- [x] Autonomous dev cycle imported (`.grok/`)

---

*Hosting: VPS docker-compose behind nginx TLS. Secrets only in server `.env`.*
