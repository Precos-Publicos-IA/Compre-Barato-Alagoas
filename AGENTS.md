# Project rules — Compre Barato Alagoas

## Project lock (HARD — refuse other projects)

**Read first:** [`PROJECT_LOCK.md`](PROJECT_LOCK.md) and workspace [`../PROJECT_LOCK.md`](../PROJECT_LOCK.md) / [`../AGENTS.md`](../AGENTS.md).

This session/workspace is **locked to Compre Barato Alagoas** (public product repo; private ops sibling only when needed for the **same** product).

- **Allowed roots:** this repo, optionally `Compre-Barato-Alagoas-Privado/`. Workspace root is `/code/alagoas` but **code changes** stay in those two trees.
- **Refuse** implementing, committing, pushing, or spawning work under other trees (e.g. `/code/1st-rust-game` / Rusty Dasher, other apps/games). If the user asks about another project (including accidental mis-send): **refuse + redirect**; do not “just fix it” here.
- **Ignore foreign skills** listed from other repos; use only this repo’s `.grok/skills/*` for product process.
- Every **worker prompt** must include the PROJECT LOCK one-liner from `PROJECT_LOCK.md` and an Alagoas `cwd`.

## Finish completable work (HARD — no half-done parking)

- Do **not** leave completable Alagoas work as “optional / residual / later / idle.”
- **Completable** = agents can finish without external blockers (code, tests, recapture, critique, commit, push, deploy watch, live smoke, install runners, fix open BADs).
- **Hard block only** = missing credentials, dead third-party host, no device, explicit user hold — document in `.grok/status/session.md` with evidence (still not optional).
- After true gates (e.g. A7 PASS): proceed to Phase B immediately (commit/push/`main`/deploy/live) unless user held.
- CAPTURE_OK ≠ done. Missing runners → build them. Open BADs agents can fix → keep workers until open_bads is empty or hard-blocked. Dirty intentional tree after a ship unit → commit/push or leave an owned must-complete item with a worker.
- Orchestrator/worker **must not** end a turn with open completable checklist items and no active/queued owner.
- Prefer finishing the open **must-complete** list over starting unrelated polish.
- Session may say **Done** only when the checklist in `session.md` has no completable open items.

## Autonomous dev cycle (substantial work)

For **substantial** user-facing or multi-file work, the delivery process is the
imported cycle under [`.grok/`](.grok/README.md):

| Role | Path |
|------|------|
| Ship order A/B/C, capture∥review pipeline, pre-prod gate | [`.grok/skills/ui-viewport-qa/SKILL.md`](.grok/skills/ui-viewport-qa/SKILL.md) |
| Keyboard / mouse / touch on every surface | [`.grok/skills/app-input-e2e/SKILL.md`](.grok/skills/app-input-e2e/SKILL.md) |
| Session orchestrator (`/loop`) | [`.grok/prompts/orchestrator-loop.md`](.grok/prompts/orchestrator-loop.md) |
| Live goal / phase / concurrency | [`.grok/status/session.md`](.grok/status/session.md) |
| Screens × formats matrix | [`e2e/qa_matrix.json`](e2e/qa_matrix.json) |
| **PASS/FAIL criteria** | [`e2e/qa_success_criteria.json`](e2e/qa_success_criteria.json) |

Skills are **process only** (no live status, no fixed `CONCURRENCY`). Status
files hold progress. **Trust the gates:** true A7 PASS → commit/push/`main` →
watch `deploy.yml` → `cd e2e && npm run live` without idling for a human “go”.

Product checklist (human): [`TODO.md`](TODO.md).

## Workflow: batch small changes; full pipeline only for substantial work

Post-deploy the maintainer often sends a stream of small ideas. Treat that as **inbox**, not a deploy trigger.

| Situation | What the agent should do |
|-----------|---------------------------|
| **Minor / trivial** (typo, copy tweak, one-liner, tiny style fix, single-file nit) | **Do not** start implement/review/e2e/commit on its own. **Ask** whether to apply it now or **hold it in a batch**. Prefer holding. |
| **Several small items** already on the table | **Batch** them into one change set. One headless run and one review pass for the batch—not once per idea. |
| **Substantial work** (new feature, multi-file behavior change, API/UI flow, anything that needs verification) | Proceed autonomously via the **autonomous dev cycle** (`.grok/` skills): implement, A1–A7, ship on `main`. |

Rules of thumb:

1. **Default after a deploy or a short idea message:** acknowledge, classify size, and if it's small → ask *“Apply now or batch for later?”* unless the user already said “do it” / “ship it”.
2. **Never spin the whole cycle** (A1–A7 + deploy + live) for a single minor tweak unless explicitly requested.
3. **Headless suite still applies** when a batch *ships*—run `e2e` once over the combined diff, not per micro-change while drafting.
4. If unsure whether something is “minor” vs “substantial,” **ask once** instead of over-building.

## Delivery path: commit to `main` → deploy → live tests

This is a solo-maintainer repo. **Commit verified work directly to `main`.** Do **not**
create feature branches or open pull requests, and **never** run an autonomous /
continuous agent that opens or auto-merges PRs on its own authority. (An earlier
`pr_agent_loop.sh` did exactly that and flooded the repo — it has been removed and
must not be reintroduced.)

```
verified change ──commit──► push to main ──► deploy to VPS (auto via CI) ──► live test routine
```

