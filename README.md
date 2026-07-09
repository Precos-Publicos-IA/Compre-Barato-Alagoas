# Compre Barato Alagoas

**Compare supermarket, pharmacy, and store prices in Alagoas and build the cheapest
shopping list — using public, real electronic invoice (NFC-e) data.**

Open app (Android + web) that helps people in Alagoas, starting with Maceió, find
where to buy for less. Prices come from the **public Economiza Alagoas API**, run by
the Alagoas State Department of Finance (SEFAZ-AL), and reflect real sales collected
near real time.

> **Preços Públicos IA** project · MIT License · Live app at
> https://alagoas.precospublicos.ia.br · Documentation at
> https://docs.alagoas.precospublicos.ia.br

SEFAZ-AL is currently the only state revenue department in Brazil offering this
price-lookup service publicly and for free. This project puts that data in people's
hands with a simple, accessible experience.

## What the app does

- You type (or speak) your shopping list in natural language — e.g. *"5kg de
  arroz, 1L de leite, sabão em pó"*.
- The app looks up prices near you and computes a **fair unit price**
  (per kg, per liter, per unit) so products of different sizes can be compared honestly.
- The result is a store list ordered from **cheapest** to most expensive, with
  how much you save and the date of each sale.
- The list can be shared via a short link.

## How it works (the hard part)

The SEFAZ database has no field for **package size** ("5kg", "1L"): that information
exists only in free-text product descriptions. The heart of the project is extracting
size and unit from that text to compute a **comparable unit price**. That logic lives
in `backend/app/services/normalization/`.

```
User (Flutter, Android/web)
        │
        ▼
Backend (FastAPI)  ──►  Public Economiza Alagoas API (SEFAZ-AL)
        │
        ├── interpret the list (LLM)
        ├── normalize size/unit  →  fair price per kg/L/unit
        └── rank stores by total basket
```

The backend is a secure intermediary: it holds the SEFAZ access token — the token
**never** goes to the user app.

## Repository structure

| Folder | Description |
|--------|-------------|
| `backend/` | FastAPI API: secure intermediary, normalization, and ranking. |
| `frontend/` | Flutter app (Android + web): Riverpod, OpenStreetMap, voice. |
| `admin-frontend/` | Static admin panel (AI/product + technical metrics). |
| `docs/` | Static documentation (English), published at `docs.<domain>`. |
| `deploy/` | docker-compose + nginx to run the project on a server. |
| `e2e/` | Headless tests (Puppeteer): simulated input + screenshots (local and live). |
| `shared-assets/` | Source art/logo for the app. |

Each folder has its own README with detailed instructions.

**Delivery (agents):** branch → PR → review → merge `main` → VPS deploy (CI) → live tests.
See [`AGENTS.md`](AGENTS.md). Local: `cd e2e && npm run full:local`. Post-deploy: `cd e2e && npm run live`.

## Documentation

Full functional and technical documentation is in
[`docs/`](docs/index.html) and is published at
**https://docs.alagoas.precospublicos.ia.br** — overview, architecture, search flow,
fair-price normalization, ranking, privacy/LGPD, API, and an honest known-limitations
section. It is a static site (HTML/CSS, no build).

## Running locally

The project runs **without any external infrastructure** in *mock mode* (synthetic
Maceió catalog; no SEFAZ token or LLM key required).

**Backend**
```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload      # docs at http://127.0.0.1:8000/docs
```

**Frontend**
```bash
cd frontend
flutter pub get
flutter test
flutter run --dart-define=API_BASE_URL=http://<your-machine-ip>:8000
```

All configuration is via environment variables — copy `.env.example` to `.env` and
adjust as needed.

## Data source: Economiza Alagoas API (SEFAZ-AL)

Data comes from the public SEFAZ-AL API. Use requires a **free access token**,
requested directly from the department.

- **Developer guidance manual:**
  https://gcs.sefaz.al.gov.br/documentos/visualizarDocumento.action?key=ltOvHx2smR4%3D
- **Token request:** send full name, CPF, and project name to
  `api@sefaz.al.gov.br`.
- **General information:** `economizaalagoas@sefaz.al.gov.br`

While the token is not configured, keep `USE_MOCK_SEFAZ=true`. To go live with real
data, fill in the token in `.env` and flip the flags — **no code changes**
(see [`deploy/README.md`](deploy/README.md)).

## Deploy

`deploy/` provides a `docker-compose` stack (API + Postgres + Redis) meant to run
behind nginx with TLS. All sensitive configuration (token, passwords, domain) lives in
a single `.env` file that is **never** committed. Step-by-step guide in
[`deploy/README.md`](deploy/README.md).

## License

[MIT](LICENSE) — © 2026 Preços Públicos IA. Feel free to use, study, and contribute.


## Security posture

The application API is public by design (Flutter/web client). In **production** the
interactive OpenAPI UI (`/docs`, `/redoc`, `/openapi.json`) is **off**; app nginx only
proxies `/api` and `/health`. Threat model and scanner response:

- [docs/security-posture.md](docs/security-posture.md) (Markdown in the repo)
- Site: [Security posture](https://docs.alagoas.precospublicos.ia.br/security-posture.html) (after docs deploy)

## Internal maintenance

Session notes, on-device guides, source art (`.xcf`), informal security reports, and
agent research outputs live in the private repository
[Compre-Barato-Alagoas-Privado](https://github.com/Precos-Publicos-IA/Compre-Barato-Alagoas-Privado)
(team-only access).

