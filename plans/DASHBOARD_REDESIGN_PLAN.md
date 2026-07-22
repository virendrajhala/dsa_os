# Dashboard Redesign ("Mission Deck") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> Read `plans/DASHBOARD_REDESIGN_DESIGN.md` FIRST — it is the spec this plan
> implements. Every visual/metric decision (tokens, palette hexes, feed
> schema, alignment matrix) lives there and is not re-argued here.

**Goal:** Rebuild the web dashboard as a scheduler-true, research-grounded
learning cockpit: Python computes everything via a new `/api/feed`; the UI
becomes a 4-workspace "mission deck" with new insight modules (review-load
forecast, retention split, hint independence, mock trend, skill
constellation) and a distinctive dark-first identity.

**Architecture:** `serve_dashboard.py` serves `GET /api/feed` built by a new
pure function `build_dashboard_feed(state, on_date)` in `scripts/_shared.py`
(same engine as the CLI — parity by construction). `web_dashboard/app.js`
drops its scheduler/readiness mirrors and renders the feed; static views
still read raw JSON so the page degrades gracefully without the server.

**Tech Stack:** Python 3 stdlib only; vanilla JS/CSS/SVG only; no build
step; no CDN assets (offline-first); unittest via `make test`.

## Global Constraints (from the repo owner — non-negotiable)

- Commits directly on `main`, ONE commit per task below, conventional format
  `type/scope: lowercase imperative subject ≤72 chars` + concise body, via
  HEREDOC. NO Co-Authored-By / AI attribution anywhere. Do NOT push.
- NEVER stage `GAPS_ANALYSIS.md`, `FIXES_PROPOSAL.md`, `.superpowers/`,
  `__pycache__/`, scratch files. Stage files explicitly by name.
- `progress/progress.json` is production data: byte-identical after every
  task (`git diff -- progress/progress.json` must be empty). Tests copy it
  to temp files, never write the live file.
- Python stdlib only. Dashboard vanilla JS only; after every JS edit run
  `node --check web_dashboard/app.js`.
- After EVERY task: `make test` AND `make validate` must pass before commit.
- TDD for all Python behavior: failing test first. For JS (no test harness):
  each task's Verify block is mandatory and includes serving + curling.
- Date logic: injectable `on_date` params only — never monkeypatch datetime.
  In JS, never `toISOString()` for day-strings (IST bug) — use the existing
  local `isoDate()` helper.
- Before visual tasks (4-8): load the `dataviz` skill and the
  `frontend-design` skill; every chart must follow the dataviz procedure
  (form → color-by-job → validated palette → mark specs → hover layer →
  a11y pass → render and look at it). The palette in the design doc §7 is
  already validated for the §7 surfaces — if you change ANY hex or surface,
  re-run: `node <dataviz-skill-dir>/scripts/validate_palette.js
  "<hex,...>" --mode dark --surface "#0E1620"` (and light vs `#F6F8F7`);
  the script is ESM — copy it next to a `package.json` containing
  `{"type":"module"}` and keep the filename `validate_palette.js`.
- Visual acceptance: after each of tasks 3-8, start
  `python3 scripts/serve_dashboard.py` (background), open/screenshot the
  page if a browser tool is available, otherwise verify via the curl matrix
  in the task; kill the server after. Zero console errors is part of done.

## File Structure

- `scripts/_shared.py` — add `build_dashboard_feed(state, on_date)` + small
  helpers (`review_forecast`, `retention_split`, `hint_trajectory_events`).
- `scripts/serve_dashboard.py` — `/api/feed` route.
- `scripts/test_dashboard_feed.py` — NEW test suite (wired into Makefile).
- `web_dashboard/index.html` — new shell: single rail nav, 4 workspaces,
  contextual toolbar, briefing band.
- `web_dashboard/styles.css` — token system rewrite (design §7), component
  styles.
- `web_dashboard/app.js` — feed consumption; delete mirrored logic; new
  modules (trajectory strip, forecast chart, hint chart, mock trend,
  constellation); restyled existing views.
- `README.md`, `HOW_TO_RUN.md` — dashboard section updates.

---

