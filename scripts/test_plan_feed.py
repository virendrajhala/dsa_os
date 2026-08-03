#!/usr/bin/env python3
"""Tests for the plan layer: plan.json loading and plan-vs-actual feed block."""
from __future__ import annotations

import unittest
from datetime import date

import _shared
from _shared import (
    RepositoryError,
    RepositoryState,
    build_dashboard_feed,
    build_plan_feed,
    compute_month_milestones,
    compute_quarter_burnup,
    compute_today_contract,
    compute_week_history,
    compute_week_scoreboard,
    load_json_file,
    load_plan,
    mock_entries_in_range,
    plan_expected_solves,
    plan_week_for,
    promotion_ladder,
    revision_events_in_range,
    solves_in_range,
    time_invested,
    validate_plan,
)


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
        self.assertAlmostEqual(
            plan_expected_solves(plan, date(2026, 7, 29)), 6 * 3 / 7, places=4)
        self.assertAlmostEqual(plan_expected_solves(plan, date(2026, 8, 9)), 6.0, places=4)
        self.assertAlmostEqual(plan_expected_solves(plan, date(2026, 8, 16)), 12.0, places=4)


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
        self.assertTrue(contract["mock"]["planned"])

    def test_deload_week_plans_no_solve_but_keeps_mock(self):
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
        progress = _progress([_completed("OBS-001", "2026-07-27")])
        rows = compute_week_history(_state(progress), _plan(), date(2026, 8, 5))
        self.assertEqual([row["week"] for row in rows], [1, 2])
        self.assertEqual(rows[0]["actual_solves"], 1)


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


class MonthMilestoneTests(unittest.TestCase):
    def test_milestone_dates_skip_short_months_and_clip_to_quarter_end(self):
        milestones = compute_month_milestones(
            _state(_progress()), _plan(), date(2026, 7, 28))
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
        self.assertEqual(first["attempted"], 2)
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


class FeedIntegrationTests(unittest.TestCase):
    def test_feed_carries_plan_promotion_and_time(self):
        feed = build_dashboard_feed(_state(_progress()), date(2026, 7, 28))
        self.assertIn("plan", feed)
        self.assertIn("promotion", feed)
        self.assertIn("time_invested", feed)
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
        self.assertIn("next_action", feed)

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


class UnlockedProblemsTests(unittest.TestCase):
    def test_unlocked_excludes_completed_and_locked(self):
        progress = _progress([_completed("OBS-001", "2026-07-09")])
        feed = build_dashboard_feed(_state(progress), date(2026, 7, 28))
        unlocked = feed["unlocked_problems"]
        self.assertIsInstance(unlocked, list)
        self.assertNotIn("OBS-001", unlocked)
        self.assertTrue(unlocked, "something must be workable")
        self.assertNotIn("DP-050", unlocked)

    def test_unlocked_matches_scheduler_helper(self):
        from _shared import (
            challenge_stage_gate, completed_problem_ids, is_problem_unlocked,
            problem_dependencies_map, problem_lookup,
        )
        progress = _progress([_completed("OBS-001", "2026-07-09")])
        state = _state(progress)
        feed = build_dashboard_feed(state, date(2026, 7, 28))
        completed = completed_problem_ids(progress)
        deps = problem_dependencies_map(state.graph)
        gate = challenge_stage_gate(state.curriculum)
        for problem_id, problem in problem_lookup(state.curriculum).items():
            expected = problem_id not in completed and is_problem_unlocked(
                problem, completed, deps, gate)
            self.assertEqual(problem_id in set(feed["unlocked_problems"]), expected,
                             f"{problem_id} disagrees with is_problem_unlocked")


class InterviewFrequencyTests(unittest.TestCase):
    @staticmethod
    def _zip(files):
        import io
        import zipfile
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for path, content in files.items():
                archive.writestr(path, content)
        return buffer.getvalue()

    def test_slug_from_url(self):
        from fetch_interview_frequency import slug_from_url
        self.assertEqual(
            slug_from_url("https://leetcode.com/problems/two-sum/"), "two-sum")
        self.assertEqual(
            slug_from_url("https://leetcode.com/problems/two-sum/description/"), "two-sum")
        self.assertIsNone(slug_from_url("https://leetcode.com/explore/"))
        self.assertIsNone(slug_from_url(None))

    def test_parse_prefers_all_window_and_takes_max(self):
        from fetch_interview_frequency import parse_dataset_zip
        header = "Difficulty,Title,Frequency,Link\n"
        payload = self._zip({
            "repo-main/Google/1. Thirty Days.csv":
                header + "Easy,Two Sum,99.0,https://leetcode.com/problems/two-sum/\n",
            "repo-main/Google/5. All.csv":
                header + "Easy,Two Sum,61.5,https://leetcode.com/problems/two-sum/\n"
                + "Hard,Word Ladder,10.0,https://leetcode.com/problems/word-ladder/\n",
            "repo-main/Amazon/5. All.csv":
                header + "Easy,Two Sum,80.0,https://leetcode.com/problems/two-sum/\n",
        })
        parsed = parse_dataset_zip(payload)
        self.assertEqual(parsed["two-sum"]["Google"], 61.5)
        self.assertEqual(parsed["two-sum"]["Amazon"], 80.0)
        self.assertEqual(parsed["word-ladder"], {"Google": 10.0})

    def test_aggregate_and_tiers(self):
        from fetch_interview_frequency import aggregate, assign_tiers
        per_company = {
            f"slug-{index}": {f"c{c}": 1.0 for c in range(count)}
            for index, count in enumerate([50, 40, 30, 20, 10, 8, 6, 4, 2, 1])
        }
        aggregated = aggregate(per_company)
        self.assertEqual(aggregated["slug-0"]["companies"], 50)
        assign_tiers(aggregated)
        tiers = [aggregated[f"slug-{index}"]["tier"] for index in range(10)]
        self.assertEqual(tiers, ["very_high", "high", "high",
                                 "medium", "medium", "medium",
                                 "low", "low", "low", "low"])

    def test_top_companies_sorted_by_frequency(self):
        from fetch_interview_frequency import aggregate
        aggregated = aggregate({"two-sum": {"A": 1.0, "B": 9.0, "C": 5.0}})
        self.assertEqual(aggregated["two-sum"]["top_companies"][:2], ["B", "C"])


if __name__ == "__main__":
    unittest.main()
