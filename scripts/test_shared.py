#!/usr/bin/env python3
"""Regression tests for scripts/_shared.py (stdlib unittest, no deps).

Run: python3 scripts/test_shared.py
"""

from __future__ import annotations

import unittest
from datetime import date

import _shared
from _shared import (
    RepositoryState,
    apply_revision_result,
    compute_skill_progress,
    is_mock_due,
    load_json_file,
    revision_stage_label,
    select_next_problem,
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


if __name__ == "__main__":
    unittest.main()
