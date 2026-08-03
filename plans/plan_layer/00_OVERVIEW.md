# Plan Layer — Implementation Overview

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Execute the feature files in the order given in §Execution order. Each feature file is self-contained; this overview holds the shared contracts every file references.

**Goal:** Add a proactive planning layer to DSA_OS: a quarter plan as data (`progress/plan.json`), plan-vs-actual computations in the Python engine, and dashboard surfaces for daily contract, weekly scoreboard, monthly skill milestones, quarter burn-up roadmap, promotion ladder, and time-invested analytics.

**Architecture:** `progress/plan.json` becomes the machine-readable source of truth for the 13-week quarter currently living only in `study_plan_months_1-3.xlsx` (which stays as a human reference, never parsed by code). All derived numbers are computed in `scripts/_shared.py` and shipped through the existing `GET /api/feed` (`build_dashboard_feed`); `web_dashboard/app.js` stays a pure view (repo rule: "the dashboard never recomputes what `_shared.py` can compute"). Milestones are **derived** (curriculum order + weekly targets), never hand-maintained, so they re-plan automatically when actuals slip.

**Tech Stack:** Python 3 stdlib only (`requirements.txt` rule), vanilla JS single-file `app.js`, `unittest` test files run directly by `make test`.

## Decisions taken (owner may override before execution)

