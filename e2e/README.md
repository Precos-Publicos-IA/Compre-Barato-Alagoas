# e2e — headless browser suite

Puppeteer drives real Chrome with **simulated user input** and **screenshots**. See
[`AGENTS.md`](../AGENTS.md) for when this is mandatory (local before PR, live after deploy).

| Command | Use |
|---------|-----|
| `npm run full:local` | Mock backend + admin + docs; full DOM/API suite (PR gate) |
| `npm run full` | Same suite against already-running URLs |
| `npm run live` | Production app/API/docs (+ optional admin) post-deploy |
| `npm run smoke` | Lighter live app + API shape check |

## Local (dev machine)

```bash
cd e2e && npm install
npx puppeteer browsers install chrome   # once if needed
npm run full:local
npm run live                            # after deploy
```

## CI — pre-baked image (no reinstall per job)

Toolchain lives in **`ghcr.io/<owner>/compre-barato-alagoas/ci-e2e:latest`**
(`e2e/Dockerfile.ci`, built by `.github/workflows/ci-image.yml` only when the recipe changes).

Deploy workflow jobs `e2e-local` / `live-verify` / backend `test` **pull that image** and only
`actions/checkout` + run scripts. They must not run `npm install` / Chrome download on every PR
(that hung the first pipeline on Puppeteer install).

Bootstrap once (Actions → **Build CI e2e image** → Run workflow on `main`, or let the path-filtered
push on `main` run it). PR builds may push `:pr-N` tags; `:latest` is updated from `main`.

Screenshots land in `screenshots/` (gitignored). Exit non-zero on any failed check.
