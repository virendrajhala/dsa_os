# Feature 02 — Plan Metrics Engine + Feed Block

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Requires Feature 01 complete. Read `00_OVERVIEW.md` first.

**Goal:** Every plan-vs-actual number (today contract, week scoreboard, quarter burn-up, month milestones, promotion ladder, time invested) computed in `_shared.py` and shipped on `GET /api/feed`.

**Architecture:** Pure functions appended to `scripts/_shared.py` after the Feature-01 plan helpers. `build_dashboard_feed` gains three keys: `plan` (null when no plan.json; `{"error": ...}` when invalid — a broken plan must never 500 the feed, see `serve_dashboard.py:32-49`), `promotion`, `time_invested`. Milestones derive from curriculum order + weekly targets so they re-plan automatically.

**Tech Stack:** Python 3 stdlib, `unittest` (extend `scripts/test_plan_feed.py`).

## Global constraints

- Reuse, never re-derive: pace from `compute_pace` (`_shared.py:1808`), skill mastery from `compute_skill_progress`/`skill_mastery_dates`, mocks from `mock_interview_entries` + `weekend_window`, due revisions from `revision_due_entries`, stage checks from `recompute_score_summary`.
- All outputs JSON-serializable dicts/lists of str/int/float/bool/None.
- Tests pass explicit `progress` + `plan` dicts; never assert against live `progress.json` numbers.
- Commit style `feat/plan: ...`; no Co-Authored-By.

## Contract produced (consumed by Features 03-06)

See `00_OVERVIEW.md` §Shared contract for the full JSON shape of `feed.plan`, `feed.promotion`, `feed.time_invested`. Field names there are normative.

---

### Task 1: Range helpers + expected-solves curve

**Files:**
- Modify: `scripts/_shared.py` (append after `plan_week_for`)
- Modify: `scripts/test_plan_feed.py` (append test classes)

**Interfaces:**
- Consumes: `completed_records`, `_completion_date`, `mock_interview_entries`, `parse_iso_date`, `plan_week_bounds` (Feature 01).
- Produces:
  - `solves_in_range(progress: JsonDict, start: date, end: date) -> int`
  - `mock_entries_in_range(progress: JsonDict, start: date, end: date) -> list[JsonDict]`
  - `revision_events_in_range(progress: JsonDict, start: date, end: date) -> list[JsonDict]` — graded PASS/FAIL history events only (same walk as `activity_heatmap`, `_shared.py:2013`).
  - `plan_expected_solves(plan: JsonDict, on_date: date) -> float` — cumulative planned solves through `on_date`, linear within a week.

- [ ] **Step 1: Write the failing tests.** Append to `scripts/test_plan_feed.py` (below the existing classes; the `_plan()` fixture from Feature 01 Task 2 is reused). Also add these shared fixtures right under `_plan()`:

```python
from _shared import (
    RepositoryState, build_dashboard_feed, load_json_file,
    build_plan_feed, compute_month_milestones, compute_quarter_burnup,
    compute_today_contract, compute_week_scoreboard, mock_entries_in_range,
    plan_expected_solves, promotion_ladder, revision_events_in_range,
    solves_in_range, time_invested,
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


def _completed(problem_id, completed_at, minutes=45, next_due="2099-01-01"):
    return {
        "problem_id": problem_id, "completed_at": completed_at,
        "time_taken_minutes": minutes, "hint_level_used": 2,
        "revision": {"status": "ACTIVE", "stage": 1,
                     "completed": [completed_at], "next_due": next_due,
                     "history": []},
    }


def _progress(records=(), mocks=()):
    return {
        "completed": list(records), "mastered_skills": [],
        "current_problem": None, "current_stage": "Observation",
        "mock_interviews": list(mocks),
    }
```

Then the test class:

```python
class RangeHelperTests(unittest.TestCase):
    def test_solves_in_range_inclusive_bounds(self):
        progress = _progress([
            _completed("OBS-001", "2026-07-27"),
            _completed("OBS-002", "2026-07-29"),
            _completed("OBS-003", "2026-08-03"),
        ])
        self.assertEqual(
            solves_in_range(progress, date(2026, 7, 27), date(2026, 8, 2)), 2)
        self.assertEqual(
            solves_in_range(progress, date(2026, 7, 27), date(2026, 8, 3)), 3)

    def test_mock_entries_in_range(self):
        progress = _progress(mocks=[
            {"date": "2026-08-01", "problem_id": "TWO-001", "verdict": "hire"},
            {"date": "2026-08-08", "problem_id": "WIN-001", "verdict": "no-hire"},
        ])
        found = mock_entries_in_range(progress, date(2026, 7, 27), date(2026, 8, 2))
        self.assertEqual([m["problem_id"] for m in found], ["TWO-001"])

    def test_revision_events_only_graded_results(self):
        record = _completed("OBS-001", "2026-07-01")
        record["revision"]["history"] = [
            {"date": "2026-07-28", "result": "PASS", "attempted_stage": 1},
            {"date": "2026-07-29", "result": "FAIL", "attempted_stage": 2},
            {"date": "2026-07-30", "result": "REACTIVATED", "stage": 1},
        ]
        events = revision_events_in_range(
            _progress([record]), date(2026, 7, 27), date(2026, 8, 2))
        self.assertEqual(len(events), 2)

    def test_expected_solves_linear_within_week(self):
        plan = _plan()
        # Wed of week 1: 3 of 7 days elapsed -> 6 * 3/7
        self.assertAlmostEqual(
            plan_expected_solves(plan, date(2026, 7, 29)), 6 * 3 / 7, places=4)
        # deload week 2 adds nothing
        self.assertAlmostEqual(plan_expected_solves(plan, date(2026, 8, 9)), 6.0, places=4)
        # end of quarter = full target
        self.assertAlmostEqual(plan_expected_solves(plan, date(2026, 8, 16)), 12.0, places=4)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 scripts/test_plan_feed.py`