### 1. Commit on `main`

Once a change set **passes its local verification** (headless suite when user-facing;
`pytest` when backend moved; **`flutter test` when `frontend/` moved** — host may need
Flutter SDK installed; Flutter is the product UI and stays in A1/A2), **commit it
directly to `main`** — do not leave a verified batch sitting uncommitted unless the
user asked to wait.

- **Okay to combine** multiple features/fixes/docs tweaks in the **same commit** when they landed together in one batch; prefer simplicity over one-commit-per-feature micro-history.
- Write a clear commit message that names the main themes (what + why), not a novel.
- Follow normal git safety (no force-push, no secrets, no amend of pushed commits unless requested).
- If only part of the work is verified, commit the verified subset; leave incomplete/failing work out of the commit.

### 2. Review before committing

Before pushing, run a **real review pass** (prefer the `/code-review` skill or equivalent) over the diff:

- Correctness, regressions, security (secrets, authz on admin routes, LGPD paths).
- Coverage: new UI/API paths must extend headless steps when applicable.
- No drive-by scope; no incomplete half-features in the commit.

### 3. Deploy (VPS)

- Pushes to `main` **auto-deploy** via `.github/workflows/deploy.yml` (path-filtered; only rebuilds what changed).
- Pure docs-only changes may still deploy if `AGENTS.md` / `e2e/**` are in the workflow’s path filters for tests—see the workflow.

### 4. Live / production test routine (mandatory after deploy)

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

Apply this **twice in the delivery path:** (A) locally/mock **before push** (Phase A), (B) **against live** after deploy (Phase B3 / C).

### Surfaces in scope

| Surface | How it is driven |
|---------|------------------|
| **Admin panel** (`admin-frontend/`) | Puppeteer DOM: login, all tabs, range/refresh/logout |
| **Docs site** (`docs/`) | Puppeteer: sidebar nav links, secondary HTML pages |
| **Public API** | `fetch` inside the browser page |
| **User app** (`frontend/`) | Web smoke in browser; full UI via `frontend/integration_test/` on device/emulator |

### iPhone / Safari / WebKit limitation (issue #16)

Headless e2e is **Chromium-only** (Puppeteer), even with the mobile viewport
(`390×820`, `isMobile`, `hasTouch`). It is **not Safari** and **not WebKit**, so
green CI does **not** prove iPhone-only behavior (safe-area, `-webkit-` scroll,
Safari PWA install, iOS permission prompts, input zoom). For iPhone-risk changes
(or after deploy), run the
[iPhone Safari / WebKit checklist](.github/ISSUE_TEMPLATE/iphone-safari-checklist.md)
on a real device. Structural checks (no Mac required):
`python3 scripts/verify_ios_webkit_e2e.py` and, when present,
`python3 scripts/verify_ios_info_plist.py`. iOS is **in-scope** (`frontend/ios/`
scaffold; full Xcode target is issue #4).

### How to run

```bash
# (A0) Unit tests — layer-aware. Flutter IS the product UI (keep in cycle).
(cd backend && pytest -q)                 # when backend/ changes or full cycle
# Host may need Flutter SDK installed (`flutter` on PATH); install stable if missing.
(cd frontend && flutter test)             # required when frontend/ changes

# (A) Local / mock — Phase A baseline ship bar (before push)
cd e2e && npm install && npm run full:local
# Then open e2e/qa_success_criteria.json and critique this-run stills
#   (matrix_critique.md / video_critique.md). Suite exit 0 ≠ visual review.
# Full 147-cell matrix (e2e/qa_matrix.json expected_cells): required for residual
# close / full visual QA. If runners missing or priority-only → install/finish them.
# matrix:local subset is debug only; review those cells, then complete 147.

# (B) Live — after deploy succeeds (CI job `live-verify` or locally)
cd e2e && npm run live

# Phone / integration against live API
cd frontend && flutter test integration_test/app_test.dart \
  --dart-define=API_BASE_URL=https://alagoas.precospublicos.ia.br -d <device-id>

# iOS/WebKit readiness (docs + checklist template + ios/ scaffold; issue #16)
python3 scripts/verify_ios_webkit_e2e.py
```

Exit code must be **0** for that phase. Runtime screenshot dumps under `e2e/screenshots/`
are gitignored; critique templates under `e2e/screenshots/viewports/` and
`e2e/screenshots/web/e2e/` are tracked.

**Ship bar vs matrix residual:** baseline = `full:local` + `live` + criteria critiques
(+ A1 for changed layers) — always. Full screens×formats matrix (147 cells) is the
required target for residual close / full visual QA; if runners are incomplete,
**install/finish them** (do not treat missing runners as optional). Never drop
baseline gates or remove Flutter from A1/A2.

### CI image (do not rebuild on every PR)

Toolchain image is published **infrequently** by `.github/workflows/ci-image.yml` (Dockerfile/package change, weekly schedule, or manual dispatch) to GHCR. PR/deploy jobs use GitHub Actions **`jobs.<id>.container.image`** and only **pull** that image — never `docker build` the CI toolchain inside `deploy.yml`. See `e2e/README.md`.

### When implementing or reviewing

- Prefer extending `e2e/full.js` / `e2e/live.js` over ad-hoc scripts.
- New UI/API paths → add a headless step with interaction + screenshot.
- Backend/Flutter unit tests **do not replace** headless or post-deploy live/app checks.
