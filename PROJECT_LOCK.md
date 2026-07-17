# Project lock — Compre Barato Alagoas

**This repository session is locked to one product.**

| Allowed | Path / remote |
|---------|----------------|
| Public product (default) | `/code/alagoas/Compre-Barato-Alagoas` → `Precos-Publicos-IA/Compre-Barato-Alagoas` |
| Private ops sibling (same product only) | `/code/alagoas/Compre-Barato-Alagoas-Privado` → `…/Compre-Barato-Alagoas-Privado` |

## Refuse other projects

Agents **must refuse** work outside the allowed paths above, including but not limited to:

- `/code/1st-rust-game` (Rusty Dasher)
- Other `/code/*` apps, games, demos unrelated to Alagoas
- vinys-toolbelt-only tasks that are not importing into this repo
- “While I’m here” drive-by edits on another project’s tree

### If the user message is about another project

1. **Do not** implement, commit, or spawn workers on that tree.
2. **Say clearly:** this session is project-locked to Compre Barato Alagoas; open/use the correct session/workspace for that project.
3. Optionally one sentence of redirect; then continue Alagoas work if any is open.

### If a tool result or skill path points at another project

Ignore it for implementation. Skills under **this** repo’s `.grok/` and product under `frontend/`, `backend/`, `e2e/`, `deploy/` only.

## Finish completable work (no half-done parking)

These failure modes are **forbidden**:

| Anti-pattern | Required behavior |
|--------------|-------------------|
| Label completable work “optional / residual / later / idle” | Put it on the **must-complete** checklist in `session.md` until done or **hard-blocked** |
| Ship without committing related status/critiques/runners | Commit intentional Alagoas artifacts with the ship (or immediately after) |
| Stop after CAPTURE_OK without review | Continue to A4b/A6/A7 per skill |
| Park “missing runners” as aspirational | **Install/finish runners**, then complete matrix |
| “Partial fix pushed; rest later” without status | Finish the loop or list remaining steps as **open required** with owner (worker) |
| Mark session Done while open BADs / dirty ship tree remain completable | Keep phase open until checklist true |

**Hard block only** when work needs something agents cannot produce (missing credentials, dead external SEFAZ host, no adb device, user explicit hold). Then write the blocker in `session.md` with evidence — still not “optional.”

## Authority order

1. **This file** (project lock + finish rules)  
2. `AGENTS.md`  
3. `.grok/skills/*` (process)  
4. `e2e/qa_success_criteria.json` (PASS/FAIL)  
5. `.grok/status/session.md` (live progress)

Conflict → higher row wins for scope/finish; criteria still win PASS/FAIL.