### Task 1: Feed engine in Python (`build_dashboard_feed`)

**Files:**
- Modify: `scripts/_shared.py` (append after `compute_readiness` family)
- Create: `scripts/test_dashboard_feed.py`
- Modify: `Makefile` (add the new suite to the `test` target)

**Interfaces:**
- Consumes: `select_next_problem(state, on_date)`, `revision_due_entries`,
  `quarterly_maintenance_entries`, `open_revision_entries`,
  `compute_readiness(state, on_date)`, `compute_pace`, `REVISION_POLICY`,
  `problem_lookup`, `load_repository_state()` (confirm exact loader name by
  reading `_shared.py` — `next_problem.py` shows the canonical way to build
  `RepositoryState`).
- Produces: `build_dashboard_feed(state: RepositoryState, on_date: date) ->
  dict` returning EXACTLY the schema in design doc §3 (keys:
  `generated_at, reference_date, next_action, revision_queue,
  review_forecast, readiness, retention, hint_trajectory, mock_history,
  policy`). Task 2 serves it; Task 4+ render it. Field names are LOAD-BEARING
  — JS consumes them verbatim.

- [ ] **Step 1: Write failing tests** — `scripts/test_dashboard_feed.py`,
  following the fixture style of `test_shared.py` (build `RepositoryState`
  from the live curriculum files + a constructed `progress` dict; never
  write live files):

