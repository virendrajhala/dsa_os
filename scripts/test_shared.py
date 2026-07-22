#!/usr/bin/env python3
"""Regression tests for scripts/_shared.py (stdlib unittest, no deps).

Run: python3 scripts/test_shared.py
"""

from __future__ import annotations

import unittest
from datetime import date, timedelta

import _shared
from _shared import (
    RepositoryState,
    apply_revision_result,
    compute_core_mastery_status,
    compute_pace,
    compute_readiness,
    compute_recent_mock_status,
    compute_revision_pass_rate,
    compute_skill_progress,
    core_skill_ids_in_scope,
    format_iso_date,
    is_mock_due,
    load_json_file,
    project_readiness_date,
    resolve_revision_policy,
    revision_intervals,
    revision_stage_label,
    select_mock_problem,
    select_next_problem,
    skill_mastery_dates,
    weekend_window,
)


def _record(problem_id: str = "TEST-001", completed_at: str = "2026-01-01") -> dict:
    return {"problem_id": problem_id, "completed_at": completed_at}


def _completion(problem_id: str, hint_level_used: int | None, thinking_score: dict | None) -> dict:
    record = {"problem_id": problem_id, "completed_at": "2026-01-01"}
    if hint_level_used is not None:
        record["hint_level_used"] = hint_level_used
    if thinking_score is not None:
        record["thinking_score"] = thinking_score
    return record


_SCORING = {
    "scale": {"minimum": 0, "maximum": 4},
    "weights": {"understanding": 0.5, "algorithm_design": 0.5},
    "skill_mastery": {"minimum_primary_weighted_score": 2.6, "require_reinforcement_attempt": True},
    "hint_mastery_discount": {"0": 1, "1": 1, "2": 1, "3": 0.5, "4": 0.5, "5": 0, "6": 0, "7": 0},
}

_SKILLS = {
    "skills": {
        "SK-TEST": {
            "scope": "stage",
            "primary_validation_problem": "PRIMARY-001",
            "reinforcement_problems": ["REINFORCE-001"],
        }
    }
}


def _progress(*completions: dict) -> dict:
    return {"completed": list(completions)}


class ComputeSkillProgressHintDiscountTests(unittest.TestCase):
    """F6: hint_level_used scales the mastery bar for a primary solve.

    Margin-scaled effective bar (not score discounting): weight 1.0 leaves
    the 2.6 bar unchanged (hint 0-2); weight 0.5 raises it to 3.3, halfway
    to the scale max of 4.0 (hint 3-4), so a strong hint-3/4 solve can still
    master while a mediocre one can't; weight 0 (hint 5+) makes mastery
    impossible regardless of score.
    """

    FULL_SCORE = {"understanding": 4, "algorithm_design": 4}  # weighted 4.0
    MID_SCORE = {"understanding": 3, "algorithm_design": 3}  # weighted 3.0

    def test_hint_6_primary_solve_never_masters_even_at_max_score(self):
        progress = _progress(
            _completion("PRIMARY-001", hint_level_used=6, thinking_score=self.FULL_SCORE),
            _completion("REINFORCE-001", hint_level_used=0, thinking_score=self.FULL_SCORE),
        )
        result = compute_skill_progress({}, _SKILLS, _SCORING, progress)
        self.assertFalse(result["SK-TEST"]["mastered"])

    def test_hint_3_primary_solve_at_raw_4_masters_against_scaled_bar(self):
        # weight 0.5 -> effective bar 2.6 + (4.0 - 2.6) * 0.5 = 3.3; raw 4.0 clears it.
        progress = _progress(
            _completion("PRIMARY-001", hint_level_used=3, thinking_score=self.FULL_SCORE),
            _completion("REINFORCE-001", hint_level_used=0, thinking_score=self.FULL_SCORE),
        )
        result = compute_skill_progress({}, _SKILLS, _SCORING, progress)
        # primary_weighted_score stays the raw score - discount applies only
        # to the mastery comparison, not to the stored/displayed value.
        self.assertEqual(result["SK-TEST"]["primary_weighted_score"], 4.0)
        self.assertTrue(result["SK-TEST"]["mastered"])

    def test_hint_3_primary_solve_at_raw_3_fails_scaled_bar(self):
        # effective bar 3.3; raw 3.0 falls short.
        progress = _progress(
            _completion("PRIMARY-001", hint_level_used=3, thinking_score=self.MID_SCORE),
            _completion("REINFORCE-001", hint_level_used=0, thinking_score=self.FULL_SCORE),
        )
        result = compute_skill_progress({}, _SKILLS, _SCORING, progress)
        self.assertEqual(result["SK-TEST"]["primary_weighted_score"], 3.0)
        self.assertFalse(result["SK-TEST"]["mastered"])

    def test_hint_2_primary_solve_keeps_bar_at_2_6(self):
        # weight 1.0 -> effective bar unchanged at 2.6; raw 3.0 clears it.
        progress = _progress(
            _completion("PRIMARY-001", hint_level_used=2, thinking_score=self.MID_SCORE),
            _completion("REINFORCE-001", hint_level_used=0, thinking_score=self.FULL_SCORE),
        )
        result = compute_skill_progress({}, _SKILLS, _SCORING, progress)
        self.assertEqual(result["SK-TEST"]["primary_weighted_score"], 3.0)
        self.assertTrue(result["SK-TEST"]["mastered"])

    def test_hint_0_primary_solve_counts_at_full_weight_and_masters(self):
        progress = _progress(
            _completion("PRIMARY-001", hint_level_used=0, thinking_score=self.FULL_SCORE),
            _completion("REINFORCE-001", hint_level_used=0, thinking_score=self.FULL_SCORE),
        )
        result = compute_skill_progress({}, _SKILLS, _SCORING, progress)
        self.assertEqual(result["SK-TEST"]["primary_weighted_score"], 4.0)
        self.assertTrue(result["SK-TEST"]["mastered"])

    def test_no_numeric_thinking_score_does_not_pass_the_bar(self):
        progress = _progress(
            _completion("PRIMARY-001", hint_level_used=0, thinking_score=None),
            _completion("REINFORCE-001", hint_level_used=0, thinking_score=self.FULL_SCORE),
        )
        result = compute_skill_progress({}, _SKILLS, _SCORING, progress)
        self.assertFalse(result["SK-TEST"]["mastered"])