Expected: `ImportError` on the new names.

- [ ] **Step 3: Implement.** Append to `scripts/_shared.py`:

```python
def solves_in_range(progress: JsonDict, start: date, end: date) -> int:
    """Count completion records dated within [start, end] inclusive."""

    return sum(
        1
        for record in completed_records(progress)
        if (completed_on := _completion_date(record)) is not None
        and start <= completed_on <= end
    )


def mock_entries_in_range(progress: JsonDict, start: date, end: date) -> list[JsonDict]:
    """Return recorded mock interviews dated within [start, end] inclusive."""

    found: list[JsonDict] = []
    for entry in mock_interview_entries(progress):
        raw = entry.get("date")
        if not isinstance(raw, str):
            continue
        try:
            when = parse_iso_date(raw, "mock_interviews.date")
        except RepositoryError:
            continue
        if start <= when <= end:
            found.append(entry)
    return found


def revision_events_in_range(progress: JsonDict, start: date, end: date) -> list[JsonDict]:
    """Graded (PASS/FAIL) revision history events dated within [start, end]."""

    events: list[JsonDict] = []
    for record in completed_records(progress):
        revision = record.get("revision")
        history = revision.get("history") if isinstance(revision, dict) else None
        if not isinstance(history, list):
            continue
        for event in history:
            if not isinstance(event, dict) or event.get("result") not in {"PASS", "FAIL"}:
                continue
            raw = event.get("date")
            if not isinstance(raw, str):
                continue
            try:
                when = parse_iso_date(raw, "revision.history.date")
            except RepositoryError:
                continue
            if start <= when <= end:
                events.append(event)
    return events


def plan_expected_solves(plan: JsonDict, on_date: date) -> float:
    """Cumulative planned solves through `on_date`, linear within a week."""

    total = 0.0
    for week in plan.get("weeks", []):
        start, end = plan_week_bounds(week)
        target = float(week.get("target_solves", 0))
        if on_date >= end:
            total += target
        elif on_date >= start:
            total += target * ((on_date - start).days + 1) / 7.0
    return total
```

- [ ] **Step 4: Run tests** — `python3 scripts/test_plan_feed.py` → PASS.
- [ ] **Step 5: Commit** — `git add scripts/_shared.py scripts/test_plan_feed.py && git commit -m "feat/plan: range helpers and expected-solve curve"`

---

### Task 2: Today contract + week scoreboard + week history

**Files:**
- Modify: `scripts/_shared.py`, `scripts/test_plan_feed.py`

**Interfaces:**
- Consumes: Task 1 helpers, `plan_week_for`/`plan_week_bounds`, `revision_due_entries(progress, on_date)`, `weekend_window`, `compute_skill_progress(curriculum, skills, scoring, progress)`, `skill_mastery_dates(skills, progress, skill_progress)`.
- Produces:
  - `compute_today_contract(state: RepositoryState, plan: JsonDict, on_date: date) -> JsonDict`
  - `compute_week_scoreboard(state, plan, on_date) -> JsonDict | None` — `None` outside the quarter.
  - `compute_week_history(state, plan, on_date) -> list[JsonDict]` — one row per started week.

- [ ] **Step 1: Failing tests** — append:

