# Third-party notices & attributions

This project (Compre Barato Alagoas / Preços Públicos IA) is licensed under the
[MIT License](LICENSE). It depends on external data sources, libraries, and
vendored assets that carry their own terms. This file is a **human-maintained**
summary for operators, store listings, and forks (#291). It is not a substitute
for each upstream `LICENSE` file.

A Portuguese product-facing page mirrors this content: [`docs/terceiros.html`](docs/terceiros.html).

## Data sources

| Source | Role | Notes |
|--------|------|--------|
| **SEFAZ-AL — Economiza Alagoas** (API pública de NFC-e) | Authoritative price/offer data in production (`USE_MOCK_SEFAZ=false`) | Government public API; requires operator-issued access token (server-side only). Terms and acceptable use are governed by SEFAZ-AL / Estado de Alagoas — consult their portal and token issuance process. This app is an intermediary; it does not own SEFAZ data. |
| **Mock SEFAZ catalog** (`backend/app/data/mock_sefaz.json`) | Deterministic local/dev data | Project-authored synthetic data for tests; not real fiscal records. |

## Maps & geolocation

| Component | Role | Attribution / terms |
|-----------|------|---------------------|
| **OpenStreetMap** contributors | Map tiles via `flutter_map` / OSM tile servers | © OpenStreetMap contributors; [ODbL](https://www.openstreetmap.org/copyright). UI should surface OSM attribution (issue #164). |
| **Geolocator / platform location APIs** | Optional user location (falls back to Maceió) | Platform/OS permission and privacy policies apply; location is optional for core search. |

## Application runtime (high level)

| Area | Examples | License (typical) |
|------|----------|-------------------|
| **Flutter / Dart SDK & engine** | App UI (web, Android; iOS scaffold incomplete) | [Flutter / Dart licenses](https://github.com/flutter/flutter/blob/master/LICENSE) (BSD-style) |
| **Flutter plugins** (non-exhaustive) | `http`, `shared_preferences`, `flutter_secure_storage`, `geolocator`, `speech_to_text`, `share_plus`, `url_launcher`, `app_links`, `flutter_map`, `flutter_riverpod`, … | See each package on [pub.dev](https://pub.dev) (`flutter pub deps` / package LICENSE) |
| **Backend** | FastAPI, Starlette, Pydantic, httpx, redis-py, cryptography (Fernet), uvicorn/gunicorn, optional sentry-sdk, anthropic client, … | See `backend` dependency manifests / wheels |
| **Admin dashboard** | Vanilla JS/CSS; vendored **Chart.js** (`admin-frontend/vendor/chart.umd.min.js`) | Chart.js: MIT (verify version in vendor header/comments); issue #193 notes missing source map |
| **E2E** | Puppeteer / Chromium in `e2e/` | Apache-2.0 / BSD components per Chromium/Puppeteer |

Generate an exact lockfile-oriented list when preparing a formal compliance review:

```bash
cd frontend && flutter pub deps
cd ../backend && pip freeze   # or poetry/pip-tools export if adopted
```

## Fonts & icons

- Material / Cupertino icons and fonts shipped via Flutter toolchains — see Flutter/engine notices.
- Project logo / brand assets under `shared-assets/` / `docs/logo.png` — Preços Públicos IA project assets (MIT project scope unless otherwise marked).

## Deploy & infrastructure examples

- **nginx**, **Docker**, **Redis**, **Postgres/pgvector** images: respective upstream licenses (BSD/MIT/SSPL/etc. depending on distribution). Compose pins are operational convenience (#269); operators remain responsible for chosen image licenses and CVEs.

## What this project does *not* include by default

- Google Play / App Store SDKs (FCM, billing, in-app review) — not wired in current tree.
- Firebase / third-party ad or analytics SDKs — anonymous usage is first-party HyperLogLog on the API (see `docs/lgpd-medicao-de-uso.html`).

## Maintaining this document

Update when adding vendored code, changing map providers, or adopting new SDKs.
Link store listing / privacy questionnaires (#262, #270) to this file and
`docs/terceiros.html` so disclosures stay consistent.