class ApplyRevisionResultTests(unittest.TestCase):
    """F1: PASS at R4 must master, not crash on a missing R5 interval."""

    def test_pass_x4_from_stage_0_masters_without_keyerror(self):
        record = _record()
        today = date(2026, 1, 1)

        # PASS #1: stage 0 -> 1 (R1 cleared)
        event = apply_revision_result(record, "PASS", today, confidence=8, hint_level=0, revision_score={})
        self.assertEqual(event["attempted_stage"], 1)
        self.assertEqual(record["revision"]["stage"], 1)
        self.assertEqual(record["revision"]["status"], "ACTIVE")

        # PASS #2: stage 1 -> 2 (R2 cleared)
        event = apply_revision_result(record, "PASS", today, confidence=8, hint_level=0, revision_score={})
        self.assertEqual(event["attempted_stage"], 2)
        self.assertEqual(record["revision"]["stage"], 2)
        self.assertEqual(record["revision"]["status"], "ACTIVE")

        # PASS #3: stage 2 -> 3 (R3 cleared)
        event = apply_revision_result(record, "PASS", today, confidence=8, hint_level=0, revision_score={})
        self.assertEqual(event["attempted_stage"], 3)
        self.assertEqual(record["revision"]["stage"], 3)
        self.assertEqual(record["revision"]["status"], "ACTIVE")

        # PASS #4: stage 3 -> 4 (R4 cleared) must MASTER, not raise KeyError.
        event = apply_revision_result(record, "PASS", today, confidence=8, hint_level=0, revision_score={})
        self.assertEqual(event["attempted_stage"], 4)
        self.assertEqual(record["revision"]["stage"], 4)
        self.assertEqual(record["revision"]["status"], "MASTERED")
        self.assertIsNone(record["revision"]["next_due"])
        self.assertEqual(record["revision"]["last_maintenance"], "2026-01-01")

    def test_pass_at_stage_3_masters_using_real_record_shape(self):
        # Mirrors the brief's manual verification: a record already advanced
        # to R4 (stage 3) that then PASSes must master, not KeyError.
        record = _record()
        record["revision"] = {
            "status": "ACTIVE",
            "stage": 3,
            "completed": ["2026-01-01", "2026-01-08", "2026-01-29"],
            "next_due": "2026-03-30",
            "history": [],
        }
        event = apply_revision_result(
            record, "PASS", date(2026, 3, 30), confidence=8, hint_level=0, revision_score={}
        )
        self.assertEqual(event["attempted_stage"], 4)
        self.assertEqual(record["revision"]["status"], "MASTERED")
        self.assertEqual(record["revision"]["stage"], 4)
        self.assertIsNone(record["revision"]["next_due"])

    def test_fail_path_retries_same_stage_next_day(self):
        record = _record()
        record["revision"] = {
            "status": "ACTIVE",
            "stage": 1,
            "completed": ["2026-01-01"],
            "next_due": "2026-01-08",
            "history": [],
        }
        event = apply_revision_result(
            record, "FAIL", date(2026, 1, 8), confidence=3, hint_level=2, revision_score={}
        )
        self.assertEqual(event["result"], "FAIL")
        self.assertEqual(record["revision"]["status"], "FAILED")
        # Stage does not advance on FAIL.
        self.assertEqual(record["revision"]["stage"], 1)
        # Retried the next day.
        self.assertEqual(record["revision"]["next_due"], "2026-01-09")


class RevisionStageLabelTests(unittest.TestCase):
    """F1: labels are capped at R4 + MASTERED; no phantom R5."""

    def test_labels_r1_through_r4(self):
        self.assertEqual(revision_stage_label(0), "R1")
        self.assertEqual(revision_stage_label(1), "R2")
        self.assertEqual(revision_stage_label(2), "R3")
        self.assertEqual(revision_stage_label(3), "R4")

    def test_stage_4_and_beyond_is_mastered_not_r5(self):
        self.assertEqual(revision_stage_label(4), "MASTERED")
        self.assertEqual(revision_stage_label(5), "MASTERED")
        self.assertNotIn("R5", {revision_stage_label(s) for s in range(0, 6)})


class MockDueSchedulingTests(unittest.TestCase):
    """F10: weekend mock scheduling. The date is injected via `on_date` /
    `is_mock_due(..., on_date)` — never by monkeypatching datetime globally.

    Reference dates: 2026-07-25 is a Saturday, 2026-07-26 a Sunday,
    2026-07-22 a Wednesday.
    """

    SATURDAY = date(2026, 7, 25)
    SUNDAY = date(2026, 7, 26)
    WEDNESDAY = date(2026, 7, 22)

    def test_weekend_window(self):
        self.assertEqual(weekend_window(self.SATURDAY), (self.SATURDAY, self.SUNDAY))
        self.assertEqual(weekend_window(self.SUNDAY), (self.SATURDAY, self.SUNDAY))
        self.assertIsNone(weekend_window(self.WEDNESDAY))

    def test_is_mock_due_weekend_without_mock(self):
        self.assertTrue(is_mock_due({}, self.SATURDAY))
        self.assertTrue(is_mock_due({}, self.SUNDAY))

    def test_is_mock_due_false_on_weekday(self):
        self.assertFalse(is_mock_due({}, self.WEDNESDAY))

    def test_is_mock_due_false_when_mock_already_in_window(self):
        # A Saturday mock covers the whole Sat-Sun window.
        progress = {"mock_interviews": [{"date": "2026-07-25"}]}
        self.assertFalse(is_mock_due(progress, self.SATURDAY))
        self.assertFalse(is_mock_due(progress, self.SUNDAY))

    def test_is_mock_due_true_when_mock_is_previous_weekend(self):
        progress = {"mock_interviews": [{"date": "2026-07-18"}]}
        self.assertTrue(is_mock_due(progress, self.SATURDAY))


