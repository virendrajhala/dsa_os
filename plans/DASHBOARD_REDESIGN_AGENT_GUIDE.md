# Dashboard Redesign — Autonomous Agent Guide

> How a single agent executes the whole redesign end-to-end in an autonomous
> loop, using:
> 1. `plans/DASHBOARD_REDESIGN_DESIGN.md` — WHAT to build (spec; never
>    re-argue its decisions)
> 2. `plans/DASHBOARD_REDESIGN_PLAN.md` — HOW, task by task (9 tasks; exact
>    files, code, verify blocks, commit messages)
> 3. this file — the LOOP: order, gates, recovery, stop conditions, reporting

## Session bootstrap (once, before any task)

1. Read all three files fully. Then read `plans/PHASE_EXECUTION_GUIDE.md`
   "Hard rules" — they apply verbatim here too.
2. Load skills: `dataviz` and `frontend-design` (required before Tasks 3-8;
   loading them at bootstrap is fine). If a git-workflow skill is available,
   load it before the first commit.
3. Baseline gate: `make test && make validate` must pass BEFORE you start,
   and `git status` must be clean apart from untracked owner files (xlsx,
   `.playwright-mcp/`). If not → STOP and report; do not "fix" unrelated
   state.
4. Confirm the plan's baseline still holds: `grep -n "build_dashboard_feed"
   scripts/_shared.py` returns nothing (Task 1 not already done). If any
   task is already implemented, skip to the first unimplemented task and
   say so in your report.

## The execution loop

```
for TASK in 1..9 (strictly in order):
    a. Re-read the task section AND the design-doc sections it cites.
    b. Read every file the task touches BEFORE editing (plan line numbers
       are approximate; locate by content).
    c. Execute the steps in order. TDD steps are literal: run the failing
       test and SEE it fail before implementing.
    d. Run the task's full Verify block. ALL of it — including serve+curl,
       node --check, and both-themes checks where listed.
    e. Gate: make test && make validate && node --check web_dashboard/app.js
       && git diff --quiet -- progress/progress.json. Any failure → fix
       within this task; never commit red.
    f. Self-review `git diff` for scope creep (nothing outside the task's
       file list; no drive-by refactors).
    g. Commit exactly one commit with the task's message (HEREDOC,
       conventional format, NO AI/agent attribution of any kind). Do NOT
       push.
    h. Append one line to your running report (see Reporting).
```

### Retry / recovery rules

- A failing verify step gets at most **3 distinct fix attempts** (different
  hypotheses, not the same edit re-run). Still red → STOP CONDITION.
- If an edit breaks previously-green tests, `git checkout -- <file>` back to
  the last commit for the affected files and re-approach; never stack fixes
  on a broken base.
- If the plan contradicts the actual code (renamed function, moved line),
  the CODE is truth for mechanics, the DESIGN DOC is truth for behavior;
  note the deviation in the task's report line. If the contradiction is
  behavioral (the design says X, code makes X impossible) → STOP CONDITION.
- Server processes: always start `serve_dashboard.py` in the background on a
  non-default port for checks, and kill it before the task commit.

### Stop conditions (halt, report, ask the owner — do NOT improvise)

1. `progress/progress.json` would need to change.
2. A design-doc decision seems wrong or two spec sections conflict.
3. 3 failed fix attempts on the same verify step.
4. You need a palette hex or surface color not in design §7 (changing any
   requires re-running the validator AND owner sign-off).
5. Anything requiring a push, a new dependency, a build step, or a CDN
   asset.
6. `make test`/`make validate` was already red before you touched anything.

## Skill usage during visual tasks (3-8)

- Follow the dataviz procedure per chart: form → color-by-job → palette
  (already validated; §7 hexes verbatim) → mark specs → hover layer → a11y
  pass → **render it and look at it**. Check every chart against
  `references/anti-patterns.md` before the task commit.
- Frontend-design discipline: the constellation is the ONE bold element;
  everything else stays quiet. Before each visual commit ask: "does any
  part of this read as generic-default?" — fix or justify in the report.
- If a browser tool (Playwright/Chrome MCP) is available, screenshot each
  workspace after Tasks 4-8 and eyeball for label collisions/overflow; if
  not, the curl + node-check matrix in each task is the floor, and say in
  the report that visuals were not screenshot-verified.

## Final gate (after Task 9, before declaring done)

1. Full final-state check:
   `make test && make validate && python3 scripts/next_problem.py &&
   python3 scripts/revision_report.py && python3 scripts/dashboard.py` —
   all exit 0.
2. Alignment-matrix audit (design §3b): produce the 14-row table with
   file:line evidence per row. Any unmet row → back to its task.
3. Dispatch ONE independent fresh-context review subagent with: the design
   doc path, `git log --oneline` range of your commits, and instructions to
   verify (a) matrix completeness, (b) palette hexes match §7 or a
   validator rerun is attached, (c) parity tests exist and pass, (d) no JS
   recomputes what the feed provides. Fix Critical/Important findings (one
   fix commit per logical group), have it re-confirm. Report Minors
   without fixing.
4. `git diff <start-commit>..HEAD --stat` goes in the final report.

## Reporting

Maintain `plans/DASHBOARD_REDESIGN_REPORT.md` (create at bootstrap; commit
it only in the Task 9 docs commit):
- one line per task: `Task N: <commit sha> — <deviations or "as planned">`
- stop conditions hit (if any) and how resolved
- final gate results: test counts, matrix table, reviewer verdict, Minors
  list
- anything the owner must decide later

The final chat message to the owner = that report's summary: lead with
done/not-done, the commit list, reviewer verdict, and open Minors. No push
— the owner pushes after their own look.