```python
#!/usr/bin/env python3
"""Tests for build_dashboard_feed (dashboard = pure view of _shared)."""
from __future__ import annotations

import unittest
from datetime import date

import _shared
from _shared import (
    RepositoryState, build_dashboard_feed, load_json_file, select_next_problem,
)


def _state(progress):
    return RepositoryState(
        curriculum=load_json_file(_shared.CURRICULUM_PATH),
        graph=load_json_file(_shared.GRAPH_PATH),
        stages=load_json_file(_shared.STAGES_PATH),
        skills=load_json_file(_shared.SKILLS_PATH),
        patterns=load_json_file(_shared.PATTERNS_PATH),
        scoring=load_json_file(_shared.SCORING_PATH),
        progress=progress,
        progress_path=_shared.PROGRESS_PATH,
    )


def _completed(problem_id, next_due="2099-01-01", stage=1, status="ACTIVE"):
    return {
        "problem_id": problem_id, "completed_at": "2026-01-01",
        "hint_level_used": 2,
        "revision": {"status": status, "stage": stage,
                      "completed": ["2026-01-01"], "next_due": next_due,
                      "history": []},
    }


def _base_progress():
    return {
        "completed": [_completed(p) for p in
                       ["OBS-001", "OBS-002", "OBS-003", "CPX-001"]],
        "mastered_skills": [], "current_problem": None,
        "current_stage": "Observation", "mock_interviews": [],
    }


class FeedParityTests(unittest.TestCase):
    """The feed must agree with the CLI scheduler byte-for-byte."""

    def test_next_action_matches_scheduler_weekday(self):
        state = _state(_base_progress())
        on = date(2026, 7, 22)  # Wednesday
        feed = build_dashboard_feed(state, on)
        selection = select_next_problem(state, on_date=on)
        self.assertEqual(feed["next_action"]["mode"], selection.mode)
        expected_id = selection.problem["id"] if selection.problem else None
        self.assertEqual(feed["next_action"]["problem_id"], expected_id)

    def test_next_action_mock_due_on_weekend(self):
        progress = _base_progress()
        progress["mastered_skills"] = ["SK-OB-01"]
        state = _state(progress)
        feed = build_dashboard_feed(state, date(2026, 7, 25))  # Saturday
        selection = select_next_problem(state, on_date=date(2026, 7, 25))
        self.assertEqual(feed["next_action"]["mode"], selection.mode)
        if selection.mode == "mock_due":
            self.assertEqual(feed["next_action"]["problem_id"],
                             selection.problem["id"])

    def test_overdue_revision_wins_even_on_weekend(self):
        progress = _base_progress()
        progress["completed"][0] = _completed("OBS-001", next_due="2026-07-01")
        progress["mastered_skills"] = ["SK-OB-01"]
        state = _state(progress)
        feed = build_dashboard_feed(state, date(2026, 7, 25))
        self.assertEqual(feed["next_action"]["mode"], "revision")
        self.assertEqual(feed["next_action"]["problem_id"], "OBS-001")


class FeedShapeTests(unittest.TestCase):
    REQUIRED_KEYS = {
        "generated_at", "reference_date", "next_action", "revision_queue",
        "review_forecast", "readiness", "retention", "hint_trajectory",
        "mock_history", "policy",
    }

    def test_all_top_level_keys_present(self):
        feed = build_dashboard_feed(_state(_base_progress()), date(2026, 7, 22))
        self.assertEqual(set(feed) & self.REQUIRED_KEYS, self.REQUIRED_KEYS)

    def test_forecast_is_14_days_and_folds_overdue_into_day0(self):
        progress = _base_progress()
        progress["completed"][0] = _completed("OBS-001", next_due="2026-07-01")
        progress["completed"][1] = _completed("OBS-002", next_due="2026-07-30")
        feed = build_dashboard_feed(_state(progress), date(2026, 7, 22))
        forecast = feed["review_forecast"]
        self.assertEqual(len(forecast), 14)
        self.assertEqual(forecast[0]["date"], "2026-07-22")
        self.assertTrue(forecast[0]["overdue"])
        self.assertIn("OBS-001", forecast[0]["problem_ids"])
        day8 = next(d for d in forecast if d["date"] == "2026-07-30")
        self.assertIn("OBS-002", day8["problem_ids"])

    def test_retention_split_young_vs_mature(self):
        progress = _base_progress()
        progress["completed"][0]["revision"]["history"] = [
            {"date": "2026-02-01", "result": "PASS", "attempted_stage": 1},
            {"date": "2026-03-01", "result": "PASS", "attempted_stage": 3},
            {"date": "2026-04-01", "result": "FAIL", "attempted_stage": 4,
             "stage": 3},
        ]
        feed = build_dashboard_feed(_state(progress), date(2026, 7, 22))
        r = feed["retention"]
        self.assertEqual(r["counts"]["young_total"], 1)
        self.assertEqual(r["counts"]["mature_total"], 2)
        self.assertEqual(r["young_pass_rate"], 1.0)
        self.assertEqual(r["mature_pass_rate"], 0.5)

    def test_policy_block_mirrors_scoring(self):
        feed = build_dashboard_feed(_state(_base_progress()), date(2026, 7, 22))
        self.assertEqual(feed["policy"]["mastered_after_stage"],
                         _shared.MASTERED_AFTER_STAGE)
        self.assertEqual(feed["policy"]["intervals"]["R1"],
                         _shared.REVISION_INTERVAL_DAYS[0])

    def test_feed_is_json_serializable(self):
        import json as _json
        feed = build_dashboard_feed(_state(_base_progress()), date(2026, 7, 22))
        _json.dumps(feed)  # must not raise


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure** —
  `python3 scripts/test_dashboard_feed.py` → ImportError
  (`build_dashboard_feed` not defined).

- [ ] **Step 3: Implement `build_dashboard_feed` in `scripts/_shared.py`.**
  Skeleton (adapt names to what actually exists — read neighbors first;
  every value must come from existing `_shared` functions, never
  re-derived):

```python
def build_dashboard_feed(state: RepositoryState, on_date: date) -> JsonDict:
    """Everything the web dashboard renders, computed by the same engine as
    the CLI (design: plans/DASHBOARD_REDESIGN_DESIGN.md §3). Pure function;
    JSON-serializable output; never mutates state."""

    problems = problem_lookup(state.curriculum)
    selection = select_next_problem(state, on_date=on_date)
    next_action: JsonDict = {"mode": selection.mode, "problem_id": None,
                              "title": None, "url": None,
                              "reason": selection.reason, "stage_label": None}
    if selection.problem:
        p = selection.problem
        next_action.update(problem_id=p["id"], title=p.get("title"),
                            url=p.get("url"))
      solve_modes = {"resume_current_problem", "current_skill",
                   "current_stage", "earliest_unlocked"}
    if selection.mode in solve_modes and next_action["problem_id"]:
        path = ROOT / "solutions" / f"{next_action['problem_id']}.py"
        next_action["code_gate"] = {
            "solution_expected": f"solutions/{next_action['problem_id']}.py",
            "solution_exists": path.exists(),
        }
    # revision_queue: due + upcoming open revisions with kind + overdue flag
    # review_forecast: 14 buckets from on_date; overdue folds into day 0
    # readiness: compute_readiness(...) reshaped to the design §3 gate dict
    # retention: walk revision histories; attempted_stage <= 2 → young else mature
    # hint_trajectory: completions sorted by completed_at → {date, hint_level, problem_id}
    # mock_history: progress["mock_interviews"] passthrough (date, problem_id,
    #                verdict, duration_minutes, scores)
    # policy: {"mastered_after_stage": MASTERED_AFTER_STAGE,
    #           "intervals": {f"R{i+1}": d for i, d in REVISION_INTERVAL_DAYS.items()}}
    ...
    return feed