class MockSelectionOrderingTests(unittest.TestCase):
    """F10: a due mock outranks new work but never an overdue revision, and
    the selected problem comes from a mastered/adjacent skill, never the
    current in-progress skill or an already-completed problem."""

    SATURDAY = date(2026, 7, 25)
    WEDNESDAY = date(2026, 7, 22)
    MASTERED = ["SK-OB-01", "SK-OB-03", "SK-OB-04"]

    def _state(self, progress):
        return RepositoryState(
            curriculum=load_json_file(_shared.CURRICULUM_PATH),
            graph=load_json_file(_shared.GRAPH_PATH),
            stages=load_json_file(_shared.STAGES_PATH),
            skills=load_json_file(_shared.SKILLS_PATH),
            patterns={},
            scoring=load_json_file(_shared.SCORING_PATH),
            progress=progress,
            progress_path=_shared.PROGRESS_PATH,
        )

    @staticmethod
    def _completed(problem_id, next_due="2099-01-01"):
        return {
            "problem_id": problem_id,
            "completed_at": "2026-01-01",
            "revision": {
                "status": "ACTIVE",
                "stage": 1,
                "completed": ["2026-01-01"],
                "next_due": next_due,
                "history": [],
            },
        }

    def _base_progress(self):
        solved = ["OBS-001", "OBS-002", "OBS-003", "OBS-004", "OBS-005",
                  "OBS-006", "OBS-007", "OBS-008", "CPX-001", "CPX-002"]
        return {
            "completed": [self._completed(p) for p in solved],
            "mastered_skills": list(self.MASTERED),
            "current_problem": None,
            "current_stage": "Observation",
        }

    def test_mock_due_outranks_new_work_on_weekend(self):
        selection = select_next_problem(self._state(self._base_progress()), on_date=self.SATURDAY)
        self.assertEqual(selection.mode, "mock_due")
        problem = selection.problem
        self.assertIsNotNone(problem)
        # Drawn from a mastered/adjacent (Observation-stage) skill, unseen.
        self.assertTrue(problem["primary_skill"].startswith("SK-OB-"))
        solved_ids = {c["problem_id"] for c in self._base_progress()["completed"]}
        self.assertNotIn(problem["id"], solved_ids)

    def test_weekday_does_not_trigger_mock(self):
        selection = select_next_problem(self._state(self._base_progress()), on_date=self.WEDNESDAY)
        self.assertNotEqual(selection.mode, "mock_due")

    def test_existing_weekend_mock_suppresses_mock_due(self):
        progress = self._base_progress()
        progress["mock_interviews"] = [{"date": "2026-07-25"}]
        selection = select_next_problem(self._state(progress), on_date=self.SATURDAY)
        self.assertNotEqual(selection.mode, "mock_due")

    def test_overdue_revision_outranks_mock(self):
        progress = self._base_progress()
        progress["completed"][0] = self._completed("OBS-001", next_due="2026-07-01")
        selection = select_next_problem(self._state(progress), on_date=self.SATURDAY)
        self.assertEqual(selection.mode, "revision")

    def test_mock_never_serves_revisit_of_completed_problem(self):
        # TWO-001 is `revisit_of` CPX-001 (Two Sum); with CPX-001 completed and
        # SK-CM-01 mastered, TWO-001 is the top-ordered candidate — but it is
        # literally a seen problem, so mock selection must skip it (rule 5).
        progress = {
            "completed": [self._completed("CPX-001")],
            "mastered_skills": ["SK-CM-01"],
            "current_problem": None,
            "current_stage": "Observation",
        }
        problem, kind = select_mock_problem(self._state(progress))
        self.assertEqual(kind, "mock")
        self.assertIsNotNone(problem)
        self.assertNotEqual(problem["id"], "TWO-001")
        self.assertNotIn(problem.get("revisit_of"), {"CPX-001"})

    def test_practice_mock_when_no_skill_mastered(self):
        progress = {
            "completed": [self._completed("OBS-001")],
            "mastered_skills": [],
            "current_problem": None,
            "current_stage": "Observation",
        }
        selection = select_next_problem(self._state(progress), on_date=self.SATURDAY)
        self.assertEqual(selection.mode, "mock_due")
        self.assertIn("practice", selection.reason)


