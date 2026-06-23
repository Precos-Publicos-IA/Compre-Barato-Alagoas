# e2e — headless browser suite

Puppeteer drives real Chrome with **simulated user input** and **screenshots**. See
[`AGENTS.md`](../AGENTS.md) for when this is mandatory (local before PR, live after deploy).

| Command | Use |
|---------|-----|
| `npm run full:local` | Mock backend + admin + docs; full DOM/API suite (PR gate) |
| `npm run full` | Same suite against already-running URLs |
| `npm run live` | Production app/API/docs (+ optional admin) post-deploy |
| `npm run smoke` | Lighter live app + API shape check |

```bash
cd e2e && npm install
npx puppeteer browsers install chrome   # once if needed
npm run full:local
npm run live                            # after deploy
```

Screenshots land in `screenshots/` (gitignored). Exit non-zero on any failed check.

CI: `e2e-local` runs on PRs/pushes that touch app surfaces; `live-verify` runs after
successful deploy on `main` (see `.github/workflows/deploy.yml`).
