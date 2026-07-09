# Security posture — Compre Barato Alagoas

This document describes the project's **threat model** and **control boundaries**.
It is for security reviews, scanners, and anyone assessing whether open source is
compatible with production operations.

**Summary:** the application API is **public by design** (the Flutter/web app is an
untrusted client). The source can remain **open source**. Protection does not come
from hiding routes on GitHub; it comes from **secrets outside the repository**,
**admin closed by default**, **abuse limits**, **data minimization (LGPD)**,
and **disabling the interactive OpenAPI UI in production**.

Related documentation on the static site:

- [Security & data (LGPD)](security-and-data.html)
- [LGPD · Usage measurement](lgpd-usage-measurement.html)
- [Privacy policy (app)](https://alagoas.precospublicos.ia.br/privacy.html)

---

## 1. What is public on purpose

| Surface | Why it exists | Primary control |
|---------|---------------|-----------------|
| Code on GitHub (MIT) | Transparency, LGPD trust, civic reuse | Secrets **never** in git; see `.gitignore` and `.env.example` |
| `POST /api/v1/search` and product routes | The app must call the backend | Daily rate limit, input validation, cache, no unnecessary PII in responses |
| Documentation site (`docs.*`) | Explain product and privacy | User/operator-oriented content; no credentials |
| Price data (SEFAZ-AL origin) | Public NFC-e data | SEFAZ token only on the server (encrypted admin panel or bootstrap in the VPS `.env`) |

**Typical scanner finding:** “Documented API / visible endpoints.”  
**This project's response:** the client (browser or APK) already reveals the contract.
Open source and product documentation **do not** replace authentication or limits; and
they are **not**, by themselves, a vulnerability if the controls below are active.

---

## 2. What is *not* a security boundary

- **Public repository visibility** — hiding the code does not remove the API at
  `https://alagoas.precospublicos.ia.br`. Anyone who wants to abuse still speaks HTTPS
  to the backend.
- **Only trusting “nobody knows the admin URL”** — the panel uses a separate subdomain,
  but the admin API requires a token; without a token it returns **401** (fail-closed).
- **Swagger/ReDoc in production** — makes automated scanning easier and is not needed
  by the app. That is why it stays **off in production** (see §4).

---

## 3. Surfaces and controls

### 3.1 Application API (user)

- Clients are **not account-authenticated** (no login/password); device identity is
  optional and used for consent/cloud lists (LGPD).
- Device token: generated on the client, **stored on the server only as a salted
  hash** — a Redis dump does not return a usable bearer.
- Searches: configurable daily limit (`DAILY_SEARCH_LIMIT`), keyed to prevent
  trivial abuse.
- Location: used for search; policy of **not retaining** trajectories as a profile.
- Errors: `X-Request-ID` for support correlation, without leaking stack traces to the user.

### 3.2 Admin API (`/admin/api/*`)

- Effectively disabled if `ADMIN_TOKEN` is empty (**401**).
- Token comparison in **constant time** (`hmac.compare_digest`).
- Served on its own vhost (`admin.<domain>`); same backend, separate origin.
- Secrets vault (e.g. SEFAZ token): written via the panel, **Fernet** at rest in
  Redis; the status API returns only a *fingerprint*, not the secret.

### 3.3 Secrets and configuration

| Secret | Where it lives | Does not live in |
|--------|----------------|------------------|
| `ADMIN_TOKEN` | `.env` only on the server | git, client app, JSON responses |
| `SECRET_ENCRYPTION_KEY` | `.env` only on the server | git, public backups |
| SEFAZ token | Preferably panel → encrypted Redis; fallback `SEFAZ_APP_TOKEN` in the VPS `.env` | public repository |
| `ANTHROPIC_API_KEY` | VPS `.env` | Flutter client, commits |
| Postgres / Redis | internal Docker network; API published only on `127.0.0.1:8000` on the host | the open internet |

Sensitive operational material (session notes, on-device guides with machine paths,
extra source art) stays in the team's **private** repository, not the public product.

### 3.4 LLM / SEFAZ (cost amplification)

- User input treated as **inert data** in the prompt (security rules in the system
  prompt; deterministic fallback if the model fails or is steered off course).
- Limited SEFAZ fan-out (`SEFAZ_CONCURRENCY`, pages, radius/days within public API
  limits).
- Redis cache reduces repeated identical queries.

### 3.5 Static frontend and app

- Admin and product docs are **static HTML/JS** with no server-side rendering of
  arbitrary user input.
- App Links / `assetlinks.json` use a signing-certificate fingerprint (expected on
  Android); not an API credential.

---

## 4. OpenAPI / Swagger in production

Backend behavior (`ENVIRONMENT` + optional `EXPOSE_API_DOCS`):

| Environment | `/docs`, `/redoc`, `/openapi.json` |
|-------------|-------------------------------------|
| `development` (local default) | **On** — useful for dev and tests |
| `production` (deploy compose sets this) | **Off** (404) |
| Any + `EXPOSE_API_DOCS=true` | On (escape hatch) |
| Any + `EXPOSE_API_DOCS=false` | Off |

User-app nginx only proxies **`/api` and `/health`** to FastAPI; it no longer
publishes `/docs` or `/openapi.json` at the edge.

**Important:** turning off the OpenAPI UI does **not** “hide” the app contract — the
client still calls the same routes. It reduces noise in automated pentests and avoids
running an *interactive* documentation surface in production without need.

The human view of endpoints remains in the [product documentation](index.html#api)
(`docs.*` site), in product language — not as an exploration console on the same host
as the API.

---

## 5. Response to frequent findings

| Finding | Severity we adopt | Treatment |
|---------|-------------------|-----------|
| “Public / documented API” | Informational if §3 controls are OK | Keep open source; cite this doc; ensure §4 in prod |
| OpenAPI/Swagger in production | Low/medium hygiene | Off by default in `production` |
| Admin without authentication | Critical if `ADMIN_TOKEN` empty and route reachable with data | Fail-closed; set a strong token on the VPS |
| Secret in the repository | Critical | Rotate; never commit `.env` |
| Abuse / scraping / LLM cost | Medium operational | Rate limit, cache, mocks in dev, monitor admin |
| Prompt injection | Medium (integrity/cost) | Hardened prompt + mock fallback + dedicated tests |

---

## 6. What auditors / scanners should verify

Objective checklist (beyond “does it have OpenAPI?”):

1. In production with `ENVIRONMENT=production`, `GET /docs` and `GET /openapi.json` → **404**.
2. `GET /admin/api/...` without a token → **401**.
3. No real `.env`, PEM key, or SEFAZ token in relevant public history.
4. Redis/Postgres not published on the internet (compose network + local proxy only).
5. Production CORS is **not** `*` if there are sensitive cross-origin credentials (set
   `CORS_ORIGINS` in the VPS `.env`).
6. Privacy policy and minimization aligned with the code (hashes, consent for cloud
   lists).

---

## 7. Open source on purpose

We keep the application code public because:

1. Price data is already public (SEFAZ-AL); the value is in the **secure bridge** and
   honest UX, not a secret state algorithm.
2. LGPD claims and “we don't sell your search” remain **auditable**.
3. Closing GitHub **does not close** the app's HTTPS API.

What stays restricted to the team (private repository or VPS only) is **operational
secrets**, internal notes, and informal reports — not the security design described
here.

---

## 8. Honest limitations

- Anyone with **root on the VPS** can read process memory and the on-disk `.env`; full
  mitigation would require an external HSM/KMS (out of scope for a single VPS today).
- Rate limit and cache depend on a healthy Redis; without Redis the API does not start
  (fail fast).
- This text does **not** replace a formal pentest or external DPO LGPD opinion; it is
  the project's posture to guide implementation and review.

---

*Last guidance aligned with the code: interactive docs off in production;
controls in `backend/app/config.py` (`api_docs_enabled`), `backend/app/main.py`, and
`deploy/nginx/alagoas.precospublicos.ia.br.conf`.*
