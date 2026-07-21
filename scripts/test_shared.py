#!/usr/bin/env python3
"""Regression tests for scripts/_shared.py (stdlib unittest, no deps).

Run: python3 scripts/test_shared.py
"""

from __future__ import annotations

import unittest
from datetime import date

from _shared import apply_revision_result, revision_stage_label


def _record(problem_id: str = "TEST-001", completed_at: str = "2026-01-01") -> dict:
    return {"problem_id": problem_id, "completed_at": completed_at}


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
