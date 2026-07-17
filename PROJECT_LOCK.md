# Project lock — Compre Barato Alagoas

**This repository (and the parent workspace `/code/alagoas`) is locked to one product.**

| Allowed | Path / remote |
|---------|----------------|
| Public product (default) | `/code/alagoas/Compre-Barato-Alagoas` → `Precos-Publicos-IA/Compre-Barato-Alagoas` |
| Private ops sibling (same product only) | `/code/alagoas/Compre-Barato-Alagoas-Privado` → `…/Compre-Barato-Alagoas-Privado` |
| Workspace wrapper | `/code/alagoas/PROJECT_LOCK.md` + `/code/alagoas/AGENTS.md` (same lock, session root) |

## Refuse other projects (HARD)

Agents **must refuse** work outside the allowed paths above, including but not limited to:

- `/code/1st-rust-game` (Rusty Dasher) and any skill whose absolute path is under that tree
- Other `/code/*` apps, games, demos unrelated to Alagoas product development
- vinys-toolbelt-only tasks that are not importing into this repo
- “While I’m here” drive-by edits on another project’s tree
- Accidental user mis-sends (message clearly about another app while this session is Alagoas)

### If the user message is about another project

1. **Do not** implement, commit, push, or spawn workers on that tree.
2. **Say clearly:** this session is project-locked to Compre Barato Alagoas; open/use the correct session/workspace for that project.
3. Optionally one sentence of redirect; then continue Alagoas **must-complete** work if any is open.

### If a tool result or skill path points at another project

Ignore it for implementation. Skills under **this** repo’s `.grok/` and product under `frontend/`, `backend/`, `admin-frontend/`, `e2e/`, `deploy/`, `docs/` only. Global/product-agnostic skills may run, but only against Alagoas paths.

### Worker prompts (required)

Every worker spawn prompt **must** include:

```text
PROJECT LOCK: Alagoas only. cwd=/code/alagoas/Compre-Barato-Alagoas (or Privado). Refuse other projects. Finish this task fully — no half-done parking; if blocked, write evidence in .grok/status/session.md.
```

Do not spawn a worker with a foreign `cwd` or with a task that edits a foreign tree.

## Finish completable work (HARD — no half-done parking)

These failure modes are **forbidden**:

| Anti-pattern | Required behavior |
|--------------|-------------------|
| Label completable work “optional / residual / later / idle” | Put it on the **must-complete** checklist in `.grok/status/session.md` until done or **hard-blocked** |
| Ship without committing related status/critiques/runners that are part of the ship | Commit intentional Alagoas artifacts with the ship (or immediately after) |
| Stop after CAPTURE_OK without review | Continue to A4b/A6/A7 per skill |
| Park “missing runners” as aspirational | **Install/finish runners**, then complete all matrix `expected_cells` |
| “Partial fix pushed; rest later” without status | Finish the loop or list remaining steps as **open required** with an active/queued worker |
| Mid-flight product UI left dirty with no owner | Worker owns through recapture + critique + commit/push, or hard-block with evidence |
| Mark session Done while open BADs / dirty ship tree / unfinished runners remain completable | Keep phase open until checklist true |
| Orchestrator turn with open checklist and no worker and no hard-block | **Spawn** the next worker (if hardware allows) or document hard-block — never silent park |
| Start unrelated polish while must-complete items are open | Prefer finishing the open checklist first |

**Hard block only** when work needs something agents cannot produce (missing credentials, dead external SEFAZ host, no adb device, user explicit hold). Then write the blocker in `session.md` with evidence — still not “optional.”

**Definition of done for a task:** the worker’s acceptance criteria are met **and** related intentional artifacts are committed/pushed when they are ship material (or left owned on the checklist with a follow-on worker already planned).

## Authority order

1. **This file** + workspace `/code/alagoas/PROJECT_LOCK.md` (project lock + finish rules)  
2. `AGENTS.md` (repo + workspace)  
3. `.grok/skills/*` (process)  
4. `e2e/qa_success_criteria.json` (PASS/FAIL)  
5. `.grok/status/session.md` (live progress)

Conflict → higher row wins for scope/finish; criteria still win PASS/FAIL.
