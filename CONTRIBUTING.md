# Contributing

Thanks for helping improve **Compre Barato Alagoas** (public SEFAZ-AL price intermediary for Alagoas).

## Before you start

- Read [`AGENTS.md`](AGENTS.md) if you are an automated agent (batch small work; branch → PR; do not merge on agent authority without review).
- Read [`SECURITY.md`](SECURITY.md) before filing security issues.
- Public product docs: `docs/` (served at `docs.alagoas.precospublicos.ia.br` in production).

## Development basics

| Area | Entry |
|------|--------|
| Backend | `backend/` — FastAPI, Redis mandatory; `USE_MOCK_SEFAZ` / `USE_MOCK_LLM` for local |
| App | `frontend/` — Flutter (web primary; Android APK; iOS scaffold incomplete — needs Mac) |
| Admin | `admin-frontend/` — static SPA, `ADMIN_TOKEN` bearer |
| Docs | `docs/` — static HTML |
| Deploy | `deploy/` — compose + nginx vhosts + `deploy.sh` |
| E2E | `e2e/` — Puppeteer/Chromium; see `e2e/README.md` (WebKit gap on iPhone Safari) |

Copy `.env.example` → `.env` for local/server config; **never commit** `.env`, keystores, or real App Links fingerprints.

## Pull requests

1. Branch from latest `main`; one logical batch per PR when possible.
2. Describe what changed, issues fixed (`Fixes #…` / `Partial #…`), and how you tested.
3. Run what you can locally:
   - Backend: `cd backend && pytest` (when deps available)
   - Android/deploy structure: `scripts/check_android_deploy_hardening.sh`
   - iOS plist seeds (Linux): `python3 scripts/verify_ios_info_plist.py`
   - Full product smoke: `e2e/run_local.sh` (substantial user-facing batches)
4. Do not force-push `main`, skip hooks without cause, or include secrets.

## LGPD / privacy

- Device token and admin token are credentials — never log or paste them into issues/PRs.
- Basket/search strings can be sensitive; minimize in screenshots and Sentry samples.
- Policy/consent version bumps: follow `docs/ops-policy-version-release.md` (#283).

## iOS / Android operator blockers

Some work requires Mac/Xcode, Play Console, real signing certs, or Apple Team ID. Document those in issues/PRs; do not pretend Linux-only fixes complete App Store / Play / Universal Links verification.