```python
class TodayContractTests(unittest.TestCase):
    def test_weekday_solve_planned_and_done(self):
        progress = _progress([_completed("OBS-001", "2026-07-28")])
        contract = compute_today_contract(_state(progress), _plan(), date(2026, 7, 28))
        self.assertTrue(contract["solve"]["planned"])
        self.assertTrue(contract["solve"]["done"])
        self.assertFalse(contract["deload"])

    def test_sunday_has_no_solve_planned(self):
        contract = compute_today_contract(_state(_progress()), _plan(), date(2026, 8, 2))
        self.assertFalse(contract["solve"]["planned"])
        self.assertTrue(contract["mock"]["planned"])  # Sunday is in the weekend window

    def test_deload_week_plans_no_solve_but_keeps_mock(self):
        # 2026-08-05 is the Wednesday of fixture week 2 (deload).
        contract = compute_today_contract(_state(_progress()), _plan(), date(2026, 8, 5))
        self.assertTrue(contract["deload"])
        self.assertFalse(contract["solve"]["planned"])

    def test_revisions_due_and_cleared(self):
        overdue = _completed("OBS-001", "2026-07-01", next_due="2026-07-27")
        contract = compute_today_contract(
            _state(_progress([overdue])), _plan(), date(2026, 7, 28))
        self.assertEqual(contract["revisions"]["due"], 1)
        self.assertFalse(contract["revisions"]["cleared"])

    def test_mock_done_inside_weekend_window(self):
        progress = _progress(mocks=[{"date": "2026-08-01", "problem_id": "TWO-001"}])
        contract = compute_today_contract(_state(progress), _plan(), date(2026, 8, 2))
        self.assertTrue(contract["mock"]["done"])

    def test_outside_quarter(self):
        contract = compute_today_contract(_state(_progress()), _plan(), date(2026, 8, 20))
        self.assertFalse(contract["in_quarter"])
        self.assertFalse(contract["solve"]["planned"])


class WeekScoreboardTests(unittest.TestCase):
    def test_counts_and_on_track(self):
        progress = _progress([
            _completed("OBS-001", "2026-07-27"),
            _completed("OBS-002", "2026-07-28"),
            _completed("OBS-003", "2026-07-29"),
        ])
        board = compute_week_scoreboard(_state(progress), _plan(), date(2026, 7, 29))
        self.assertEqual(board["week"], 1)
        self.assertEqual(board["target_solves"], 6)
        self.assertEqual(board["actual_solves"], 3)
        self.assertAlmostEqual(board["expected_to_date"], round(6 * 3 / 7, 2))
        self.assertTrue(board["on_track"])
        self.assertEqual(board["days_remaining"], 4)

    def test_behind_plan_is_not_on_track(self):
        progress = _progress([_completed("OBS-001", "2026-07-27")])
        board = compute_week_scoreboard(_state(progress), _plan(), date(2026, 7, 31))
        self.assertFalse(board["on_track"])

    def test_revision_and_mock_actuals(self):
        record = _completed("OBS-001", "2026-07-01")
        record["revision"]["history"] = [
            {"date": "2026-07-28", "result": "PASS", "attempted_stage": 1},
            {"date": "2026-07-29", "result": "FAIL", "attempted_stage": 2},
        ]
        progress = _progress([record], mocks=[{"date": "2026-08-01", "problem_id": "TWO-001"}])
        board = compute_week_scoreboard(_state(progress), _plan(), date(2026, 8, 1))
        self.assertEqual(board["revisions_done"], 2)
        self.assertEqual(board["revisions_passed"], 1)
        self.assertTrue(board["mock_done"])

    def test_none_outside_quarter(self):
        self.assertIsNone(
            compute_week_scoreboard(_state(_progress()), _plan(), date(2026, 8, 20)))

    def test_week_history_covers_started_weeks_only(self):
        from _shared import compute_week_history
        progress = _progress([_completed("OBS-001", "2026-07-27")])
        rows = compute_week_history(_state(progress), _plan(), date(2026, 8, 5))
        self.assertEqual([row["week"] for row in rows], [1, 2])
        self.assertEqual(rows[0]["actual_solves"], 1)
```

- [ ] **Step 2: Run to verify failure** — `python3 scripts/test_plan_feed.py` → ImportError/AttributeError.

- [ ] **Step 3: Implement.** Append to `scripts/_shared.py`:

```python
def compute_today_contract(state: RepositoryState, plan: JsonDict, on_date: date) -> JsonDict:
    """Today's plan-vs-actual checklist: solve, revisions cleared, weekend mock.

    Sunday plans no new solve (revisions-sweep day) and deload weeks plan none
    at all — both from the quarter plan's rules. The mock check spans the
    whole Saturday-Sunday window, mirroring `is_mock_due`.
    """

    progress = state.progress
    week = plan_week_for(plan, on_date)
    in_quarter = week is not None
    deload = bool(week and week.get("deload"))
    solve_planned = in_quarter and not deload and on_date.weekday() != 6
    today = format_iso_date(on_date)
    solve_done = any(
        record.get("completed_at") == today for record in completed_records(progress)
    )
    due = revision_due_entries(progress, on_date)
    window = weekend_window(on_date)
    mock_planned = in_quarter and window is not None and bool(week.get("mock", True))
    mock_done = bool(window and mock_entries_in_range(progress, window[0], window[1]))
    return {
        "in_quarter": in_quarter,
        "deload": deload,
        "solve": {"planned": solve_planned, "done": solve_done},
        "revisions": {
            "due": len(due),
            "done_today": len(revision_events_in_range(progress, on_date, on_date)),
            "cleared": not due,
        },
        "mock": {"planned": mock_planned, "done": mock_done},
    }


def compute_week_scoreboard(
    state: RepositoryState, plan: JsonDict, on_date: date
) -> JsonDict | None:
    """Current plan week: targets vs actuals. None outside the quarter."""

    week = plan_week_for(plan, on_date)
    if week is None:
        return None
    progress = state.progress
    start, end = plan_week_bounds(week)
    upto = min(on_date, end)
    target = int(week.get("target_solves", 0))
    actual = solves_in_range(progress, start, upto)
    expected = round(target * ((upto - start).days + 1) / 7.0, 2)
    events = revision_events_in_range(progress, start, upto)
    skill_progress = compute_skill_progress(
        state.curriculum, state.skills, state.scoring, progress
    )
    mastery_dates = skill_mastery_dates(state.skills, progress, skill_progress)
    mastered = sorted(
        skill_id
        for skill_id, mastered_on in mastery_dates.items()
        if mastered_on is not None and start <= mastered_on <= upto
    )
    return {
        "week": week.get("week"),
        "start": format_iso_date(start),
        "end": format_iso_date(end),
        "deload": bool(week.get("deload")),
        "target_solves": target,
        "actual_solves": actual,
        "expected_to_date": expected,
        "on_track": actual + 1e-9 >= expected,
        "mock_planned": bool(week.get("mock")),
        "mock_done": bool(mock_entries_in_range(progress, start, upto)),
        "revisions_done": len(events),
        "revisions_passed": sum(1 for event in events if event.get("result") == "PASS"),
        "skills_mastered": mastered,
        "days_remaining": max((end - on_date).days, 0),
    }


def compute_week_history(
    state: RepositoryState, plan: JsonDict, on_date: date
) -> list[JsonDict]:
    """Target-vs-actual for every week that has started (for the mini bars)."""

    rows: list[JsonDict] = []
    for week in plan.get("weeks", []):
        start, end = plan_week_bounds(week)
        if start > on_date:
            break
        upto = min(on_date, end)
        rows.append(
            {
                "week": week.get("week"),
                "start": format_iso_date(start),
                "deload": bool(week.get("deload")),
                "target_solves": int(week.get("target_solves", 0)),
                "actual_solves": solves_in_range(state.progress, start, upto),
                "mock_done": bool(mock_entries_in_range(state.progress, start, upto)),
            }
        )
    return rows
```