class RevisionPolicyConfigTests(unittest.TestCase):
    """Revision policy numbers must flow from scoring.json `revision_policy`,
    not from a second hardcoded table in Python."""

    def test_resolve_defaults_when_config_absent(self):
        policy = resolve_revision_policy(None)
        self.assertEqual(
            policy["successful_recall_intervals"], {"R1": 3, "R2": 7, "R3": 21, "R4": 60}
        )
        self.assertEqual(policy["mastered_after_stage"], 4)
        self.assertEqual(policy["failure_retry_days"], 1)

    def test_resolve_overlays_config_values(self):
        policy = resolve_revision_policy(
            {"revision_policy": {"failure_retry_days": 2, "quarterly_maintenance_days": 45}}
        )
        self.assertEqual(policy["failure_retry_days"], 2)
        self.assertEqual(policy["quarterly_maintenance_days"], 45)
        # Untouched keys keep their defaults.
        self.assertEqual(policy["successful_recall_intervals"]["R3"], 21)

    def test_revision_intervals_maps_stage_indexes(self):
        policy = resolve_revision_policy(
            {"revision_policy": {"successful_recall_intervals": {"R1": 1, "R2": 2, "R3": 4, "R4": 8}}}
        )
        self.assertEqual(revision_intervals(policy), {0: 1, 1: 2, 2: 4, 3: 8})

    def test_apply_revision_result_honors_injected_policy(self):
        policy = resolve_revision_policy(
            {
                "revision_policy": {
                    "successful_recall_intervals": {"R1": 1, "R2": 2, "R3": 4, "R4": 8},
                    "failure_retry_days": 3,
                }
            }
        )
        record = _record()
        on = date(2026, 1, 10)

        # PASS clears R1; next due follows the custom R2 interval (2 days).
        apply_revision_result(
            record, "PASS", on, confidence=8, hint_level=0, revision_score={}, policy=policy
        )
        self.assertEqual(record["revision"]["next_due"], "2026-01-12")

        # FAIL retries after the custom failure_retry_days (3 days).
        apply_revision_result(
            record, "FAIL", on, confidence=5, hint_level=3, revision_score={}, policy=policy
        )
        self.assertEqual(record["revision"]["next_due"], "2026-01-13")

    def test_maintenance_fail_demotion_follows_policy(self):
        # Demotion after a failed quarterly check must land one stage below
        # mastery (and truncate completed accordingly), not hardcoded 3.
        policy = resolve_revision_policy(
            {
                "revision_policy": {
                    "successful_recall_intervals": {"R1": 1, "R2": 2, "R3": 4, "R4": 8, "R5": 16},
                    "mastered_after_stage": 5,
                }
            }
        )
        record = _record()
        record["revision"] = {
            "status": "MASTERED",
            "stage": 6,
            "completed": ["2026-01-01", "2026-01-02", "2026-01-04", "2026-01-08", "2026-01-16"],
            "next_due": None,
            "history": [],
        }
        apply_revision_result(
            record, "FAIL", date(2026, 4, 1), confidence=4, hint_level=4, revision_score={}, policy=policy
        )
        self.assertEqual(record["revision"]["status"], "ACTIVE")
        self.assertEqual(record["revision"]["stage"], 4)
        self.assertEqual(len(record["revision"]["completed"]), 4)

    def test_scoring_read_tolerates_non_utf8_file(self):
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
            handle.write(b"\xff\xfe\x00garbage")
            path = Path(handle.name)
        try:
            self.assertIsNone(_shared._scoring_payload_for_policy(path))
        finally:
            path.unlink()

    def test_module_constants_mirror_live_scoring_json(self):
        block = load_json_file(_shared.SCORING_PATH)["revision_policy"]
        self.assertEqual(
            _shared.REVISION_INTERVAL_DAYS,
            {i: block["successful_recall_intervals"][f"R{i + 1}"] for i in range(4)},
        )
        self.assertEqual(_shared.MASTERED_AFTER_STAGE, block["mastered_after_stage"])
        self.assertEqual(_shared.FAILURE_RETRY_DAYS, block["failure_retry_days"])
        self.assertEqual(_shared.QUARTERLY_MAINTENANCE_DAYS, block["quarterly_maintenance_days"])
        self.assertEqual(
            _shared.QUARTERLY_MAINTENANCE_LIMIT, block["quarterly_maintenance_sample_size"]
        )


