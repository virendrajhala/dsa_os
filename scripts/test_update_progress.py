#!/usr/bin/env python3
"""Regression tests for scripts/update_progress.py (stdlib unittest, no deps).

Run: python3 scripts/test_update_progress.py

These tests never touch the live progress/progress.json. They copy it to a
temp file and pass --progress-file explicitly so the real file is never
opened for writing.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "update_progress.py"
LIVE_PROGRESS = ROOT / "progress" / "progress.json"

# A curriculum problem id that is NOT yet completed in the live fixture, so
# recording it exercises the "new solve" path (not the revision path).
NEW_PROBLEM_ID = "OBS-009"

BASE_ARGS = [
    "--problem-id", NEW_PROBLEM_ID,
    "--completed-at", "2026-07-21",
    "--time-taken-minutes", "20",
    "--hint-level-used", "1",
    "--confidence-before", "5",
    "--confidence-after", "8",
    "--thinking-breakthrough", "Test breakthrough.",
    "--main-mistake", "Test mistake.",
    "--thinking-score", "understanding=3",
    "--thinking-score", "examples=3",
    "--thinking-score", "brute_force=3",
    "--thinking-score", "pattern_detection=3",
    "--thinking-score", "algorithm_design=3",
    "--thinking-score", "complexity_analysis=3",
    "--thinking-score", "implementation=3",
    "--thinking-score", "communication=3",
    "--interview-score", "understanding=7",
    "--interview-score", "communication=7",
    "--interview-score", "algorithm=7",
    "--interview-score", "coding=7",
    "--interview-score", "complexity=7",
    "--format", "json",
]


class RevisionFirstGateTests(unittest.TestCase):
    """F3: recording a NEW solve must abort while a revision is overdue."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="dsa_os_test_")
        self.tmp_progress = Path(self.tmpdir) / "progress.json"
        shutil.copyfile(LIVE_PROGRESS, self.tmp_progress)
        self.original_bytes = self.tmp_progress.read_bytes()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, extra_args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--progress-file", str(self.tmp_progress), *extra_args],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )

    def test_new_solve_blocked_while_revisions_overdue(self) -> None:
        # Live fixture has OBS-005 (due 2026-07-17) and OBS-006 (due
        # 2026-07-18) overdue as of 2026-07-21.
        result = self._run(BASE_ARGS)

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("OBS-005", result.stderr)
        self.assertIn("OBS-006", result.stderr)
        # Gate must fire before any write: the temp progress file must be
        # untouched.
        self.assertEqual(self.tmp_progress.read_bytes(), self.original_bytes)

    def test_override_revisions_bypasses_gate_and_logs_note(self) -> None:
        result = self._run([*BASE_ARGS, "--override-revisions"])

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["problem_id"], NEW_PROBLEM_ID)

        updated = json.loads(self.tmp_progress.read_text())
        record = next(r for r in updated["completed"] if r["problem_id"] == NEW_PROBLEM_ID)
        notes = record.get("notes")
        self.assertIsInstance(notes, list)
        self.assertTrue(notes, "expected an override note recorded on the new record")
        joined = " ".join(notes)
        self.assertIn("OBS-005", joined)
        self.assertIn("OBS-006", joined)
        self.assertIn("override", joined.lower())

    def test_new_solve_not_blocked_when_no_revisions_overdue(self) -> None:
        # Push every overdue revision's next_due far into the future so the
        # gate has nothing to fire on, proving it's not a blanket block.
        payload = json.loads(self.tmp_progress.read_text())
        for record in payload["completed"]:
            revision = record.get("revision")
            if isinstance(revision, dict) and revision.get("next_due"):
                revision["next_due"] = "2099-01-01"
        self.tmp_progress.write_text(json.dumps(payload, indent=2))

        result = self._run(BASE_ARGS)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