- [ ] **Step 4: Run tests** — PASS.
- [ ] **Step 5: Commit** — `git commit -am "feat/plan: today contract and week scoreboard"`

---

### Task 3: Quarter burn-up

**Files:**
- Modify: `scripts/_shared.py`, `scripts/test_plan_feed.py`

**Interfaces:**
- Consumes: `compute_pace`, `compute_skill_progress`, Task 1 helpers.
- Produces: `compute_quarter_burnup(state, plan, on_date) -> JsonDict` (shape in `00_OVERVIEW.md`).

- [ ] **Step 1: Failing tests:**

```python
class BurnupTests(unittest.TestCase):
    def test_planned_curve_and_actuals(self):
        progress = _progress([
            _completed("OBS-001", "2026-07-27"),
            _completed("OBS-002", "2026-07-27"),
            _completed("OBS-003", "2026-07-30"),
        ])
        burnup = compute_quarter_burnup(_state(progress), _plan(), date(2026, 8, 1))
        self.assertEqual(burnup["target_total"], 12)
        self.assertEqual(
            [point["cumulative"] for point in burnup["planned"]], [6, 6, 12])
        self.assertEqual(burnup["planned"][0]["date"], "2026-08-02")
        self.assertEqual(
            burnup["actual"], [
                {"date": "2026-07-27", "cumulative": 2},
                {"date": "2026-07-30", "cumulative": 3},
            ])
        self.assertEqual(burnup["actual_total"], 3)

    def test_required_pace_uses_remaining_weeks(self):
        progress = _progress([_completed("OBS-001", "2026-07-27")])
        on = date(2026, 8, 2)
        burnup = compute_quarter_burnup(_state(progress), _plan(), on)
        weeks_remaining = (date(2026, 8, 16) - on).days / 7
        self.assertAlmostEqual(
            burnup["required_per_week"], round(11 / weeks_remaining, 2))

    def test_quarter_over_returns_null_required_pace(self):
        burnup = compute_quarter_burnup(_state(_progress()), _plan(), date(2026, 8, 17))
        self.assertIsNone(burnup["required_per_week"])

    def test_solves_before_quarter_do_not_count(self):
        progress = _progress([_completed("OBS-001", "2026-07-20")])
        burnup = compute_quarter_burnup(_state(progress), _plan(), date(2026, 7, 28))
        self.assertEqual(burnup["actual_total"], 0)
```

- [ ] **Step 2: Verify failure**, then **Step 3: Implement:**

```python
def compute_quarter_burnup(
    state: RepositoryState, plan: JsonDict, on_date: date
) -> JsonDict:
    """Planned vs actual cumulative solves for the quarter, plus the two
    steering numbers: projected landing (trailing pace extrapolated) and the
    required weekly rate to still hit the target."""

    progress = state.progress
    quarter = plan["quarter"]
    quarter_start = parse_iso_date(str(quarter["start"]), "plan.quarter.start")
    quarter_end = parse_iso_date(str(quarter["end"]), "plan.quarter.end")
    target = int(quarter.get("target_new_solves", 0))
    upto = min(on_date, quarter_end)

    planned: list[JsonDict] = []
    running = 0
    for week in plan.get("weeks", []):
        week_start, week_end = plan_week_bounds(week)
        running += int(week.get("target_solves", 0))
        planned.append(
            {
                "date": format_iso_date(week_end),
                "start": format_iso_date(week_start),
                "cumulative": running,
                "deload": bool(week.get("deload")),
            }
        )

    daily: dict[str, int] = {}
    for record in completed_records(progress):
        completed_on = _completion_date(record)
        if completed_on is not None and quarter_start <= completed_on <= upto:
            key = format_iso_date(completed_on)
            daily[key] = daily.get(key, 0) + 1
    actual: list[JsonDict] = []
    cumulative = 0
    for day in sorted(daily):
        cumulative += daily[day]
        actual.append({"date": day, "cumulative": cumulative})

    readiness_cfg = state.scoring.get("readiness", {})
    skill_progress = compute_skill_progress(
        state.curriculum, state.skills, state.scoring, progress
    )
    pace = compute_pace(progress, state.skills, skill_progress, readiness_cfg, on_date)
    weeks_remaining = round(max((quarter_end - on_date).days, 0) / 7.0, 2)
    remaining = max(target - cumulative, 0)
    return {
        "start": quarter.get("start"),
        "end": quarter.get("end"),
        "target_total": target,
        "planned": planned,
        "actual": actual,
        "actual_total": cumulative,
        "projected_total": round(
            cumulative + pace["problems_per_week"] * weeks_remaining, 1
        ),
        "required_per_week": (
            round(remaining / weeks_remaining, 2) if weeks_remaining > 0 else None
        ),
        "weeks_remaining": weeks_remaining,
        "mocks_done": len(mock_entries_in_range(progress, quarter_start, upto)),
        "target_mocks": int(quarter.get("target_mocks", 0)),
    }
```

