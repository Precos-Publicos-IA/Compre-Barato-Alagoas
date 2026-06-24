# Project rules — Compre Barato Alagoas

## Workflow: batch small changes; full pipeline only for substantial work

Post-deploy the maintainer often sends a stream of small ideas. Treat that as **inbox**, not a deploy trigger.

| Situation | What the agent should do |
|-----------|---------------------------|
| **Minor / trivial** (typo, copy tweak, one-liner, tiny style fix, single-file nit) | **Do not** start implement/review/e2e/commit/PR on its own. **Ask** whether to apply it now or **hold it in a batch**. Prefer holding. |
| **Several small items** already on the table | **Batch** them into one change set (one branch/PR when committing). One headless run and one review pass for the batch—not once per idea. |
| **Substantial work** (new feature, multi-file behavior change, API/UI flow, anything that needs verification) | Proceed autonomously: implement, run the mandatory headless suite once for the batch, finish cleanly. |

Rules of thumb:

1. **Default after a deploy or a short idea message:** acknowledge, classify size, and if it's small → ask *“Apply now or batch for later?”* unless the user already said “do it” / “ship it”.
2. **Never spin the whole workflow** (plan → implement personas → full e2e → PR) for a single minor tweak unless explicitly requested.
3. **Headless suite still applies** when a batch *ships*—run `e2e` once over the combined diff, not per micro-change while drafting.
4. If unsure whether something is “minor” vs “substantial,” **ask once** instead of over-building.

## Delivery path: branch → PR → review → merge → deploy → live tests

Verified work does **not** land straight on `main` by default. Use this path unless the user explicitly overrides it (e.g. emergency hotfix on main).

```
feature branch ──commit(s)──► open PR ──thorough review──► merge to main
                                                              │
                                                              ▼
                                              deploy to VPS (auto on main via CI)
                                                              │
                                                              ▼
                                              live test routine (prod URLs + app/phone)
```

### 1. Commits on a branch (not main)

Once a change set **passes its local verification** (headless suite when user-facing; backend/Flutter tests when only those layers moved), **commit it** on a **topic branch** — do not leave a verified batch sitting uncommitted unless the user asked to wait.

- **Okay to combine** multiple features/fixes/docs tweaks in the **same commit** when they landed together in one batch; prefer simplicity over one-commit-per-feature micro-history.
- Write a clear commit message that names the main themes (what + why), not a novel.
- Still follow normal git safety (no force-push to `main`, no secrets, no amend of pushed commits unless requested).
- If only part of the work is verified, commit the verified subset; leave incomplete/failing work out of the commit.

### 2. Pull request

- Push the branch and **open a PR into `main`** for every non-trivial delivery (including batched small fixes).
- PR body should say what changed, how it was tested locally, and any deploy/risk notes.
- Do **not** merge on the agent’s own authority without review completing (below).

### 3. Thorough review

Before merge, run a **real review pass** (prefer the `/review` skill or equivalent reviewer persona on the PR/branch):

- Correctness, regressions, security (secrets, authz on admin routes, LGPD paths).
- Coverage: new UI/API paths must extend headless steps when applicable.
- No drive-by scope; no incomplete half-features in the merge commit.

Address review findings (or document explicit waive with user consent) **before** merge.

### 4. Merge to `main`

- Merge only after review is clean (or user approves known gaps).
- Prefer GitHub/PR merge (squash or merge commit — follow remote defaults); avoid silent fast-forward pushes that skip the PR unless the user asked.

### 5. Deploy (VPS)

- Merges to `main` **auto-deploy** via `.github/workflows/deploy.yml` (path-filtered; only rebuilds what changed).
- Pure docs-only agent rules may still deploy if `AGENTS.md` / `e2e/**` are in the workflow’s path filters for tests—see the workflow.

### 6. Live / production test routine (mandatory after deploy)

After the deploy pipeline **finishes successfully**, run the **same test philosophy against live**:

| Layer | Against production |
|-------|--------------------|
| Headless browser | Live hosts via `e2e` (`npm run smoke` or `npm run live`) |
| Public API journeys | In-browser `fetch` against the **live API** |
| App / phone | Flutter `integration_test/` with `API_BASE_URL` → production (device/emulator) |

Live suite must **exit 0** (or failures triaged and fixed/hotfixed) before calling the delivery done.

## Mandatory: headless browser verification

Every change that touches user-facing surfaces **must** be verified with a **headless browser** that (when the work is substantial enough to implement—see batching above):

1. **Simulates real user input** (typing, clicks, form submits, navigation) — not only HTTP assertions from Node.
2. **Captures screenshots** of each major screen/step under `e2e/screenshots/`.
3. Exercises **all product functionalities**, not only the code path that changed. This app is small enough that full coverage is the default.

Apply this **twice in the delivery path:** (A) locally/mock **before PR**, (B) **against live** after deploy.

### Surfaces in scope

| Surface | How it is driven |
|---------|------------------|
| **Admin panel** (`admin-frontend/`) | Puppeteer DOM: login, all tabs, range/refresh/logout |
| **Docs site** (`docs/`) | Puppeteer: sidebar nav links, secondary HTML pages |
| **Public API** | `fetch` inside the browser page |
| **User app** (`frontend/`) | Web smoke in browser; full UI via `frontend/integration_test/` on device/emulator |

### How to run

```bash
# (A) Local / mock — before or with the PR
cd e2e && npm install && npm run full:local

# (B) Live — after deploy succeeds (CI job `live-verify` or locally)
cd e2e && npm run live

# Phone / integration against live API
cd frontend && flutter test integration_test/app_test.dart \
  --dart-define=API_BASE_URL=https://alagoas.precospublicos.ia.br -d <device-id>
```

Exit code must be **0** for that phase. Screenshots under `e2e/screenshots/` are gitignored.

### CI image (do not rebuild on every PR)

Toolchain image is published **infrequently** by `.github/workflows/ci-image.yml` (Dockerfile/package change, weekly schedule, or manual dispatch) to GHCR. PR/deploy jobs use GitHub Actions **`jobs.<id>.container.image`** and only **pull** that image — never `docker build` the CI toolchain inside `deploy.yml`. See `e2e/README.md`.

### When implementing or reviewing

- Prefer extending `e2e/full.js` / `e2e/live.js` over ad-hoc scripts.
- New UI/API paths → add a headless step with interaction + screenshot.
- Backend/Flutter unit tests **do not replace** headless or post-deploy live/app checks.
