#!/usr/bin/env python3
"""Regression tests for scripts/_shared.py (stdlib unittest, no deps).

Run: python3 scripts/test_shared.py
"""

from __future__ import annotations

import unittest
from datetime import date

from _shared import apply_revision_result, compute_skill_progress, revision_stage_label


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


if __name__ == "__main__":
    unittest.main()