- [ ] **Step 4: Run tests** — PASS. **Step 5: Commit** — `git commit -am "feat/plan: quarter burn-up with projected landing and required pace"`

---

### Task 4: Month milestones (derived, auto-replanning)

**Files:**
- Modify: `scripts/_shared.py`, `scripts/test_plan_feed.py`

**Interfaces:**
- Consumes: `skill_lookup`, `is_meta_skill`, `compute_skill_progress`, `skill_mastery_dates`, `plan_expected_solves`, `solves_in_range`, `state.graph["skill_order"]`, `state.stages`.
- Produces: `compute_month_milestones(state, plan, on_date) -> list[JsonDict]`.

**Mechanism (do not deviate):** A skill is *targeted by milestone M* when its primary problem AND at least one reinforcement problem fall inside `done_before ∪ planned_queue[:expected_solves(M)]`, where `planned_queue` = curriculum-array-order problems not completed before quarter start, truncated to the quarter target. This mirrors how mastery is actually earned (`compute_skill_progress`: primary + reinforcement), so milestones stay honest. Skills mastered before quarter start are excluded. Status: `done` (mastered now) / `missed` (milestone date past, not mastered) / `at_risk` (future milestone but actual solves behind `plan_expected_solves(today)`) / `on_track`. Milestone dates: last day of each calendar month clipped to the quarter end, skipping months with fewer than 14 in-quarter days.

- [ ] **Step 1: Failing tests:**

```python
class MonthMilestoneTests(unittest.TestCase):
    def test_milestone_dates_skip_short_months_and_clip_to_quarter_end(self):
        milestones = compute_month_milestones(
            _state(_progress()), _plan(), date(2026, 7, 28))
        # Fixture quarter 2026-07-27..08-16: July has 5 in-quarter days (skip),
        # August clips to the quarter end.
        self.assertEqual(
            [m["milestone_date"] for m in milestones], ["2026-08-16"])
        self.assertEqual(milestones[0]["month"], "2026-08")
        self.assertEqual(milestones[0]["expected_solves"], 12)

    def test_skills_have_valid_statuses_and_stage_note(self):
        milestones = compute_month_milestones(
            _state(_progress()), _plan(), date(2026, 7, 28))
        skills = milestones[0]["skills"]
        self.assertTrue(skills, "quarter targeting 12 solves must target skills")
        for entry in skills:
            self.assertEqual(
                set(entry), {"skill_id", "name", "stage", "status"})
            self.assertIn(entry["status"], {"done", "on_track", "at_risk", "missed"})
        self.assertIn("Observation", milestones[0]["stage_note"])

    def test_behind_plan_marks_future_skills_at_risk(self):
        # No solves at all, four days in -> behind the expected curve.
        milestones = compute_month_milestones(
            _state(_progress()), _plan(), date(2026, 7, 30))
        statuses = {entry["status"] for entry in milestones[0]["skills"]}
        self.assertIn("at_risk", statuses)
        self.assertNotIn("missed", statuses)

    def test_past_milestone_unmastered_is_missed(self):
        milestones = compute_month_milestones(
            _state(_progress()), _plan(), date(2026, 8, 17))
        self.assertTrue(
            all(entry["status"] in {"done", "missed"}
                for m in milestones for entry in m["skills"]))
```

- [ ] **Step 2: Verify failure**, then **Step 3: Implement:**