class ReadinessTests(unittest.TestCase):
    """F23: system-derived interview-readiness estimator (pure functions)."""

    STAGES = {
        "stage_order": ["Stage1", "Stage2", "Stage3"],
        "stages": {
            "Stage1": {"skills": ["SK-A", "SK-B"]},
            "Stage2": {"skills": ["SK-C"]},
            "Stage3": {"skills": ["SK-D"]},
        },
    }
    CURRICULUM = {
        "problems": [
            {"id": "P-A1", "primary_skill": "SK-A", "importance": "CORE"},
            # SK-B is in scope but has no CORE problem -> excluded.
            {"id": "P-B1", "primary_skill": "SK-B", "importance": "COMMON"},
            {"id": "P-C1", "primary_skill": "SK-C", "importance": "CORE"},
            # SK-D's stage (Stage3) is outside the first-2-stage scope -> excluded.
            {"id": "P-D1", "primary_skill": "SK-D", "importance": "CORE"},
        ]
    }
    SKILLS = {
        "skills": {
            "SK-A": {"stage": "Stage1", "primary_validation_problem": "P-A1", "reinforcement_problems": ["P-A2"]},
            "SK-B": {"stage": "Stage1", "primary_validation_problem": "P-B1", "reinforcement_problems": ["P-B2"]},
            "SK-C": {"stage": "Stage2", "primary_validation_problem": "P-C1", "reinforcement_problems": ["P-C2"]},
            "SK-D": {"stage": "Stage3", "primary_validation_problem": "P-D1", "reinforcement_problems": ["P-D2"]},
        }
    }
    READINESS_CFG = {
        "core_skill_fraction": 0.8,
        "stage_scope_count": 2,
        "revision_pass_rate": 0.9,
        "recent_mock_count": 3,
        "min_mock_verdicts": ["hire", "strong-hire"],
        "pace_window_days": 28,
    }

    def test_core_skill_ids_in_scope_filters_by_stage_and_core_importance(self):
        ids = core_skill_ids_in_scope(self.CURRICULUM, self.STAGES, self.SKILLS, self.READINESS_CFG)
        self.assertEqual(ids, {"SK-A", "SK-C"})

    def test_core_mastery_status_fraction(self):
        skill_progress = {"SK-A": {"mastered": True}, "SK-C": {"mastered": False}}
        status = compute_core_mastery_status(skill_progress, {"SK-A", "SK-C"})
        self.assertEqual(status, {"mastered": 1, "total": 2, "fraction": 0.5})

    def test_core_mastery_status_empty_scope(self):
        status = compute_core_mastery_status({}, set())
        self.assertEqual(status, {"mastered": 0, "total": 0, "fraction": 0.0})

    def test_revision_pass_rate_excludes_reactivated_events(self):
        progress = {
            "completed": [
                {
                    "revision": {
                        "history": [
                            {"result": "PASS"},
                            {"result": "PASS"},
                            {"result": "FAIL"},
                            {"result": "REACTIVATED"},
                        ]
                    }
                }
            ]
        }
        status = compute_revision_pass_rate(progress)
        self.assertEqual(status["pass"], 2)
        self.assertEqual(status["total"], 3)
        self.assertAlmostEqual(status["fraction"], 2 / 3, places=4)

    def test_revision_pass_rate_no_events_is_zero(self):
        status = compute_revision_pass_rate({"completed": []})
        self.assertEqual(status, {"pass": 0, "total": 0, "fraction": 0.0})

    def test_recent_mock_status_no_mocks_is_unmet(self):
        status = compute_recent_mock_status({}, self.READINESS_CFG)
        self.assertFalse(status["met"])
        self.assertEqual(status["recorded"], 0)
        self.assertEqual(status["required"], 3)

    def test_recent_mock_status_three_hire_mocks_is_met(self):
        progress = {
            "mock_interviews": [
                {"date": "2026-06-01", "verdict": "hire"},
                {"date": "2026-06-08", "verdict": "strong-hire"},
                {"date": "2026-06-15", "verdict": "hire"},
            ]
        }
        status = compute_recent_mock_status(progress, self.READINESS_CFG)
        self.assertTrue(status["met"])
        self.assertEqual(status["recorded"], 3)

    def test_recent_mock_status_recent_no_hire_is_unmet(self):
        progress = {
            "mock_interviews": [
                {"date": "2026-06-01", "verdict": "hire"},
                {"date": "2026-06-08", "verdict": "hire"},
                {"date": "2026-06-15", "verdict": "no-hire"},
            ]
        }
        status = compute_recent_mock_status(progress, self.READINESS_CFG)
        self.assertFalse(status["met"])

    def test_skill_mastery_dates_uses_max_of_primary_and_earliest_reinforcement(self):
        progress = {
            "completed": [
                {"problem_id": "P-A1", "completed_at": "2026-07-01"},
                {"problem_id": "P-A2", "completed_at": "2026-07-05"},
            ]
        }
        skill_progress = {"SK-A": {"mastered": True}}
        dates = skill_mastery_dates(self.SKILLS, progress, skill_progress)
        self.assertEqual(dates["SK-A"], date(2026, 7, 5))

    def test_skill_mastery_dates_none_when_reinforcement_missing(self):
        progress = {"completed": [{"problem_id": "P-A1", "completed_at": "2026-07-01"}]}
        skill_progress = {"SK-A": {"mastered": True}}
        dates = skill_mastery_dates(self.SKILLS, progress, skill_progress)
        self.assertIsNone(dates["SK-A"])

    def test_compute_pace_counts_problems_and_skills_in_window(self):
        on_date = date(2026, 7, 21)
        progress = {
            "completed": [
                {"problem_id": "PX1", "completed_at": "2026-07-01"},
                {"problem_id": "PX2", "completed_at": "2026-07-05"},  # SK-X mastery date, in window
                {"problem_id": "PY1", "completed_at": "2026-05-01"},
                {"problem_id": "PY2", "completed_at": "2026-05-10"},  # SK-Y mastery date, out of window
                {"problem_id": "OTHER-1", "completed_at": "2026-07-10"},
            ]
        }
        skills = {
            "skills": {
                "SK-X": {"primary_validation_problem": "PX1", "reinforcement_problems": ["PX2"]},
                "SK-Y": {"primary_validation_problem": "PY1", "reinforcement_problems": ["PY2"]},
            }
        }
        skill_progress = {"SK-X": {"mastered": True}, "SK-Y": {"mastered": True}}
        pace = compute_pace(progress, skills, skill_progress, self.READINESS_CFG, on_date)
        self.assertEqual(pace["window_days"], 28)
        # 3 completions fall within [2026-06-24, 2026-07-21]: PX1, PX2, OTHER-1.
        self.assertEqual(pace["problems_in_window"], 3)
        self.assertEqual(pace["skills_mastered_in_window"], 1)
        self.assertAlmostEqual(pace["problems_per_week"], 3 / 4, places=4)
        self.assertAlmostEqual(pace["skills_mastered_per_week"], 1 / 4, places=4)

    def test_project_readiness_date_core_mastery_already_met(self):
        result = project_readiness_date(0, 0.5, date(2026, 7, 21))
        self.assertEqual(result["status"], "core_mastery_met")

    def test_project_readiness_date_no_pace_is_unprojected(self):
        result = project_readiness_date(3, 0.0, date(2026, 7, 21))
        self.assertEqual(result["status"], "no_pace")
        self.assertIn("no projection yet", result["message"])

    def test_project_readiness_date_linear_extrapolation(self):
        on_date = date(2026, 7, 21)
        result = project_readiness_date(2, 0.25, on_date)
        self.assertEqual(result["status"], "projected")
        expected = on_date + timedelta(days=56)
        self.assertEqual(result["date"], expected.isoformat())
        self.assertIn(expected.isoformat(), result["message"])

    def test_compute_readiness_no_mocks_is_unmet(self):
        curriculum = {"problems": [{"id": "P-A1", "primary_skill": "SK-A", "importance": "CORE"}]}
        stages = {"stage_order": ["Stage1"], "stages": {"Stage1": {"skills": ["SK-A"]}}}
        skills = {
            "skills": {
                "SK-A": {
                    "stage": "Stage1",
                    "primary_validation_problem": "P-A1",
                    "reinforcement_problems": ["P-A2"],
                }
            }
        }
        scoring = dict(_SCORING)
        scoring["readiness"] = {
            "core_skill_fraction": 0.8,
            "stage_scope_count": 1,
            "revision_pass_rate": 0.9,
            "recent_mock_count": 3,
            "min_mock_verdicts": ["hire", "strong-hire"],
            "pace_window_days": 28,
        }
        progress = {"completed": []}
        result = compute_readiness(curriculum, stages, skills, scoring, progress, date(2026, 7, 21))
        self.assertFalse(result["thresholds"]["recent_mocks"]["met"])
        self.assertFalse(result["all_met"])

    def _build_core_scope(self, total_skills: int, mastered_count: int, on_date: date):
        """Build a curriculum/stages/skills/progress with `total_skills` CORE
        skills in scope, of which the first `mastered_count` are mastered
        (primary + reinforcement both completed on `on_date`)."""

        skill_ids = [f"SK-{i:03d}" for i in range(1, total_skills + 1)]
        curriculum = {
            "problems": [
                {"id": f"P-{i:03d}", "primary_skill": sid, "importance": "CORE"}
                for i, sid in enumerate(skill_ids, start=1)
            ]
        }
        stages = {"stage_order": ["Stage1"], "stages": {"Stage1": {"skills": skill_ids}}}
        skills = {
            "skills": {
                sid: {
                    "stage": "Stage1",
                    "primary_validation_problem": f"P-{i:03d}",
                    "reinforcement_problems": [f"P-{i:03d}-R"],
                }
                for i, sid in enumerate(skill_ids, start=1)
            }
        }
        completions = []
        for i in range(1, mastered_count + 1):
            completions.append(
                _completion(f"P-{i:03d}", hint_level_used=0, thinking_score={"understanding": 4, "algorithm_design": 4})
            )
            completions.append(_record(f"P-{i:03d}-R", completed_at=format_iso_date(on_date)))
        progress = {"completed": completions}
        return curriculum, stages, skills, progress

    def test_compute_readiness_remaining_is_target_relative_not_total(self):
        """F23 regression: remaining must be against ceil(target * total), not
        against 100% mastery. Live-data shape: total 55, mastered 1, fraction
        0.8 -> needed 44 -> remaining 43 (not 54)."""

        on_date = date(2026, 7, 21)
        curriculum, stages, skills, progress = self._build_core_scope(55, 1, on_date)
        scoring = dict(_SCORING)
        scoring["readiness"] = {
            "core_skill_fraction": 0.8,
            "stage_scope_count": 1,
            "revision_pass_rate": 0.9,
            "recent_mock_count": 3,
            "min_mock_verdicts": ["hire", "strong-hire"],
            "pace_window_days": 28,
        }
        result = compute_readiness(curriculum, stages, skills, scoring, progress, on_date)
        core = result["thresholds"]["core_skill_mastery"]
        self.assertEqual(core["mastered"], 1)
        self.assertEqual(core["total"], 55)
        self.assertFalse(core["met"])

        # Single mastered skill lands inside the 28-day pace window ->
        # skills_mastered_per_week = 1 / 4 = 0.25.
        self.assertAlmostEqual(result["pace"]["skills_mastered_per_week"], 0.25, places=4)
        expected_remaining = 43  # ceil(0.8 * 55) - 1, NOT 55 - 1 = 54.
        expected_weeks = expected_remaining / 0.25
        expected_date = on_date + timedelta(days=round(expected_weeks * 7))
        self.assertEqual(result["projection"]["status"], "projected")
        self.assertEqual(result["projection"]["date"], expected_date.isoformat())

    def test_compute_readiness_remaining_zero_at_threshold_not_at_full_mastery(self):
        """44/55 (exactly the 0.8 threshold) must report remaining 0 and no
        future projection - core_met True must not coexist with a projected
        future date."""

        on_date = date(2026, 7, 21)
        curriculum, stages, skills, progress = self._build_core_scope(55, 44, on_date)
        scoring = dict(_SCORING)
        scoring["readiness"] = {
            "core_skill_fraction": 0.8,
            "stage_scope_count": 1,
            "revision_pass_rate": 0.9,
            "recent_mock_count": 3,
            "min_mock_verdicts": ["hire", "strong-hire"],
            "pace_window_days": 28,
        }
        result = compute_readiness(curriculum, stages, skills, scoring, progress, on_date)
        core = result["thresholds"]["core_skill_mastery"]
        self.assertEqual(core["mastered"], 44)
        self.assertEqual(core["total"], 55)
        self.assertTrue(core["met"])
        self.assertEqual(result["projection"]["status"], "core_mastery_met")
        self.assertNotIn("date", result["projection"])

    def test_compute_readiness_all_met(self):
        curriculum = {"problems": [{"id": "P-A1", "primary_skill": "SK-A", "importance": "CORE"}]}
        stages = {"stage_order": ["Stage1"], "stages": {"Stage1": {"skills": ["SK-A"]}}}
        skills = {
            "skills": {
                "SK-A": {
                    "stage": "Stage1",
                    "primary_validation_problem": "P-A1",
                    "reinforcement_problems": ["P-A2"],
                }
            }
        }
        scoring = {
            "scale": {"minimum": 0, "maximum": 4},
            "weights": {"understanding": 0.5, "algorithm_design": 0.5},
            "skill_mastery": {"minimum_primary_weighted_score": 2.6, "require_reinforcement_attempt": True},
            "hint_mastery_discount": {"0": 1, "1": 1, "2": 1, "3": 0.5, "4": 0.5, "5": 0, "6": 0, "7": 0},
            "readiness": {
                "core_skill_fraction": 0.8,
                "stage_scope_count": 1,
                "revision_pass_rate": 0.9,
                "recent_mock_count": 3,
                "min_mock_verdicts": ["hire", "strong-hire"],
                "pace_window_days": 28,
            },
        }
        progress = {
            "completed": [
                _completion("P-A1", hint_level_used=0, thinking_score={"understanding": 4, "algorithm_design": 4}),
                {
                    "problem_id": "P-A2",
                    "completed_at": "2026-01-01",
                    "revision": {"history": [{"result": "PASS"}, {"result": "PASS"}, {"result": "PASS"}]},
                },
            ],
            "mock_interviews": [
                {"date": "2026-06-01", "verdict": "hire"},
                {"date": "2026-06-08", "verdict": "strong-hire"},
                {"date": "2026-06-15", "verdict": "hire"},
            ],
        }
        result = compute_readiness(curriculum, stages, skills, scoring, progress, date(2026, 7, 21))
        self.assertTrue(result["thresholds"]["core_skill_mastery"]["met"])
        self.assertTrue(result["thresholds"]["revision_pass_rate"]["met"])
        self.assertTrue(result["thresholds"]["recent_mocks"]["met"])
        self.assertTrue(result["all_met"])


