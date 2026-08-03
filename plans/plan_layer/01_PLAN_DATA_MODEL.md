# Feature 01 — Plan Data Model (`progress/plan.json`)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Read `00_OVERVIEW.md` §Global constraints and §PRECONDITION first.

**Goal:** The quarter plan becomes machine-readable data with a validated loader in `_shared.py`.

**Architecture:** One JSON file, one loader (`load_plan`), one validator (`validate_plan`) raising `RepositoryError` with precise messages. Weeks are Monday-anchored 7-day blocks; deload weeks carry `target_solves: 0`; the sum of week targets must equal the quarter target so the plan can never silently disagree with itself.

**Tech Stack:** Python 3 stdlib, `unittest`.

## Global constraints

- Stdlib only; no xlsx parsing (`study_plan_months_1-3.xlsx` stays a human reference).
- New test file `scripts/test_plan_feed.py` registered in `Makefile` `test` target.
- 2-space-indent JSON with trailing newline (match `save_json_file`, `_shared.py:190`).
- Commit style `feat/plan: ...` / `test/plan: ...`; no Co-Authored-By.

---

### Task 1: Author `progress/plan.json`

**Files:**
- Create: `progress/plan.json`

**Interfaces:**
- Produces: the live plan consumed by `load_plan()` (Task 2) and every computation in `02_FEED_PLAN_BLOCK.md`.

Week math (verified): W1 starts Monday 2026-07-27; W13 = start + 84d = 2026-10-19, ending 2026-10-25 = quarter end. Deloads W4/W8/W12 (xlsx "Rules & Notes"). 10 non-deload weeks × 6 = 60 = quarter target. Mocks: one per weekend incl. deload weeks (xlsx: deload = "Revisions + one mock + Java only"); quarter `target_mocks` stays 10 (the "~10" contract).

- [ ] **Step 1: Write the file** with exactly this content:

```json
{
  "schema_version": 1,
  "quarter": {
    "label": "2026 Q3 — months 1-3",
    "start": "2026-07-27",
    "end": "2026-10-25",
    "target_new_solves": 60,
    "target_mocks": 10,
    "daily_review_capacity": 4
  },
  "weeks": [
    { "week": 1,  "start": "2026-07-27", "deload": false, "target_solves": 6, "mock": true },
    { "week": 2,  "start": "2026-08-03", "deload": false, "target_solves": 6, "mock": true },
    { "week": 3,  "start": "2026-08-10", "deload": false, "target_solves": 6, "mock": true },
    { "week": 4,  "start": "2026-08-17", "deload": true,  "target_solves": 0, "mock": true },
    { "week": 5,  "start": "2026-08-24", "deload": false, "target_solves": 6, "mock": true },
    { "week": 6,  "start": "2026-08-31", "deload": false, "target_solves": 6, "mock": true },
    { "week": 7,  "start": "2026-09-07", "deload": false, "target_solves": 6, "mock": true },
    { "week": 8,  "start": "2026-09-14", "deload": true,  "target_solves": 0, "mock": true },
    { "week": 9,  "start": "2026-09-21", "deload": false, "target_solves": 6, "mock": true },
    { "week": 10, "start": "2026-09-28", "deload": false, "target_solves": 6, "mock": true },
    { "week": 11, "start": "2026-10-05", "deload": false, "target_solves": 6, "mock": true },
    { "week": 12, "start": "2026-10-12", "deload": true,  "target_solves": 0, "mock": true },
    { "week": 13, "start": "2026-10-19", "deload": false, "target_solves": 6, "mock": true }
  ],
  "notes": [
    "The scheduler (make next) is the authority; the plan is the pace contract.",
    "Deload weeks W4/W8/W12: no new solves; revisions + one mock only.",
    "Missed morning solve = skipped; the queue absorbs it. Never move it to the evening."
  ]
}
```

- [ ] **Step 2: Sanity-check by hand**

Run: `python3 -c "import json; p=json.load(open('progress/plan.json')); print(sum(w['target_solves'] for w in p['weeks']))"`
Expected: `60`

- [ ] **Step 3: Commit**

```bash
git add progress/plan.json
git commit -m "feat/plan: quarter plan as data (13 weeks, 60 solves, deloads W4/W8/W12)"
```

---

### Task 2: `load_plan` + `validate_plan` in `_shared.py`

**Files:**
- Modify: `scripts/_shared.py` (append constants near `PROGRESS_TEMPLATE_PATH`, `_shared.py:24`; append functions at end of file)
- Create: `scripts/test_plan_feed.py`
- Modify: `Makefile` (`test` target)