```

  Rules: stage labels via `revision_stage_label`; queue kinds via the same
  kind strings the due-entry helpers emit (`revision`,
  `quarterly_maintenance`; a record with `reactivated_on` → `reactivated`);
  dates via `format_iso_date`; `generated_at` =
  `datetime.now().isoformat(timespec="seconds")` (import datetime locally).

- [ ] **Step 4: Run the suite** — `python3 scripts/test_dashboard_feed.py`
  → all pass. Then `make test && make validate` → all pass.

- [ ] **Step 5: Wire into Makefile** — add
  `python3 scripts/test_dashboard_feed.py` to the `test` target, matching
  the existing lines exactly. Re-run `make test`.

- [ ] **Step 6: Commit**

```bash
git add scripts/_shared.py scripts/test_dashboard_feed.py Makefile
git commit -m "$(cat <<'EOF'
feat/dashboard: add build_dashboard_feed, the single brain for the web ui

computes next_action, revision queue + 14-day forecast, readiness,
young/mature retention split, hint trajectory, mock history and policy
from the same _shared functions the cli uses, so the dashboard can never
contradict next_problem.py or revision_report.py. parity pinned by tests.
EOF
)"
```

---

### Task 2: `/api/feed` endpoint + JS consumption (kill the mirrors)

**Files:**
- Modify: `scripts/serve_dashboard.py`
- Modify: `web_dashboard/app.js`
- Modify: `scripts/test_dashboard_feed.py` (endpoint test)

**Interfaces:**
- Consumes: `build_dashboard_feed` (Task 1).
- Produces: HTTP `GET /api/feed` → `200 application/json` (the Task-1
  schema; errors → `500` with `{"error": "..."}`). In app.js: global
  `state.feed` (object or `null`), helper `feedAvailable()`; ALL later
  tasks read `state.feed.*`.

- [ ] **Step 1: Failing endpoint test** (append to
  `scripts/test_dashboard_feed.py`) — start the server on a free port via
  `subprocess.Popen([sys.executable, "scripts/serve_dashboard.py", ...])`
  pattern; if the current server takes no port argument, add `--port` while
  you're in there (argparse, default unchanged). Assert:
  `GET /api/feed` → 200, `json.loads` succeeds, `next_action` key present,
  and `GET /web_dashboard/index.html` still 200. Poll-with-timeout for
  startup; `terminate()` in `finally`.

- [ ] **Step 2: Implement.** In `serve_dashboard.py`, subclass the existing
  handler; route `/api/feed`:

```python
def do_GET(self):
    if self.path.rstrip("/") == "/api/feed":
        try:
            state = load_repository_state()   # same loader the CLI uses
            feed = build_dashboard_feed(state, date.today())
            body = json.dumps(feed).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:  # never kill the server on bad data
            body = json.dumps({"error": str(exc)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        return
    super().do_GET()
```

- [ ] **Step 3: app.js consumes the feed.** In `loadData()`, fetch
  `/api/feed` alongside the datasets; failure → `state.feed = null` (no
  throw). Delete the now-mirrored functions and their call sites:
  `nextAction`, `readinessConfig`, `coreSkillIdsInScope`,
  `computeCoreMasteryStatus`, `computeRevisionPassRate`,
  `computeRecentMockStatus`, `skillMasteryDates`, `computePace`,
  `projectReadinessDate`, `computeReadiness`. Temporarily point their
  renderers (`renderNextAction`, `renderReadiness`, metrics) at
  `state.feed` with a guard: when `state.feed` is null render the degraded
  banner: "Live briefing needs the server — run `python3
  scripts/serve_dashboard.py`" (styling comes in Task 4; keep markup
  minimal now). Fix the frozen date while here: `today` becomes a function
  `todayDate()` evaluated per render + a `visibilitychange` listener
  calling `renderAll()`.

- [ ] **Step 4: Verify** — `node --check web_dashboard/app.js`;
  `python3 scripts/test_dashboard_feed.py` (all pass incl. endpoint);
  `make test && make validate`; serve + `curl -s localhost:<port>/api/feed
  | python3 -m json.tool | head`; load the page — Today panels populate
  from the feed, console clean; stop server, reload page → degraded banner,
  static views still render, console free of uncaught errors.

- [ ] **Step 5: Commit**

```bash
git add scripts/serve_dashboard.py scripts/test_dashboard_feed.py web_dashboard/app.js
git commit -m "$(cat <<'EOF'
feat/dashboard: serve /api/feed and delete the js scheduler mirrors

the dashboard renders what python computes: next action, readiness and
pace now come from build_dashboard_feed via serve_dashboard, removing the
drifted client reimplementations (weekend mocks were invisible in the ui).
without the server the page degrades to static views plus a banner. today
is recomputed per render instead of frozen at page load.
EOF
)"
```

---

### Task 3: Token system, theme toggle, single-nav shell (4 workspaces)

**Files:**
- Modify: `web_dashboard/index.html`, `web_dashboard/styles.css`,
  `web_dashboard/app.js` (nav wiring + theme)

**Interfaces:**
- Produces: CSS custom properties EXACTLY as design §7 (`--bg --surface
  --surface-2 --line --text --muted --good --warn --bad --accent`, plus
  `--series-1..8`); `data-theme` on `<html>`; workspaces renamed to
  `today | practice | curriculum | evidence`; `data-workspace-section`
  values migrated (`analytics` → `evidence`). Later tasks style against
  these tokens ONLY — no raw hex in component CSS.

- [ ] **Step 1: styles.css** — replace `:root` with the §7 dark/light token
  blocks (dark is default via `:root:not([data-theme="light"])`); add
  `--series-1..8` per mode from the §7 table; type rules: mono stack class
  `.num` (`font-family: ui-monospace, "JetBrains Mono", "Cascadia Code",
  "Fira Code", monospace; font-variant-numeric: tabular-nums;`) applied to
  all numerals/pills/eyebrows; uppercase micro-label class `.microlabel`
  (11px / 0.08em tracking / `--muted`); graph-paper texture class
  `.gridpaper` (two repeating-linear-gradients, 24px cell, 4% alpha of
  `--line`).
- [ ] **Step 2: index.html** — delete the topbar workspace-tab row; sidebar
  becomes the single nav (4 groups matching the workspaces, section links
  under each); move search/filters into a `.toolbar` block rendered inside
  Curriculum and Evidence section heads only; retitle brand block
  ("DSA OS — Mission Deck"); add theme toggle button in the rail footer.
- [ ] **Step 3: app.js** — theme: read `localStorage.theme` else
  `matchMedia("(prefers-color-scheme: light)")`, stamp `data-theme`, toggle
  persists; migrate `switchWorkspace` to 4 workspaces; every element that
  had `data-workspace-section="analytics"` becomes `"evidence"`; filters:
  guard so views without the toolbar don't bind missing inputs.
- [ ] **Step 4: Verify** — `node --check`; serve; click all 4 workspaces;
  toggle theme both ways + reload (persists); search/filters exist ONLY on
  Curriculum/Evidence and still filter; `make test && make validate`;
  progress.json untouched.
- [ ] **Step 5: Commit** — `feat/dashboard: dark-first token system, single
  rail nav, four workspaces` (body: what moved where, theme persistence).

---

### Task 4: Today = mission briefing

**Files:** `web_dashboard/index.html`, `styles.css`, `app.js`

**Interfaces:** Consumes `state.feed.next_action / revision_queue /
review_forecast / readiness / retention`. Produces renderers
`renderBriefing()` (next-action card), `renderTrajectory()`,
`renderDueQueue()`, `renderForecast()`, `renderPaceTiles()` — all called
from `renderAll()`; each renders a degraded placeholder when
`state.feed == null`.

- [ ] **Step 1: Next Action card** — four mode treatments per design §6;
  `mock_due` gets accent border + "MOCK" eyebrow + protocol line
  "45-minute cap · no hints · verdict at the end"; the four solve modes
  (`resume_current_problem`, `current_skill`, `current_stage`,
  `earliest_unlocked`) share one "solve" treatment and show the code-gate
  line from `next_action.code_gate` ("solution file: present" / "will be
  required"). Problem title links via existing modal opener.
- [ ] **Step 2: Trajectory strip** (hero, `.gridpaper` band) — one
  horizontal line, three gate stations from `feed.readiness.gates`
  (mono current/target under each, met = `--good` dot + ✓, unmet = outlined
  dot), terminus = projected date (large mono). Load animation: stations
  fade/slide in staggered 80ms; wrap in
  `@media (prefers-reduced-motion: no-preference)`.
- [ ] **Step 3: Due queue** — compact rows: title, kind pill
  (`R2` / `Q-maint` / `reactivated` from `stage_label`/`kind`), due date,
  overdue rows carry `--bad` icon + "overdue" label (never color alone).
- [ ] **Step 4: Forecast chart** — 14 bars from `feed.review_forecast`;
  sequential single hue (`--series-1`); day-0 overdue bucket = `--bad` +
  ⚠ label; 4px rounded tops anchored to baseline, 2px gaps, hover tooltip
  (date + count + ids), recessive weekday axis in `.microlabel`. Direct
  count labels on non-zero bars (light-mode relief rule).
- [ ] **Step 5: Pace tiles** — problems/wk, skills/wk, sessions-30d
  (`uniqueSolvedDays` on completions) as mono stat tiles with muted notes.
- [ ] **Step 6: Verify** — `node --check`; serve; screenshot/eyeball vs §6
  (5 elements, nothing else on Today); kill server → every module shows its
  degraded placeholder, no console errors; `make test && make validate`.
- [ ] **Step 7: Commit** — `feat/dashboard: rebuild today as a
  scheduler-true mission briefing`.

---

### Task 5: Evidence — hint independence, mock trend, retention; dissolve Analytics

**Files:** `web_dashboard/index.html`, `styles.css`, `app.js`

**Interfaces:** Consumes `feed.hint_trajectory`, `feed.mock_history`,
`feed.retention`, `feed.policy`. Produces `renderHintIndependence()`,
`renderMockTrend()`, `renderRetentionTiles()`; deletes `renderAnalytics`
and every `analytics*` helper (`analyticsTab` … `analyticsBar`), keeping
ONLY `analyticsConsistencyLineChart` renamed `renderConsistency()` and
restyled with tokens.

- [ ] **Step 1: Hint-independence chart** — line (2px, `--series-1`),
  x = solve index (dated ticks), y = hint level 0-7 inverted-is-better;
  three horizontal bands tinted at 4% alpha with `.microlabel` names
  matching the discount tiers: 0-2 "independent", 3-4 "guided", 5-7
  "rescued" (band edges from `feed.policy` — hint tiers are fixed 0-7 but
  label text must say they mirror `hint_mastery_discount`). Rolling mean
  (window 5) as the line; raw solves as 8px markers; hover tooltip
  (problem, date, level).
- [ ] **Step 2: Mock trend** — verdict timeline: one dot per mock on a date
  axis, verdict encoded by status color + label chip (strong-hire/hire =
  `--good`, no-hire = `--warn`, strong-no-hire = `--bad`, ALWAYS with text
  chip); below, five small-multiple sparklines (one per rubric dimension,
  1-4 scale, `--series-1`, direct last-value label). Empty state: "No mocks
  recorded yet — first weekend mock is scheduled automatically."
- [ ] **Step 3: Retention tiles** — overall / young / mature pass-rate mono
  tiles; healthy band note "target ≥ 90%" (from `feed.readiness` gate
  target); mature `null` → "no R3+ reviews yet".
- [ ] **Step 4: Dissolve Analytics** — move consistency chart into
  Evidence; delete the analytics section, nav entry, and dead helpers; grep
  `analytics` in app.js/index.html/styles.css → only historical CSS to
  delete may remain, zero JS references.
- [ ] **Step 5: Verify** — `node --check`; serve; Evidence shows history,
  thinking profile, hint chart, mock trend, retention tiles, consistency,
  deferred learning; empty-state copy correct with current data (0 mocks →
  empty state); console clean; `make test && make validate`.
- [ ] **Step 6: Commit** — `feat/dashboard: evidence insights — hint
  independence, mock trend, retention split`.

---

### Task 6: Curriculum — Skill Constellation (signature)

**Files:** `web_dashboard/index.html`, `styles.css`, `app.js`

**Interfaces:** Consumes `state.datasets.graph.skill_dependencies`,
`skills.skill_order`, `stages.stage_order`, `progress.mastered_skills`,
existing `openSingleSkillModal(skillId)`. Produces
`renderConstellation()` building inline SVG in `#constellation`.

- [ ] **Step 1: Layout algorithm** (pure, no libs):

```js
function constellationLayout() {
  const stages = state.datasets.stages.stage_order;
  const order = state.datasets.skills.skill_order;
  const byStage = new Map(stages.map((s) => [s, []]));
  for (const id of order) {
    const stage = skillMeta(id)?.stage;
    if (byStage.has(stage)) byStage.get(stage).push(id);
  }
  const COL_W = 120, ROW_H = 46, PAD = 40;
  const pos = new Map();
  stages.forEach((stage, col) => {
    byStage.get(stage).forEach((id, row) => {
      pos.set(id, { x: PAD + col * COL_W, y: PAD + 24 + row * ROW_H });
    });
  });
  return { pos, width: PAD * 2 + stages.length * COL_W,
           height: PAD * 2 + 24 +
             Math.max(...stages.map((s) => byStage.get(s).length)) * ROW_H };
}
```

- [ ] **Step 2: Render** — edges first (`<path>` cubic curves between
  prereq→skill, `--line`, 1px, 35% opacity), then nodes (`<circle>` r 5-11
  by problem count; fill per design §8 state encoding: mastered `--good`,
  current skill `--accent` ring, unlocked outlined, locked 25% opacity),
  stage names as vertical column headers in `.microlabel`. Container:
  `overflow-x: auto`.
- [ ] **Step 3: Interaction** — hover: raise node, set `.dim` on all edges
  except ancestor path + direct dependents (walk `skill_dependencies`
  reverse map), tooltip (name, stage, n problems, state); click →
  `openSingleSkillModal(id)`; keyboard: nodes are `tabindex="0"` with
  `Enter` opening the modal; `prefers-reduced-motion` skips the raise
  transition. The skills table below is unchanged (it is the table view).
- [ ] **Step 4: Verify** — `node --check`; serve; 93 nodes, 13 columns; the
  1 mastered skill glows good; hover isolates paths; click opens modal;
  tab order reaches nodes; horizontal scroll at 1024px; console clean;
  `make test && make validate`.
- [ ] **Step 5: Commit** — `feat/dashboard: skill constellation — the
  curriculum dag as an explorable map`.

---

### Task 7: Modals + Practice restyle; mentor-score comparison

**Files:** `web_dashboard/app.js`, `styles.css`

- [ ] **Step 1: Problem modal additions** — (a) when a completion record
  has `mentor_scores`, render self vs mentor columns for both score blocks;
  any dimension differing by > 2 gets `--warn` chip "discuss" (F7
  divergence rule); (b) when `solutions/<ID>.py` was part of the record
  (code gate passed / `--no-code` noted in notes), show the solution path
  as mono text. Revision history items keep per-dimension recall +
  misconception (already rendered) — restyle with tokens.
- [ ] **Step 2: Practice restyle** — weakness lab cards + edge checklist
  onto tokens; weakness source chips (`mock`, `revision.fail`, `solve`)
  in `.microlabel`; no logic changes.
- [ ] **Step 3: Verify** — `node --check`; serve; open a problem with
  mentor scores (OBS-009/010 era records) and one without; modal focus
  trap works (native dialog); Practice reads correctly in both themes;
  `make test && make validate`.
- [ ] **Step 4: Commit** — `enhancement/dashboard: mentor-vs-self scores in
  modal, practice restyle`.

---

### Task 8: Quality floor — responsive, a11y, polish, dead-code sweep

**Files:** `web_dashboard/styles.css`, `app.js`, `index.html`

- [ ] **Step 1: Responsive** — rail collapses to icon column ≤1024px;
  briefing stacks single-column ≤900px; nothing overflows the viewport
  horizontally except intentional scroll containers (constellation, tables).
- [ ] **Step 2: A11y** — visible `:focus-visible` rings (`--accent`,
  2px offset); all icon-only buttons get `aria-label`; charts have
  `role="img"` + `aria-label` summaries; verify status is never
  color-alone (grep for `--good/--warn/--bad` usages: each must pair with
  text/icon).
- [ ] **Step 3: Empty/error states** — every module has real copy (design
  §"writing": direction, not mood): degraded-mode banner, no-mocks, no
  weaknesses, empty forecast ("Nothing due in the next 14 days").
- [ ] **Step 4: Dead-code sweep** — grep app.js/styles.css for: deleted
  mirror functions, `analytics`, `workspace-tab`, unused CSS classes
  (spot-check by class grep against index.html/app.js); delete remnants.
- [ ] **Step 5: Verify (full matrix)** — `node --check`; serve; per
  workspace × per theme: console clean; keyboard-only walk of Today +
  constellation; 1024px and 768px window widths; kill server → degraded
  mode everywhere, still no errors; `make test && make validate`;
  `git diff -- progress/progress.json` empty.
- [ ] **Step 6: Commit** — `chore/dashboard: responsive rail, focus states,
  empty-state copy, dead-code sweep`.

---

### Task 9: Docs + final review gate

**Files:** `README.md`, `HOW_TO_RUN.md`

- [ ] **Step 1: Docs** — README dashboard section: 4 workspaces, `/api/feed`
  (server required for the briefing; static views degrade), theme toggle.
  HOW_TO_RUN: replace any stale dashboard walkthrough lines.
- [ ] **Step 2: Alignment-matrix audit** — walk design doc §3b row by row;
  for each row write file:line of the rendering surface; any unmet row goes
  back to its task before this task commits.
- [ ] **Step 3: Dataviz anti-pattern check** — reread
  `<dataviz-skill>/references/anti-patterns.md`; check every chart (forecast,
  hint, mock sparklines, consistency, thinking bars) against it; fix hits.
- [ ] **Step 4: Final state check** —
  `make test && make validate && python3 scripts/next_problem.py &&
  python3 scripts/revision_report.py && python3 scripts/dashboard.py` all
  clean; serve + full curl matrix (index, styles, app.js, api/feed, all 8
  data files → 200).
- [ ] **Step 5: Commit** — `docs/dashboard: mission deck usage + feed notes`.
- [ ] **Step 6: Independent review** — fresh-context reviewer reads the
  design doc + `git log` for this plan's commits and verifies: alignment
  matrix complete, palette hexes match §7 verbatim (or a validator rerun is
  attached), parity tests exist and pass, no JS recomputation of
  `_shared`-computable values. Fix Critical/Important findings, re-verify,
  report Minors.

## Self-review notes (already applied)

- Every metric in design §4 has a rendering task (1:1 checked).
- Feed field names consistent across Tasks 1/2/4/5 (`review_forecast`,
  `hint_trajectory`, `mock_history`, `policy`).
- No placeholder steps: each step names exact files, code or checkable
  criteria, and its verify command.
- Task order is dependency order: 1→2 (feed), 3 (tokens) before 4-8
  (visuals), 9 last.