class StageMasteryMetaSkillTests(unittest.TestCase):
    """F18: a problemless meta-skill registered under a stage (SK-IE-00) must
    not count toward that stage's mastery totals."""

    def test_meta_skill_excluded_from_stage_totals(self):
        stages = {
            "stage_order": ["Only"],
            "stages": {"Only": {"skills": ["SK-A", "SK-B", "SK-META"]}},
        }
        # SK-META is not tracked in skill_progress (like SK-IE-00).
        skill_progress = {
            "SK-A": {"mastered": True},
            "SK-B": {"mastered": True},
        }
        result = _shared.compute_stage_mastery(stages, skill_progress)
        self.assertEqual(result["Only"]["skills_total"], 2)
        self.assertEqual(result["Only"]["skills_mastered"], 2)
        self.assertEqual(result["Only"]["status"], "mastered")


class ImplementationEngineeringAverageTests(unittest.TestCase):
    """F22: implementation_engineering.score is a running average over
    completions, recomputed in the normalize path (not last-write-wins)."""

    STAGES = {"stage_order": ["Stage1"], "stages": {"Stage1": {"skills": ["SK-TEST"]}}}

    def _state(self, payload):
        from pathlib import Path

        return RepositoryState(
            curriculum={"problems": [{"id": "PRIMARY-001", "primary_skill": "SK-TEST"}]},
            graph={},
            stages=self.STAGES,
            skills=_SKILLS,
            patterns={},
            scoring=_SCORING,
            progress=payload,
            progress_path=Path("test"),
        )

    def test_normalize_sets_running_average_over_completions(self):
        payload = {
            "completed": [
                {"problem_id": "PRIMARY-001", "completed_at": "2026-01-01", "implementation_engineering_score": 8},
                {"problem_id": "PRIMARY-001", "completed_at": "2026-01-02", "implementation_engineering_score": 9},
            ],
            "implementation_engineering": {"score": 3, "strengths": [], "weaknesses": [], "common_errors": [], "improvement_notes": []},
        }
        _shared.normalize_progress(self._state(payload), payload)
        self.assertEqual(payload["implementation_engineering"]["score"], 8.5)

    def test_normalize_keeps_zero_score_with_no_completions(self):
        payload = {
            "completed": [],
            "implementation_engineering": {"score": 7, "strengths": [], "weaknesses": [], "common_errors": [], "improvement_notes": []},
        }
        _shared.normalize_progress(self._state(payload), payload)
        self.assertEqual(payload["implementation_engineering"]["score"], 0)