**Interfaces:**
- Consumes: `ROOT`, `RepositoryError`, `parse_iso_date` — all existing.
- Produces:
  - `PLAN_PATH: Path` — `ROOT / "progress" / "plan.json"`.
  - `load_plan(path: Path | None = None) -> JsonDict | None` — `None` when the file is absent; raises `RepositoryError` on unreadable JSON or failed validation.
  - `validate_plan(plan: JsonDict) -> None` — raises `RepositoryError` with a message naming the failing field.
  - `plan_week_for(plan: JsonDict, on_date: date) -> JsonDict | None` — the week dict containing `on_date`, else `None`.
  - `plan_week_bounds(week: JsonDict) -> tuple[date, date]` — (start, start+6d).

- [ ] **Step 1: Write the failing tests** — create `scripts/test_plan_feed.py`:

```python
#!/usr/bin/env python3
"""Tests for the plan layer: plan.json loading and plan-vs-actual feed block."""
from __future__ import annotations

import unittest
from datetime import date

import _shared
from _shared import RepositoryError, load_plan, plan_week_for, validate_plan


def _plan():
    """A minimal 3-week fixture plan (week 2 is a deload)."""
    return {
        "schema_version": 1,
        "quarter": {
            "label": "test quarter",
            "start": "2026-07-27",
            "end": "2026-08-16",
            "target_new_solves": 12,
            "target_mocks": 2,
            "daily_review_capacity": 4,
        },
        "weeks": [
            {"week": 1, "start": "2026-07-27", "deload": False, "target_solves": 6, "mock": True},
            {"week": 2, "start": "2026-08-03", "deload": True, "target_solves": 0, "mock": True},
            {"week": 3, "start": "2026-08-10", "deload": False, "target_solves": 6, "mock": True},
        ],
        "notes": [],
    }


class PlanValidationTests(unittest.TestCase):
    def test_valid_plan_passes(self):
        validate_plan(_plan())  # must not raise

    def test_live_plan_json_is_valid(self):
        plan = load_plan()
        self.assertIsNotNone(plan, "progress/plan.json must exist and validate")
        self.assertEqual(plan["quarter"]["target_new_solves"], 60)

    def test_missing_file_returns_none(self):
        self.assertIsNone(load_plan(_shared.ROOT / "progress" / "no_such_plan.json"))

    def test_week_targets_must_sum_to_quarter_target(self):
        plan = _plan()
        plan["weeks"][0]["target_solves"] = 5
        with self.assertRaises(RepositoryError) as ctx:
            validate_plan(plan)
        self.assertIn("target_new_solves", str(ctx.exception))

    def test_weeks_must_be_contiguous_seven_day_blocks(self):
        plan = _plan()
        plan["weeks"][1]["start"] = "2026-08-04"
        with self.assertRaises(RepositoryError):
            validate_plan(plan)

    def test_deload_week_must_target_zero_solves(self):
        plan = _plan()
        plan["weeks"][1]["target_solves"] = 3
        with self.assertRaises(RepositoryError):
            validate_plan(plan)

    def test_quarter_end_must_close_the_last_week(self):
        plan = _plan()
        plan["quarter"]["end"] = "2026-08-15"
        with self.assertRaises(RepositoryError):
            validate_plan(plan)

    def test_week_numbers_must_be_sequential_from_one(self):
        plan = _plan()
        plan["weeks"][2]["week"] = 4
        with self.assertRaises(RepositoryError):
            validate_plan(plan)


class PlanWeekForTests(unittest.TestCase):
    def test_returns_containing_week(self):
        week = plan_week_for(_plan(), date(2026, 8, 5))
        self.assertEqual(week["week"], 2)

    def test_boundaries_inclusive(self):
        self.assertEqual(plan_week_for(_plan(), date(2026, 7, 27))["week"], 1)
        self.assertEqual(plan_week_for(_plan(), date(2026, 8, 16))["week"], 3)

    def test_outside_quarter_returns_none(self):
        self.assertIsNone(plan_week_for(_plan(), date(2026, 8, 17)))
        self.assertIsNone(plan_week_for(_plan(), date(2026, 7, 26)))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 scripts/test_plan_feed.py`
Expected: `ImportError: cannot import name 'load_plan'`

- [ ] **Step 3: Implement.** In `scripts/_shared.py`, add below `PROGRESS_TEMPLATE_PATH = ...` (line 24):

```python
PLAN_PATH = ROOT / "progress" / "plan.json"
```

