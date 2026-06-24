# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows an informal **ship-by-PR** model (merged PRs to `main`
deploy via CI). Until tagged semver releases are routine, treat **merge date +
`GIT_SHA` / image tag** as the version identifier (`/health` may expose `git_sha`).

## [Unreleased]

### Added

- Community/ops docs: `SECURITY.md`, `CONTRIBUTING.md`, `SUPPORT.md`, this changelog (#277).
- Ops guides: `docs/ops-secret-encryption-key-rotation.md` (#282), `docs/ops-policy-version-release.md` (#283).
- Shared SEFAZ text normalization for mock + live HTTP clients (#279).
- Android optional `uses-feature` for mic/location (#281).
- PWA manifest `id` / `lang` / `categories` / `shortcuts` (#272 partial; screenshots still open).
- `e2e/ops_probes.js` for `/health`, `/api/v1/client-config`, `security.txt` (#278 partial).
- `deploy/well-known/security.txt` template for RFC 9116 contact pointer.

### Changed

- iOS scaffold README notes missing storyboards vs `Info.plist` references (#280).

## How to update this file

1. Add entries under **Unreleased** in the same PR as the change (preferred), or
2. Rely on descriptive PR titles and backfill here on significant deploys.
3. When cutting a named release, move **Unreleased** items into `## [YYYY-MM-DD]`
   and record the deploy `GIT_SHA`.