class MigrateAlgorithmWeightsTests(unittest.TestCase):
    """F22: migrate's algorithm_thinking_score backfill weights come from
    scoring.json's `algorithm_thinking.weights`, not a hardcoded table."""

    @staticmethod
    def _payload():
        return {
            "completed": [
                {
                    "problem_id": "P-1",
                    "completed_at": "2026-01-01",
                    "thinking_score": {
                        "understanding": 4,
                        "examples": 4,
                        "brute_force": 4,
                        "pattern_detection": 4,
                        "algorithm_design": 4,
                        "complexity_analysis": 4,
                    },
                    "revision": {"status": "ACTIVE", "stage": 0, "completed": [], "next_due": "2026-01-04", "history": []},
                }
            ]
        }

    def test_backfill_uses_scoring_algorithm_thinking_weights(self):
        payload = self._payload()
        scoring = {"algorithm_thinking": {"weights": {"understanding": 1.0}}}
        _shared.migrate_progress_payload(payload, scoring=scoring)
        self.assertEqual(payload["completed"][0]["algorithm_thinking_score"], 10.0)

    def test_backfill_default_weights_without_scoring_block(self):
        payload = self._payload()
        _shared.migrate_progress_payload(payload, scoring={})
        # All-4 thinking scores at any normalized weight table -> 4 * 2.5 = 10.
        self.assertEqual(payload["completed"][0]["algorithm_thinking_score"], 10.0)