```python
def _month_milestone_dates(plan: JsonDict) -> list[date]:
    """Month-end milestone dates inside the quarter. The final month clips to
    the quarter end; months with fewer than 14 in-quarter days are skipped
    (a 5-day tail is not a meaningful milestone)."""

    quarter = plan["quarter"]
    start = parse_iso_date(str(quarter["start"]), "plan.quarter.start")
    end = parse_iso_date(str(quarter["end"]), "plan.quarter.end")
    dates: list[date] = []
    cursor = start.replace(day=1)
    while cursor <= end:
        next_month = (cursor + timedelta(days=32)).replace(day=1)
        milestone = min(next_month - timedelta(days=1), end)
        window_start = max(cursor, start)
        if (milestone - window_start).days + 1 >= 14:
            dates.append(milestone)
        cursor = next_month
    return dates


def _planned_queue(state: RepositoryState, plan: JsonDict) -> tuple[set[str], list[str]]:
    """(problems completed before the quarter, the quarter's planned solve
    queue in curriculum order truncated to the target)."""

    quarter_start = parse_iso_date(str(plan["quarter"]["start"]), "plan.quarter.start")
    target = int(plan["quarter"].get("target_new_solves", 0))
    done_before: set[str] = set()
    for record in completed_records(state.progress):
        completed_on = _completion_date(record)
        problem_id = record.get("problem_id")
        if isinstance(problem_id, str) and completed_on is not None and completed_on < quarter_start:
            done_before.add(problem_id)
    problems = ensure_list(state.curriculum.get("problems"), "curriculum.problems")
    queue = [
        problem["id"]
        for problem in problems
        if isinstance(problem, dict) and "id" in problem and problem["id"] not in done_before
    ]
    return done_before, queue[:target]


def compute_month_milestones(
    state: RepositoryState, plan: JsonDict, on_date: date
) -> list[JsonDict]:
    """Skill targets per month-end, derived from curriculum order + weekly
    solve targets. A skill is targeted once its primary AND one reinforcement
    problem fall inside the planned solve budget (mirrors compute_skill_progress
    mastery mechanics). Statuses re-plan automatically as actuals move."""

    progress = state.progress
    quarter = plan["quarter"]
    quarter_start = parse_iso_date(str(quarter["start"]), "plan.quarter.start")
    quarter_end = parse_iso_date(str(quarter["end"]), "plan.quarter.end")
    done_before, queue = _planned_queue(state, plan)
    skills = skill_lookup(state.skills)
    skill_order = state.graph.get("skill_order") or list(skills)
    skill_progress = compute_skill_progress(
        state.curriculum, state.skills, state.scoring, progress
    )
    mastery_dates = skill_mastery_dates(state.skills, progress, skill_progress)
    reference = min(on_date, quarter_end)
    behind = (
        solves_in_range(progress, quarter_start, reference) + 1e-9
        < plan_expected_solves(plan, reference)
    )
    stage_defs = state.stages.get("stages", {})
    stage_order = state.stages.get("stage_order", [])

    milestones: list[JsonDict] = []
    for milestone_date in _month_milestone_dates(plan):
        expected = int(round(plan_expected_solves(plan, milestone_date)))
        available = done_before | set(queue[:expected])
        skills_out: list[JsonDict] = []
        for skill_id in skill_order:
            skill = skills.get(skill_id)
            if not isinstance(skill, dict) or is_meta_skill(skill):
                continue
            mastered_on = mastery_dates.get(skill_id)
            if mastered_on is not None and mastered_on < quarter_start:
                continue  # banked before the quarter; not a quarter milestone
            primary = skill.get("primary_validation_problem")
            reinforcement = skill.get("reinforcement_problems") or []
            if primary not in available or not any(pid in available for pid in reinforcement):
                continue
            if skill_progress.get(skill_id, {}).get("mastered"):
                status = "done"
            elif milestone_date < on_date:
                status = "missed"
            elif behind:
                status = "at_risk"
            else:
                status = "on_track"
            skills_out.append(
                {
                    "skill_id": skill_id,
                    "name": skill.get("name"),
                    "stage": skill.get("stage"),
                    "status": status,
                }
            )
        counts: dict[str, int] = {}
        for entry in skills_out:
            counts[entry["stage"]] = counts.get(entry["stage"], 0) + 1
        notes = []
        for stage_name in stage_order:
            if stage_name not in counts:
                continue
            stage_skill_ids = [
                sid
                for sid in stage_defs.get(stage_name, {}).get("skills", [])
                if isinstance(skills.get(sid), dict) and not is_meta_skill(skills[sid])
            ]
            notes.append(f"{stage_name} {counts[stage_name]}/{len(stage_skill_ids)}")
        milestones.append(
            {
                "month": format_iso_date(milestone_date)[:7],
                "milestone_date": format_iso_date(milestone_date),
                "expected_solves": expected,
                "actual_solves": solves_in_range(
                    progress, quarter_start, min(milestone_date, on_date)
                ),
                "skills": skills_out,
                "stage_note": " · ".join(notes),
            }
        )
    return milestones
```

- [ ] **Step 4: Run tests** — PASS. **Step 5: Commit** — `git commit -am "feat/plan: derived month milestones with live status"`

---

### Task 5: Promotion ladder + time invested

**Files:**
- Modify: `scripts/_shared.py`, `scripts/test_plan_feed.py`

**Interfaces:**
- Consumes: `recompute_score_summary(progress, curriculum, stages, scoring)`, `compute_skill_progress`, `compute_stage_mastery(stages, skill_progress)`, `latest_records_by_problem`, `problem_lookup`.
- Produces:
  - `promotion_ladder(state) -> JsonDict` — per-stage: live mastery status + quality-bar checks + config thresholds. **Presentation honesty:** stage advancement is skill-mastery driven (`determine_stage`, `_shared.py:866`); `minimum_completed_problems` is the cumulative volume guideline, `minimum_weighted_score` the per-problem quality bar counted in `stage_checks`. The card never claims a count-based promotion gate.
  - `time_invested(state) -> JsonDict`.

- [ ] **Step 1: Failing tests:**