1. `plan.json` is source of truth; xlsx retired from workflow (kept in repo as reference).
2. Quarter target stays **60 solves / ~10 mocks / 2026-07-27 → 2026-10-25**; the burn-up chart + required-pace tile make the gap visible instead of re-baselining.
3. Month milestones are derived from curriculum order + weekly solve targets, with live status (done / on_track / at_risk / missed).
4. New **Plan** workspace in the nav rail; the daily contract card goes into **Today** (it drives today's action).
5. **No new mock CLI work**: `update_progress.py --mode mock` already records into `progress.mock_interviews[]` (verified, `scripts/update_progress.py:528`). The plan layer only *surfaces* mock plan-vs-actual.
6. No streak counters (existing design rule, `plans/DASHBOARD_REDESIGN_DESIGN.md` §4).

## Global constraints

- Python: stdlib only. No new dependencies, no xlsx parsing.
- Dashboard: vanilla JS, single `app.js`, no frameworks, no CDN fonts. Feed-backed panels must render `degradedBanner()` when `state.feed == null` (server not running).
- All new feed values computed in `scripts/_shared.py`; `app.js` may only do display transforms.
- Status is never conveyed by color alone: icon or text label always accompanies it.
- Charts: one axis, 2px lines, tooltips via `<title>`, `role="img"` + `aria-label` on chart hosts (match `renderForecast`, `app.js:720`).
- Tests: `unittest`, file named `scripts/test_plan_feed.py`, registered in the `Makefile` `test` target. Test fixtures pass explicit `progress`/`plan` dicts — never depend on the live `progress/progress.json` values.
- Commit style (from git log): `feat/plan: ...`, `feat/dashboard: ...`, `test/plan: ...`. Extremely concise messages. **NEVER add Co-Authored-By lines.**
- Dates in fixtures use 2026 dates consistent with the quarter (start 2026-07-27, Monday).
- JSON files written via `_shared.save_json_file` conventions: 2-space indent, trailing newline.

## PRECONDITION — uncommitted WIP (check before starting)

`git status` currently shows uncommitted changes in `scripts/_shared.py`, `scripts/test_shared.py`, `scripts/test_dashboard_feed.py` (mock-selection work, unrelated to this plan). **Ask the owner to commit or stash that WIP first.** Never revert or fold those hunks into plan-layer commits. All plan-layer edits are pure additions (new functions appended to `_shared.py`, new keys added to the feed dict) — no existing function bodies are modified except the exact insertion points named in the tasks.

## Execution order

| # | File | Delivers | Depends on |
|---|---|---|---|
| 1 | `01_PLAN_DATA_MODEL.md` | `progress/plan.json` + loader/validator in `_shared.py` + tests | — |
| 2 | `02_FEED_PLAN_BLOCK.md` | week/quarter/month/contract computations, `feed.plan`, `feed.promotion`, `feed.time_invested` + tests | 1 |
| 3 | `03_TODAY_CONTRACT.md` | Today's-contract card in the Today workspace | 2 |
| 4 | `04_PLAN_WORKSPACE.md` | New Plan workspace: week scoreboard, month milestones, quarter roadmap/burn-up | 2 |
| 5 | `05_PROMOTION_LADDER.md` | Promotion ladder section (Curriculum workspace) | 2 |
| 6 | `06_TIME_ANALYTICS.md` | Time-invested section (Evidence workspace) | 2 |
| 7 | `07_PROBLEM_BROWSER.md` | Problems workspace: skill tree + LeetCode-style list with status/locks | — (feed task composes with 2) |
| 8 | `08_INTERVIEW_FREQUENCY.md` | Interview-ask frequency snapshot + "Asked" column/sort in the browser | 7 |

Files 3–6 are independent of each other (any order, or parallel agents — but they all edit `index.html`/`app.js`/`styles.css`, so run sequentially unless using isolated worktrees with a merge step).

## Shared contract: `feed.plan` (also repeated in each feature file)

`build_dashboard_feed()` gains three top-level keys. `plan` is `null` when `progress/plan.json` does not exist, and `{"error": "<message>"}` when it exists but fails validation (the rest of the feed must still build — plan problems must never 500 the whole feed).

```json
"plan": {
  "quarter": {"label": "2026 Q3 — months 1-3", "start": "2026-07-27", "end": "2026-10-25",
               "target_new_solves": 60, "target_mocks": 10, "daily_review_capacity": 4},
  "today_contract": {
    "in_quarter": true, "deload": false,
    "solve": {"planned": true, "done": false},
    "revisions": {"due": 4, "done_today": 1, "cleared": false},
    "mock": {"planned": false, "done": false}
  },
  "week": {
    "week": 2, "start": "2026-08-03", "end": "2026-08-09", "deload": false,
    "target_solves": 6, "actual_solves": 3, "expected_to_date": 4.29, "on_track": false,
    "mock_planned": true, "mock_done": false,
    "revisions_done": 5, "revisions_passed": 4,
    "skills_mastered": ["SK-OB-05"], "days_remaining": 3
  },
  "weeks": [
    {"week": 1, "start": "2026-07-27", "deload": false,
     "target_solves": 6, "actual_solves": 4, "mock_done": false}
  ],
  "burnup": {
    "start": "2026-07-27", "end": "2026-10-25", "target_total": 60,
    "planned": [{"date": "2026-08-02", "start": "2026-07-27", "cumulative": 6, "deload": false}],
    "actual": [{"date": "2026-07-28", "cumulative": 1}],
    "actual_total": 7, "projected_total": 44.6,
    "required_per_week": 4.55, "weeks_remaining": 11.9,
    "mocks_done": 0, "target_mocks": 10
  },
  "months": [
    {"month": "2026-08", "milestone_date": "2026-08-31",
     "expected_solves": 26, "actual_solves": 7,
     "skills": [{"skill_id": "SK-OB-05", "name": "...", "stage": "Observation", "status": "at_risk"}],
     "stage_note": "Observation 7/7 · State Construction 3/7"}
  ]
},
"promotion": {
  "current_stage": "Observation", "total_completed": 13,
  "stages": [
    {"stage": "Observation", "status": "in_progress",
     "skills_mastered": 4, "skills_total": 7,
     "attempted": 13, "passed": 13,
     "minimum_weighted_score": 2.4, "minimum_completed_problems": 23}
  ]
},
"time_invested": {
  "total_minutes": 785, "sessions": 13, "average_minutes": 60.4,
  "by_difficulty": [{"difficulty": "Easy", "count": 9, "average_minutes": 54.4}],
  "series": [{"date": "2026-07-09", "problem_id": "OBS-001", "minutes": 45, "difficulty": "Easy"}]
}
```

Skill milestone `status` values: `done` (mastered now) · `missed` (milestone date passed, not mastered) · `at_risk` (future milestone, actual cumulative solves behind plan-to-date) · `on_track` (otherwise).

## Mechanism notes (verified in code — do not re-derive differently)

- **Stage promotion is skill-mastery driven**: `determine_stage` (`_shared.py:866`) returns the earliest non-mastered stage; `scoring.promotion_thresholds` feeds `stage_checks` quality bars (`recompute_score_summary`, `_shared.py:925-948`). The promotion ladder must present both, never invent a "problems remaining to promote" gate.
- **Skill mastery** = primary solved at weighted score ≥ bar AND one reinforcement attempted (`compute_skill_progress`, `_shared.py:826`). Mastery dates are derived by `skill_mastery_dates` (`_shared.py:1773`).
- **Pace** = trailing-28-day window (`compute_pace`, `_shared.py:1808`), reused for projections; do not write a second pace computation.
- **Mocks** live in `progress.mock_interviews[]`, read via `mock_interview_entries` (`_shared.py:1080`); weekend window via `weekend_window` (`_shared.py:1089`).
- **Revisions done on a day** = `revision.history[]` events with that `date` (same walk as `activity_heatmap`, `_shared.py:2013`).
- Feed errors: `serve_dashboard.py:_serve_feed` 500s on any exception — hence plan-block errors must be caught inside `build_dashboard_feed`.

## Verification (run after each feature file, and at the end)

1. `make test` — all suites green (includes new `scripts/test_plan_feed.py`).
2. `node --check web_dashboard/app.js` — clean.
3. `python3 scripts/serve_dashboard.py` then load `http://127.0.0.1:8765/web_dashboard/` — zero console errors, new sections render.
4. Kill the server, open via `file://` or plain static — new feed-backed sections show the degraded banner, nothing throws.

## Unresolved questions (owner)

1. commit/stash the mock-selection WIP before execution — which?
2. `daily_review_capacity: 4` (lunch recall slot) — right number?
3. Sunday = revisions-only (no solve planned) per xlsx rules — confirm.
4. deload weeks: mock still planned (xlsx says yes, "one mock") — confirm.
5. after 2026-10-25: plan sections show "quarter ended, author next plan.json" — OK, or want auto-rollover template?
