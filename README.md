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

**Delivery (agents):** verified change → commit `main` → VPS deploy (CI) → live tests.
See [`AGENTS.md`](AGENTS.md) and the autonomous cycle under [`.grok/`](.grok/README.md).
Local: `cd e2e && npm run full:local`. Post-deploy: `cd e2e && npm run live`.

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

While the official AppToken is pending, set `USE_MOCK_SEFAZ=false` and leave the
token empty: the backend **auto-falls back to the public Economiza website**
(tokenless scrape, concurrency-limited and stream-capped because the site is slow).
When SEFAZ issues a token, set the GitHub Actions secret `SEFAZ_APP_TOKEN` (deploy
writes a mode-`600` file under `secrets/` on the VPS) or use the admin panel —
traffic switches to the JSON API with **no code changes** (see
[`deploy/README.md`](deploy/README.md)). For offline dev, keep `USE_MOCK_SEFAZ=true`.

## AI agents (Requester + Verifier)

Cost-first **plan-then-execute** design (cache → Requester RAG rewrite → SEFAZ →
Verifier critic with at most one re-query). See
[`docs/ai-architecture.md`](docs/ai-architecture.md). Not free multi-agent chat;
LLM only for list parse when mock is off.

## Deploy

`deploy/` provides a `docker-compose` stack (API + Postgres + Redis) meant to run
behind nginx with TLS. All sensitive configuration (token, passwords, domain) lives in
a single `.env` file that is **never** committed. Step-by-step guide in
[`deploy/README.md`](deploy/README.md).

## Contributing

This is the contribution workflow:

1. Clone the repo
2. Ask your favorite AI agent to install the dependencies and make it run locally. Ask it to explain the project to you.
3. Request an API key to access the SEFAZ-AL API for local development: https://economizaalagoas.sefaz.al.gov.br/desenvolvedor.htm (they take a few weeks to respond).
3.1 While you don't have your own API key, you will rely on the one from the official server. Create PRs to merge code to extract the data you need. Or, experiment with the government app (it's slow) https://economizaalagoas.sefaz.al.gov.br/economizaalagoas.htm
4. Analyze the repo and find opportunities for improvement. Then, develop the code, test locally and create a PR.
4.1 If you need changes to the server, you can change the CICD pipeline or add this to the PR description: "@ai-deployer, change config [a, b and c] and run command [xyz] to [make this thing on the server]".
5. Then, you'll have to wait for someone to review it. Send a message on the Telegram group: "Hey, I just created a PR adding [your cool feature]. @Reviewers, please review and merge if all looks good, thank you! - https://t.me/+NwdJ48hmx_FhNjNh
5.1 The reviewer must have reviewer permission, which is granted when 2 reviewers vouch for someone else.
5.2 Reviewers are listed in the "reviewers" file. To add a new reviewer, create a PR, ask two reviewers to comment "LGTM", and it will be merged. Any PR that adds a reviewer can only be merged with 2 LGTM from reviewers.
5.4 Reviewer removal is done privately. Message Viny on Telegram. Any PR that removes a reviewer is automatically closed.
6. If all good, the reviewer will comment LGMT on the github PR.
7. A scheduled AI agent will look up for open PRs with LGMT from a reviewer every hour. It will review, make minor adjustments if needed, merge - that triggers the CI/CD pipeline - and after that is finished, @ai-deployer will perform any actions requested on the PR description and trigger a symbolic GitHub action with the summary of what was done and what were the results.
8. Verify the live website and if anything looks broken, make a new PR to fix it.

Guidelines:

- In this early stage, prioritize speed over correctness. Experiment. Break the server, then fix it. Ask for help if needed, no judging.
- So far all the code on this project was written by AI. Let the agents go nuts, but own the code. If it breaks something, please fix it.
- At the moment there is no user data on the server.
- Viny, who started the project, is usually busy, so don't depend on him.
- The app is deployed on a VPS under https://alagoas.precospublicos.ia.br

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


<!-- deployer-token-probe, safe to ignore -->
