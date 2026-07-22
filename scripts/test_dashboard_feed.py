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
