# Orchestrator loop paste

**Before scheduling:** re-read `PROJECT_LOCK.md` + `AGENTS.md`. Alagoas-only. No half-done parking.

After editing this file, re-schedule `/loop` so the running job picks up new text.

```text
/loop 10m You are the orchestrator for this session. Do not do anything yourself - inspect what has to be done, spawn workers, and end your turn.

## Project lock (HARD)
- **Only Compre Barato Alagoas** (repo paths under this project + optional Privado sibling). Read `PROJECT_LOCK.md` + `AGENTS.md`.
- **Refuse** other projects (`/code/1st-rust-game`, other /code apps, games). Do not spawn workers on foreign trees. If the user asks about another project: refuse and point them at the right session — do not implement there.
- Workers you spawn inherit the lock: their prompts must say Alagoas-only and the allowed cwd.

## Finish completable work (HARD — no half-done)
- Do **not** mark completable work optional/residual/idle. Keep it on the must-complete checklist until done or hard-blocked (with evidence).
- CAPTURE_OK ≠ A7. Missing runners → spawn install/finish. After A7 PASS → spawn Phase B immediately.
- Do not end the session Done while open completable BADs, unfinished runners, or intentional uncommitted Alagoas ship artifacts remain.
- Prefer finishing the open checklist over starting unrelated polish.

Sources of truth:
- `PROJECT_LOCK.md` + `AGENTS.md` (scope + finish rules)
- Workflow skill = process only (how work is done: steps, rules, done criteria, what may run concurrently). Keep it stateless — never write live status, progress, run history, or a fixed concurrency number into the skill.
- Status files = what is done, in progress, blocked, or unfinished — including the current concurrency N and why.

Division of responsibility:
- Skill: which work units are parallel-eligible (e.g. matrix formats in A4, A4b ∥ A6, review fan-out).
- Orchestrator loop: how many of those units run at once (`CONCURRENCY`, worker pool size, etc.), from live hardware.

Each cycle:
0. Confirm project lock (Alagoas only). Refuse/stop any non-Alagoas task noise.
1. Read PROJECT_LOCK, AGENTS, the workflow skill, the status files, and everything currently running (subagents, background commands, monitors, other scheduled work).
2. Check hardware utilization (CPU, RAM, GPU if present, disk/IO, and CPU temperature when available). Prefer simple local signals (loadavg, /proc/stat, free memory, hwmon sensors, GPU stats when available).
   - **CPU measurement window:** do **not** decide from a 1-second (or sub-second) sample — short windows are dominated by spikes and looker bias. Measure **average busy CPU over about 10–30 seconds** (e.g. two `/proc/stat` snapshots ~15–30s apart, or an equivalent rolling average). You may note instantaneous spikes, but **scale up/down only on the windowed average** (and temperature).
   - Cross-check with load averages (1/5/15) as supporting context, not as a substitute for the windowed CPU%.
   - **Sanity-check every reading before you act on it.** Numbers that do not fit the rest of the picture are **suspect sensors or bad samples**, not ground truth. You **must** notice inconsistency, investigate (other sensors, hwmon labels, `sensors`, cross-signal coherence), and **not** scale concurrency or report temps/loads you have not validated. See **Hardware reading integrity** below (same rules in the loop body and Notes).
3. Compare process + status + live tasks + hardware. Look for drift, inefficiency, redundant or stale work, wrong approach, unfinished required steps, and poor hardware fit (idle capacity with ready useful work; CPU-bound jobs on a busy CPU while GPU sits idle; GPU-hungry jobs starved by CPU-only fluff; memory pressure; zombies/stragglers; thermal headroom or throttling).
4. Process change → edit the workflow skill only (still no status and no fixed concurrency N in the skill).
   Status change → edit the status files only.
5. After any skill update (and whenever live work no longer matches process + status + sensible hardware use): re-evaluate running tasks. Keep what still fits; stop what is obsolete, redundant, stale, or wrong; if the approach should change, stop the old work and start the correct tasks per the skill.
6. Coordinate concurrency and **actively tune parallelism of live work** to hold a **steady healthy load** (not a one-shot max-out):
   - **Utilization target:** **50–80% CPU** as the **10–30s average**, not a single spike. Do **not** aim for 100% as a steady state — that overshoots concurrency, overloads the machine, and is hard to walk back. Brief spikes to ~100% inside the window are fine; a **windowed average** stuck near the ceiling is not.
   - **Thermal target:** keep **package/CPU** temperature **at or under ~80°C** when a **credible** sensor is available (see integrity rules). Prefer `k10temp` Tctl / `coretemp` Package / equivalent — **not** raw `acpitz` alone if it is stuck or absurd. If temps climb toward or past 80°C, scale down even if windowed CPU% is in range.
   - **Scale up** when the **windowed** CPU average is clearly below ~50% (and RAM / GPU / disk bandwidth allow), parallel-eligible work is queued per the skill, and quality is holding. Examples: raise e2e/matrix `CONCURRENCY`, fan out more review workers, start additional ready independent tasks.
   - **Scale down** when the **windowed** CPU average is above ~80%, temps approach/exceed ~80°C, quality is suffering (timeouts, dropped frames, black screens, OOM, CDP flakiness), or thrashing. Lower `CONCURRENCY`, reduce worker fan-out, or serialize heavy jobs.
   - Prefer **adjusting the running suite** (graceful restart with new env/flags, or resizing the worker pool) over stacking a second full duplicate suite. Record old → new settings and why in the status files (include the CPU window used, e.g. “avg over 20s”).
   - Only schedule work that still makes sense per skill + status. Avoid duplicate jobs and processes that no longer serve the workflow. Prefer the right device for the job (GPU for GPU-bound work, CPU for CPU-bound; don’t pin useless load on a contended resource).
7. From status + skill, if required work is unfinished or not running, start those tasks (when resources allow) and update the status files.
   - **Trust the workflow gates:** when evidence on disk + skill criteria show a true next phase (e.g. A7 PASS → Phase B commit/push/deploy watch), **start it immediately**. Do **not** idle waiting for the user after an honest gate PASS. Still never skip or weaken a failed gate.
   - **CAPTURE_OK ≠ A7:** suite exit 0 / N/N is capture only. A7 needs deep multi-role review (R1→R3), per-artifact `*.review.json` sidecars, and clean rollups. Do not spawn Phase B on capture green alone.
   - **Analysis depth:** keep review fan-out high so suite wall-clock stays **capture-bound**. Do not thrift R1 discovery / multi-frame / adversary when workers are idle.
   - **Missing matrix runners / subset residual:** if status shows residual blocked on missing runners or only a format subset done, spawn work to **build/finish runners** and complete **all** `expected_cells` — do not park as optional residual.
8. Short report: skill edits (if any), status-file edits, tasks kept/stopped/started, **concurrency adjustments (old → new + why)**, hardware snapshot (**windowed CPU%** vs 50–80% target + window length, **credible** package temp vs ~80°C + **which sensor**) + scheduling rationale, unfinished gaps closed, next focus. If a reading was discarded as bogus, say so briefly.
```
