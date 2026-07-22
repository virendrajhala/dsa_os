#!/usr/bin/env python3
"""Regression tests for scripts/weakness_lab.py evidence collection (F20).

Run: python3 scripts/test_weakness_lab.py
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from weakness_lab import collect_evidence


def _state(progress: dict) -> SimpleNamespace:
    return SimpleNamespace(progress=progress)


class CollectEvidenceTests(unittest.TestCase):
    """F20a/b: resolved entries stay out of clusters; revision FAILs feed in."""

    def test_open_entries_count_and_resolved_entries_are_skipped(self):
        progress = {
            "weaknesses_detected": {
                "P-1": [
                    {
                        "text": "wrong loop initialization",
                        "status": "open",
                        "source": "session",
                        "resolved_on": None,
                    },
                    {
                        "text": "wrong loop initialization",
                        "status": "resolved",
                        "source": "session",
                        "resolved_on": "2026-07-01",
                    },
                ],
            },
            "completed": [],
        }
        evidence = collect_evidence(_state(progress))
        items = evidence.get("implementation", [])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["text"], "wrong loop initialization")

    def test_legacy_string_entries_still_work(self):
        progress = {
            "weaknesses_detected": {
                "P-1": [
                    "wrong loop initialization",
                    "Resolved: wrong loop initialization",
                ],
            },
            "completed": [],
        }
        evidence = collect_evidence(_state(progress))
        self.assertEqual(len(evidence.get("implementation", [])), 1)

    def test_revision_fail_notes_become_revision_evidence(self):
        progress = {
            "weaknesses_detected": {},
            "completed": [
                {
                    "problem_id": "P-1",
                    "main_mistake": "None recorded",
                    "revision": {
                        "history": [
                            {
                                "result": "FAIL",
                                "notes": "could not restate the invariant proof",
                            },
                            {"result": "PASS", "notes": "wrong loop initialization"},
                        ]
                    },
                }
            ],
        }
        evidence = collect_evidence(_state(progress))
        items = evidence.get("pattern_detection", [])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source"], "revision.fail")
        self.assertEqual(items[0]["severity"], 1.1)
        # PASS event notes never become weakness evidence.
        self.assertNotIn("implementation", evidence)


if __name__ == "__main__":
    unittest.main()