Append at the end of the file (after `build_dashboard_feed`):

```python
# ---------------------------------------------------------------------------
# Plan layer: progress/plan.json is the machine-readable quarter plan (weekly
# solve targets, deload weeks, mock cadence). The scheduler stays the
# authority on WHAT to do; the plan is the pace contract the dashboard tracks
# against. Design: plans/plan_layer/00_OVERVIEW.md.
# ---------------------------------------------------------------------------


def validate_plan(plan: JsonDict) -> None:
    """Validate a plan payload; raise RepositoryError naming the broken field."""

    if not isinstance(plan, dict):
        raise RepositoryError("plan.json: payload must be an object.")
    quarter = plan.get("quarter")
    if not isinstance(quarter, dict):
        raise RepositoryError("plan.json: `quarter` must be an object.")
    start = parse_iso_date(str(quarter.get("start")), "plan.quarter.start")
    end = parse_iso_date(str(quarter.get("end")), "plan.quarter.end")
    if end <= start:
        raise RepositoryError("plan.json: `quarter.end` must be after `quarter.start`.")
    try:
        target_total = int(quarter.get("target_new_solves"))
    except (TypeError, ValueError):
        raise RepositoryError("plan.json: `quarter.target_new_solves` must be an integer.")

    weeks = plan.get("weeks")
    if not isinstance(weeks, list) or not weeks:
        raise RepositoryError("plan.json: `weeks` must be a non-empty list.")
    total = 0
    for index, week in enumerate(weeks):
        if not isinstance(week, dict):
            raise RepositoryError(f"plan.json: weeks[{index}] must be an object.")
        if week.get("week") != index + 1:
            raise RepositoryError(
                f"plan.json: weeks[{index}].week must be {index + 1} (sequential from 1)."
            )
        week_start = parse_iso_date(str(week.get("start")), f"plan.weeks[{index}].start")
        if week_start != start + timedelta(days=7 * index):
            raise RepositoryError(
                f"plan.json: weeks[{index}].start must be quarter.start + {7 * index} days "
                "(contiguous 7-day blocks)."
            )
        try:
            week_target = int(week.get("target_solves"))
        except (TypeError, ValueError):
            raise RepositoryError(f"plan.json: weeks[{index}].target_solves must be an integer.")
        if week.get("deload") and week_target != 0:
            raise RepositoryError(
                f"plan.json: weeks[{index}] is a deload week and must target 0 solves."
            )
        total += week_target
    last_start = parse_iso_date(str(weeks[-1]["start"]), "plan.weeks.start")
    if end != last_start + timedelta(days=6):
        raise RepositoryError(
            "plan.json: `quarter.end` must be the last day (start + 6) of the final week."
        )
    if total != target_total:
        raise RepositoryError(
            f"plan.json: week targets sum to {total}, but `quarter.target_new_solves` "
            f"is {target_total}."
        )


def load_plan(path: Path | None = None) -> JsonDict | None:
    """Load and validate progress/plan.json. None when absent (plan layer off);
    RepositoryError on unreadable or invalid content."""

    plan_path = path or PLAN_PATH
    if not plan_path.exists():
        return None
    plan = load_json_file(plan_path)
    validate_plan(plan)
    return plan


def plan_week_bounds(week: JsonDict) -> tuple[date, date]:
    """Return the inclusive (start, end) dates of a plan week."""

    start = parse_iso_date(str(week.get("start")), "plan.weeks.start")
    return start, start + timedelta(days=6)


def plan_week_for(plan: JsonDict, on_date: date) -> JsonDict | None:
    """Return the plan week containing `on_date`, or None outside the quarter."""

    for week in plan.get("weeks", []):
        start, end = plan_week_bounds(week)
        if start <= on_date <= end:
            return week
    return None
```

- [ ] **Step 4: Run the tests**

Run: `python3 scripts/test_plan_feed.py`
Expected: all PASS (note: `test_live_plan_json_is_valid` requires Task 1's file — run after it).

- [ ] **Step 5: Register the suite.** In `Makefile`, inside the `test:` target, add after the `test_dashboard_feed.py` line:

```make
	$(PYTHON) scripts/test_plan_feed.py
```

- [ ] **Step 6: Full suite**

Run: `make test`
Expected: every suite green, including the pre-existing ones (proves no accidental edits to existing code paths).

- [ ] **Step 7: Commit**

```bash
git add scripts/_shared.py scripts/test_plan_feed.py Makefile
git commit -m "feat/plan: load and validate the quarter plan"
```