```python
class PromotionLadderTests(unittest.TestCase):
    def test_ladder_shape_and_live_recompute(self):
        progress = _progress([
            _completed("OBS-001", "2026-07-27"),
            _completed("OBS-002", "2026-07-28"),
        ])
        ladder = promotion_ladder(_state(progress))
        self.assertEqual(ladder["total_completed"], 2)
        stage_names = [row["stage"] for row in ladder["stages"]]
        self.assertEqual(stage_names[0], "Observation")
        self.assertEqual(len(stage_names), 13)
        first = ladder["stages"][0]
        self.assertEqual(
            set(first),
            {"stage", "status", "skills_mastered", "skills_total",
             "attempted", "passed", "minimum_weighted_score",
             "minimum_completed_problems"})
        self.assertEqual(first["attempted"], 2)  # both fixtures are Observation-stage
        self.assertEqual(ladder["stages"][1]["status"], "locked")

    def test_thresholds_come_from_scoring(self):
        ladder = promotion_ladder(_state(_progress()))
        scoring = load_json_file(_shared.SCORING_PATH)
        expected = scoring["promotion_thresholds"]["Observation"]["minimum_completed_problems"]
        self.assertEqual(
            ladder["stages"][0]["minimum_completed_problems"], expected)


class TimeInvestedTests(unittest.TestCase):
    def test_totals_and_difficulty_buckets(self):
        progress = _progress([
            _completed("OBS-001", "2026-07-27", minutes=30),
            _completed("OBS-002", "2026-07-28", minutes=60),
        ])
        result = time_invested(_state(progress))
        self.assertEqual(result["total_minutes"], 90)
        self.assertEqual(result["sessions"], 2)
        self.assertEqual(result["average_minutes"], 45.0)
        self.assertEqual(result["series"][0]["date"], "2026-07-27")
        self.assertTrue(all("difficulty" in e for e in result["series"]))
        self.assertTrue(result["by_difficulty"])

    def test_records_without_minutes_are_skipped(self):
        record = _completed("OBS-001", "2026-07-27")
        del record["time_taken_minutes"]
        result = time_invested(_state(_progress([record])))
        self.assertEqual(result["sessions"], 0)
        self.assertEqual(result["total_minutes"], 0)
```

- [ ] **Step 2: Verify failure**, then **Step 3: Implement:**

```python
def promotion_ladder(state: RepositoryState) -> JsonDict:
    """Per-stage promotion picture: live mastery status, quality-bar checks
    (stage_checks), and the scoring.json thresholds. Stage advancement itself
    is skill-mastery driven (determine_stage); the thresholds are the quality
    bar and cumulative volume guideline, surfaced together for the ladder card."""

    progress = state.progress
    skill_progress = compute_skill_progress(
        state.curriculum, state.skills, state.scoring, progress
    )
    stage_mastery = compute_stage_mastery(state.stages, skill_progress)
    checks = recompute_score_summary(
        progress, state.curriculum, state.stages, state.scoring
    )["stage_checks"]
    thresholds = state.scoring.get("promotion_thresholds", {})
    stage_order = ensure_list(state.stages.get("stage_order"), "stages.stage_order")

    stages_out: list[JsonDict] = []
    for stage_name in stage_order:
        threshold = thresholds.get(stage_name, {})
        mastery = stage_mastery.get(stage_name, {})
        check = checks.get(stage_name, {})
        stages_out.append(
            {
                "stage": stage_name,
                "status": mastery.get("status", "locked"),
                "skills_mastered": mastery.get("skills_mastered", 0),
                "skills_total": mastery.get("skills_total", 0),
                "attempted": check.get("attempted", 0),
                "passed": check.get("passed", 0),
                "minimum_weighted_score": (
                    threshold.get("minimum_weighted_score")
                    if isinstance(threshold, dict) else None
                ),
                "minimum_completed_problems": (
                    threshold.get("minimum_completed_problems")
                    if isinstance(threshold, dict) else None
                ),
            }
        )
    return {
        "current_stage": determine_stage(progress, state.stages, state.scoring, state.skills),
        "total_completed": len(latest_records_by_problem(progress)),
        "stages": stages_out,
    }


def time_invested(state: RepositoryState) -> JsonDict:
    """Session-time analytics from time_taken_minutes (recorded on every solve
    but previously surfaced only in the problem modal)."""

    problems = problem_lookup(state.curriculum)
    series: list[JsonDict] = []
    for record in completed_records(state.progress):
        completed_on = _completion_date(record)
        minutes = record.get("time_taken_minutes")
        if completed_on is None or not isinstance(minutes, (int, float)):
            continue
        series.append(
            {
                "date": format_iso_date(completed_on),
                "problem_id": record.get("problem_id"),
                "minutes": minutes,
                "difficulty": problems.get(record.get("problem_id"), {}).get("difficulty"),
            }
        )
    series.sort(key=lambda entry: entry["date"])
    total = sum(entry["minutes"] for entry in series)
    buckets: dict[str, dict[str, float]] = {}
    for entry in series:
        bucket = buckets.setdefault(
            entry["difficulty"] or "Unknown", {"count": 0, "total": 0}
        )
        bucket["count"] += 1
        bucket["total"] += entry["minutes"]
    difficulty_rank = {"Easy": 0, "Medium": 1, "Hard": 2}
    by_difficulty = sorted(
        (
            {
                "difficulty": name,
                "count": int(bucket["count"]),
                "average_minutes": round(bucket["total"] / bucket["count"], 1),
            }
            for name, bucket in buckets.items()
        ),
        key=lambda entry: difficulty_rank.get(entry["difficulty"], 9),
    )
    return {
        "total_minutes": total,
        "sessions": len(series),
        "average_minutes": round(total / len(series), 1) if series else 0.0,
        "by_difficulty": by_difficulty,
        "series": series,
    }
```