class QuarterlyMaintenanceSelectionTests(unittest.TestCase):
    """F22: pin the quarterly-maintenance selection path and its mode name
    (the old fallback string "revision_due" was not a real kind name)."""

    def _state(self, progress):
        return RepositoryState(
            curriculum=load_json_file(_shared.CURRICULUM_PATH),
            graph=load_json_file(_shared.GRAPH_PATH),
            stages=load_json_file(_shared.STAGES_PATH),
            skills=load_json_file(_shared.SKILLS_PATH),
            patterns={},
            scoring=load_json_file(_shared.SCORING_PATH),
            progress=progress,
            progress_path=_shared.PROGRESS_PATH,
        )

    def test_maintenance_due_selects_quarterly_maintenance_mode(self):
        progress = {
            "completed": [
                {
                    "problem_id": "OBS-001",
                    "completed_at": "2026-01-01",
                    "revision": {
                        "status": "MASTERED",
                        "stage": 5,
                        "completed": ["2026-01-01"],
                        "next_due": None,
                        "history": [],
                        "last_maintenance": "2026-01-01",
                    },
                }
            ],
            "mastered_skills": [],
            "current_problem": None,
            "current_stage": "Observation",
        }
        # 90+ days after last_maintenance on a weekday -> maintenance recall due.
        selection = select_next_problem(self._state(progress), on_date=date(2026, 7, 22))
        self.assertEqual(selection.mode, "quarterly_maintenance")
        self.assertEqual(selection.problem["id"], "OBS-001")


class NormalizeWeaknessEntryTests(unittest.TestCase):
    """F20a: weaknesses_detected entries become structured objects; legacy
    strings (with "Resolved: "/"Mock: " prefixes) keep working in all readers."""

    def test_plain_string_is_open_session(self):
        self.assertEqual(
            _shared.normalize_weakness_entry("Forgot loop bounds."),
            {"text": "Forgot loop bounds.", "status": "open", "source": "session", "resolved_on": None},
        )

    def test_resolved_prefix_string_maps_to_resolved_status(self):
        self.assertEqual(
            _shared.normalize_weakness_entry("Resolved: confusion about update order."),
            {
                "text": "confusion about update order.",
                "status": "resolved",
                "source": "session",
                "resolved_on": None,
            },
        )

    def test_mock_prefix_string_maps_to_mock_source(self):
        self.assertEqual(
            _shared.normalize_weakness_entry("Mock: started coding before complexity."),
            {
                "text": "started coding before complexity.",
                "status": "open",
                "source": "mock",
                "resolved_on": None,
            },
        )

    def test_object_passes_through_with_defaults_for_bad_fields(self):
        entry = {"text": "x", "status": "weird", "source": "nowhere", "resolved_on": 5}
        self.assertEqual(
            _shared.normalize_weakness_entry(entry),
            {"text": "x", "status": "open", "source": "session", "resolved_on": None},
        )

    def test_well_formed_object_is_unchanged(self):
        entry = {"text": "x", "status": "resolved", "source": "revision", "resolved_on": "2026-07-01"}
        self.assertEqual(_shared.normalize_weakness_entry(entry), entry)


class WeaknessMigrationTests(unittest.TestCase):
    """F20a: migrate_progress_payload upgrades weaknesses_detected strings."""

    def test_migrate_converts_string_entries_to_objects(self):
        payload = {
            "completed": [],
            "weaknesses_detected": {
                "P-1": ["Resolved: old issue.", "Mock: mock issue.", "open issue."],
            },
        }
        _shared.migrate_progress_payload(payload)
        self.assertEqual(
            payload["weaknesses_detected"]["P-1"],
            [
                {"text": "old issue.", "status": "resolved", "source": "session", "resolved_on": None},
                {"text": "mock issue.", "status": "open", "source": "mock", "resolved_on": None},
                {"text": "open issue.", "status": "open", "source": "session", "resolved_on": None},
            ],
        )

    def test_migrate_tolerates_non_list_values(self):
        payload = {"completed": [], "weaknesses_detected": {"P-1": "not-a-list"}}
        _shared.migrate_progress_payload(payload)
        self.assertEqual(payload["weaknesses_detected"]["P-1"], "not-a-list")


class RevisionAdjustedScoreTests(unittest.TestCase):
    """F20b: weakest-skills blends latest revision recall into the solve score."""

    def test_no_revision_history_returns_solve_score(self):
        record = _completion("P-1", 0, {"understanding": 2, "algorithm_design": 2})
        self.assertEqual(_shared.revision_adjusted_problem_score(record, _SCORING), 2.0)

    def test_no_thinking_score_returns_none(self):
        record = _completion("P-1", 0, None)
        self.assertIsNone(_shared.revision_adjusted_problem_score(record, _SCORING))

    def test_blends_latest_revision_recall_average(self):
        record = _completion("P-1", 0, {"understanding": 2, "algorithm_design": 2})
        record["revision"] = {
            "history": [
                {"result": "PASS", "thinking_score": {"concept_recall": 2, "implementation": 2}},
                # Latest event wins: avg 7.5 on 0-10 -> 3.0 on 0-4.
                {"result": "PASS", "thinking_score": {"concept_recall": 10, "implementation": 5}},
            ]
        }
        # 0.6 * 3.0 + 0.4 * 2.0 = 2.6
        self.assertEqual(_shared.revision_adjusted_problem_score(record, _SCORING), 2.6)

    def test_weakest_skills_uses_blended_score(self):
        from pathlib import Path

        record = _completion("PRIMARY-001", 0, {"understanding": 2, "algorithm_design": 2})
        record["revision"] = {
            "history": [{"result": "PASS", "thinking_score": {"concept_recall": 10, "implementation": 5}}]
        }
        state = RepositoryState(
            curriculum={"problems": [{"id": "PRIMARY-001", "primary_skill": "SK-TEST"}]},
            graph={},
            stages={},
            skills=_SKILLS,
            patterns={},
            scoring=_SCORING,
            progress=_progress(record),
            progress_path=Path("test"),
        )
        results = _shared.weakest_skills(state)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["skill"], "SK-TEST")
        self.assertEqual(results[0]["average_weighted_thinking_score"], 2.6)


if __name__ == "__main__":
    unittest.main()
