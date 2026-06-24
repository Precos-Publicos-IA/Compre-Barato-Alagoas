# e2e — headless browser suite

Puppeteer drives real Chrome with **simulated user input** and **screenshots**. See
[`AGENTS.md`](../AGENTS.md) for when this is mandatory (local before PR, live after deploy).

| Command | Use |
|---------|-----|
| `npm run full:local` | Mock backend + admin + docs; full DOM/API suite (PR gate) |
| `npm run full` | Same suite against already-running URLs |
| `npm run live` | Production app/API/docs (+ optional admin) post-deploy |
| `npm run smoke` | Lighter live app + API shape check |
| `npm run admin_smoke` | Admin SPA gate + `esc()` presence (#134); optional `ADMIN_TOKEN` |

## Local (dev machine)

```bash
cd e2e && npm install
npx puppeteer browsers install chrome   # once if needed
npm run full:local
npm run live                            # after deploy
```

## CI — published image only (standard GHCR + job `container:`)

Best practice (GitHub docs: *Running jobs in a container* + GHCR publish):

| Workflow | When it runs | What it does |
|----------|--------------|--------------|
| **`ci-image.yml`** | `main` push **only if** `e2e/Dockerfile.ci` / `e2e/package.json` change, weekly schedule, or **workflow_dispatch** | **Build + push** `ghcr.io/precos-publicos-ia/compre-barato-alagoas/ci-e2e:latest` (+ sha tag) |
| **`deploy.yml`** (`test`, `e2e-local`, `live-verify`) | Every relevant PR/main run | **`container: image: …ci-e2e:latest`** — Actions **pulls** the image; steps are only checkout + run. **No `docker build` / no save-load artifact** |

Bootstrap once (needs `packages: write` on the publish workflow, package visibility allowing the repo to read):

1. Actions → **Build CI e2e image** → **Run workflow** on `main`  
2. In GHCR package settings, allow the repo to pull (inherit access / public as you prefer)  
3. Later PRs only pull — fast and stable

If a job fails with “pull access denied” / missing image, **do not** add a build step to `deploy.yml`; re-run the publish workflow.

Screenshots land in `screenshots/` (gitignored). Exit non-zero on any failed check.