- [ ] **Step 4: Run tests** — PASS. **Step 5: Commit** — `git commit -am "feat/plan: promotion ladder and time-invested analytics"`

---

### Task 6: Wire into the feed

**Files:**
- Modify: `scripts/_shared.py` (`build_dashboard_feed`, insert immediately before `return feed` at `_shared.py:2362`)
- Modify: `scripts/test_plan_feed.py`

**Interfaces:**
- Produces: `build_plan_feed(state, on_date, plan=None) -> JsonDict | None`; feed keys `plan`, `promotion`, `time_invested`.

- [ ] **Step 1: Failing tests:**

```python
class FeedIntegrationTests(unittest.TestCase):
    def test_feed_carries_plan_promotion_and_time(self):
        feed = build_dashboard_feed(_state(_progress()), date(2026, 7, 28))
        self.assertIn("plan", feed)
        self.assertIn("promotion", feed)
        self.assertIn("time_invested", feed)
        # live plan.json exists (Feature 01), so plan is a dict with a quarter
        self.assertIsInstance(feed["plan"], dict)
        self.assertIn("quarter", feed["plan"])
        self.assertIn("today_contract", feed["plan"])

    def test_feed_still_json_serializable(self):
        import json as _json
        _json.dumps(build_dashboard_feed(_state(_progress()), date(2026, 7, 28)))

    def test_broken_plan_never_breaks_the_feed(self):
        from unittest import mock
        with mock.patch.object(
            _shared, "load_plan",
            side_effect=RepositoryError("plan.json: boom"),
        ):
            feed = build_dashboard_feed(_state(_progress()), date(2026, 7, 28))
        self.assertEqual(feed["plan"], {"error": "plan.json: boom"})
        self.assertIn("next_action", feed)  # rest of the feed intact

    def test_build_plan_feed_accepts_injected_plan(self):
        block = build_plan_feed(_state(_progress()), date(2026, 7, 28), plan=_plan())
        self.assertEqual(block["quarter"]["target_new_solves"], 12)
        self.assertEqual(block["week"]["week"], 1)
        self.assertEqual(len(block["weeks"]), 1)
        self.assertIsInstance(block["months"], list)

    def test_no_plan_file_yields_null_block(self):
        from unittest import mock
        with mock.patch.object(_shared, "load_plan", return_value=None):
            feed = build_dashboard_feed(_state(_progress()), date(2026, 7, 28))
        self.assertIsNone(feed["plan"])
```

- [ ] **Step 2: Verify failure**, then **Step 3: Implement.** Append to `_shared.py`:

```python
def build_plan_feed(
    state: RepositoryState, on_date: date, plan: JsonDict | None = None
) -> JsonDict | None:
    """Assemble the feed's `plan` block. None when no plan.json exists."""

    if plan is None:
        plan = load_plan()
    if plan is None:
        return None
    quarter = plan["quarter"]
    return {
        "quarter": {
            "label": quarter.get("label"),
            "start": quarter.get("start"),
            "end": quarter.get("end"),
            "target_new_solves": int(quarter.get("target_new_solves", 0)),
            "target_mocks": int(quarter.get("target_mocks", 0)),
            "daily_review_capacity": int(quarter.get("daily_review_capacity", 0)),
        },
        "today_contract": compute_today_contract(state, plan, on_date),
        "week": compute_week_scoreboard(state, plan, on_date),
        "weeks": compute_week_history(state, plan, on_date),
        "burnup": compute_quarter_burnup(state, plan, on_date),
        "months": compute_month_milestones(state, plan, on_date),
    }
```

In `build_dashboard_feed`, replace the bare `return feed` (end of function, `_shared.py:2362`) with:

```python
    # Plan layer (plans/plan_layer/): a broken plan.json degrades to an error
    # chip on the Plan workspace — it must never 500 the whole feed.
    try:
        feed["plan"] = build_plan_feed(state, on_date)
    except RepositoryError as exc:
        feed["plan"] = {"error": str(exc)}
    feed["promotion"] = promotion_ladder(state)
    feed["time_invested"] = time_invested(state)
    return feed
```

(`build_plan_feed` is defined later in the file than `build_dashboard_feed`; Python resolves names at call time, matching the existing file layout.)

- [ ] **Step 4: Run the full suite**

Run: `make test`
Expected: all green — especially `test_dashboard_feed.py` (its `REQUIRED_KEYS` check uses set intersection, so the added keys are compatible; if anything there fails, you broke an existing feed path — stop and fix).

- [ ] **Step 5: Live smoke**

Run: `python3 -c "from datetime import date; import sys; sys.path.insert(0,'scripts'); from _shared import load_repository_state, build_dashboard_feed; import json; f=build_dashboard_feed(load_repository_state(), date.today()); print(json.dumps({'plan_ok': f['plan'] is not None and 'error' not in (f['plan'] or {}), 'promo_stages': len(f['promotion']['stages']), 'time_sessions': f['time_invested']['sessions']}))"`
Expected: `{"plan_ok": true, "promo_stages": 13, "time_sessions": <n>}`

- [ ] **Step 6: Commit** — `git commit -am "feat/plan: ship plan, promotion and time blocks on the feed"`
