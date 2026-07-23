#!/usr/bin/env python3
"""Tests for build_dashboard_feed (dashboard = pure view of _shared)."""
from __future__ import annotations

import unittest
from datetime import date

import _shared
from _shared import (
    RepositoryState, build_dashboard_feed, load_json_file, select_next_problem,
)


def _state(progress, threshold=None):
    # Pin the recall-backlog threshold when a test asserts ordering policy, so
    # retuning the live scoring.json cannot break these assertions.
    scoring = load_json_file(_shared.SCORING_PATH)
    if threshold is not None:
        import json as _j
        scoring = _j.loads(_j.dumps(scoring))
        scoring["revision_policy"]["revision_backlog_threshold"] = threshold
    return RepositoryState(
        curriculum=load_json_file(_shared.CURRICULUM_PATH),
        graph=load_json_file(_shared.GRAPH_PATH),
        stages=load_json_file(_shared.STAGES_PATH),
        skills=load_json_file(_shared.SKILLS_PATH),
        patterns=load_json_file(_shared.PATTERNS_PATH),
        scoring=scoring,
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

    def test_overdue_backlog_wins_even_on_weekend(self):
        # A weekend must never hide recall once the backlog passes
        # revision_policy.revision_backlog_threshold. Under it, the weekend
        # mock proceeds instead — the feed must agree with the CLI either way.
        progress = _base_progress()
        for index, problem_id in enumerate(["OBS-001", "OBS-002", "OBS-003", "CPX-001"]):
            progress["completed"][index] = _completed(problem_id, next_due="2026-07-01")
        progress["completed"].append(_completed("OBS-004", next_due="2026-07-01"))
        progress["mastered_skills"] = ["SK-OB-01"]
        state = _state(progress)
        on = date(2026, 7, 25)
        feed = build_dashboard_feed(state, on)
        selection = select_next_problem(state, on_date=on)
        self.assertEqual(feed["next_action"]["mode"], selection.mode)
        self.assertEqual(feed["next_action"]["mode"], "revision")
        # Which of the equally-overdue items wins is the scheduler's call; the
        # feed must simply agree with it.
        self.assertEqual(feed["next_action"]["problem_id"], selection.problem["id"])

    def test_small_backlog_lets_the_weekend_mock_through(self):
        progress = _base_progress()
        progress["completed"][0] = _completed("OBS-001", next_due="2026-07-01")
        progress["mastered_skills"] = ["SK-OB-01"]
        state = _state(progress, threshold=4)
        on = date(2026, 7, 25)
        feed = build_dashboard_feed(state, on)
        selection = select_next_problem(state, on_date=on)
        self.assertEqual(feed["next_action"]["mode"], selection.mode)
        self.assertNotEqual(feed["next_action"]["mode"], "revision")


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


class FeedEndpointTests(unittest.TestCase):
    """serve_dashboard.py must expose the feed at GET /api/feed."""

    @staticmethod
    def _free_port():
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    def test_api_feed_endpoint_and_static_still_served(self):
        import json as _json
        import subprocess
        import sys
        import time
        import urllib.error
        import urllib.request

        port = self._free_port()
        proc = subprocess.Popen(
            [sys.executable, str(_shared.ROOT / "scripts" / "serve_dashboard.py"),
             "--host", "127.0.0.1", "--port", str(port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            base = f"http://127.0.0.1:{port}"
            feed = None
            deadline = time.time() + 10
            while time.time() < deadline:
                try:
                    with urllib.request.urlopen(f"{base}/api/feed", timeout=2) as resp:
                        self.assertEqual(resp.status, 200)
                        feed = _json.loads(resp.read().decode("utf-8"))
                    break
                except (urllib.error.URLError, ConnectionError):
                    time.sleep(0.15)
            self.assertIsNotNone(feed, "server did not answer /api/feed in time")
            self.assertIn("next_action", feed)
            with urllib.request.urlopen(
                f"{base}/web_dashboard/index.html", timeout=2
            ) as resp:
                self.assertEqual(resp.status, 200)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


class ForecastMaintenanceTests(unittest.TestCase):
    """The day-0 bar must not undercount the queue printed above it."""

    def _mastered_due_for_maintenance(self, problem_id, last_pass):
        record = _completed(problem_id, status="MASTERED", stage=5)
        record["revision"]["completed"] = [last_pass]
        record["revision"]["next_due"] = None
        return record

    def test_day_zero_includes_quarterly_maintenance_due_now(self):
        progress = _base_progress()
        # Passed R4 long enough ago that 90-day maintenance has come due.
        progress["completed"][0] = self._mastered_due_for_maintenance(
            "OBS-001", "2026-01-01"
        )
        on = date(2026, 7, 22)
        feed = build_dashboard_feed(_state(progress), on)
        maintenance = [
            item["problem_id"] for item in feed["revision_queue"]
            if item["kind"] == "quarterly_maintenance"
        ]
        self.assertTrue(maintenance, "fixture did not produce maintenance work")
        day_zero = feed["review_forecast"][0]
        for problem_id in maintenance:
            self.assertIn(problem_id, day_zero["problem_ids"])
        # Every queue row due today or earlier is represented in day 0.
        due_now = [
            item["problem_id"] for item in feed["revision_queue"]
            if item["next_due"] <= "2026-07-22"
        ]
        self.assertEqual(sorted(set(due_now)), sorted(set(day_zero["problem_ids"])))
        self.assertEqual(day_zero["count"], len(day_zero["problem_ids"]))

    def test_forecast_never_double_counts_a_problem_on_day_zero(self):
        progress = _base_progress()
        progress["completed"][0] = self._mastered_due_for_maintenance(
            "OBS-001", "2026-01-01"
        )
        progress["completed"][1] = _completed("OBS-002", next_due="2026-07-01")
        feed = build_dashboard_feed(_state(progress), date(2026, 7, 22))
        ids = feed["review_forecast"][0]["problem_ids"]
        self.assertEqual(len(ids), len(set(ids)))


class SolutionPresenceTests(unittest.TestCase):
    """The modal may only link a solution file the repo actually has."""

    def test_solutions_present_lists_only_real_files(self):
        feed = build_dashboard_feed(_state(_base_progress()), date(2026, 7, 22))
        present = feed["solutions_present"]
        self.assertIsInstance(present, list)
        for problem_id in present:
            self.assertTrue((_shared.ROOT / "solutions" / f"{problem_id}.py").exists())

    def test_solutions_present_excludes_non_problem_files(self):
        feed = build_dashboard_feed(_state(_base_progress()), date(2026, 7, 22))
        # solutions/ ships _example.py and README.md; neither is a problem id.
        self.assertNotIn("_example", feed["solutions_present"])
        self.assertNotIn("README", feed["solutions_present"])


if __name__ == "__main__":
    unittest.main()
