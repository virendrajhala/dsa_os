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


def _pin_overdue_fixture(tmp_progress: Path) -> None:
    """Freeze the copied fixture so these tests don't depend on live state:
    OBS-005/OBS-006 are forced overdue (as of the 2026-07-21 --completed-at),
    every other revision is pushed far into the future, and any live
    completion of NEW_PROBLEM_ID is dropped so it stays a new solve."""

    payload = json.loads(tmp_progress.read_text())
    payload["completed"] = [
        r for r in payload["completed"] if r.get("problem_id") != NEW_PROBLEM_ID
    ]
    forced_overdue = {"OBS-005": "2026-07-17", "OBS-006": "2026-07-18"}
    for record in payload["completed"]:
        revision = record.get("revision")
        if not isinstance(revision, dict):
            continue
        if record["problem_id"] in forced_overdue:
            revision["status"] = "ACTIVE"
            revision["next_due"] = forced_overdue[record["problem_id"]]
        elif revision.get("next_due"):
            revision["next_due"] = "2099-01-01"
    tmp_progress.write_text(json.dumps(payload, indent=2))


class RevisionFirstGateTests(unittest.TestCase):
    """F3: recording a NEW solve must abort while a revision is overdue."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="dsa_os_test_")
        self.tmp_progress = Path(self.tmpdir) / "progress.json"
        shutil.copyfile(LIVE_PROGRESS, self.tmp_progress)
        _pin_overdue_fixture(self.tmp_progress)
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
        # Fixture pins OBS-005 (due 2026-07-17) and OBS-006 (due 2026-07-18)
        # overdue as of the 2026-07-21 --completed-at.
        result = self._run(BASE_ARGS)

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("OBS-005", result.stderr)
        self.assertIn("OBS-006", result.stderr)
        # Gate must fire before any write: the temp progress file must be
        # untouched.
        self.assertEqual(self.tmp_progress.read_bytes(), self.original_bytes)

    def test_override_revisions_bypasses_gate_and_logs_note(self) -> None:
        # F9: no solution file exists for NEW_PROBLEM_ID in this test, so
        # --no-code is required to get past the code-execution gate too.
        result = self._run([*BASE_ARGS, "--override-revisions", "--no-code"])

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

    def test_revision_recording_not_blocked_by_other_overdue_revisions(self) -> None:
        # Pins the F3 design point: revision mode is UNGATED — recording a
        # revision is how overdue state gets cleared, so OBS-001's revision
        # must record fine while OBS-005/OBS-006 are overdue.
        result = self._run(
            [*REVISION_BASE_ARGS, "--revision-result", "PASS", *_revision_score_args(9)]
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = json.loads(self.tmp_progress.read_text())
        record = next(r for r in updated["completed"] if r["problem_id"] == REVISION_PROBLEM_ID)
        self.assertEqual(record["revision"]["history"][-1]["result"], "PASS")

    def test_new_solve_not_blocked_when_no_revisions_overdue(self) -> None:
        # Push every overdue revision's next_due far into the future so the
        # gate has nothing to fire on, proving it's not a blanket block.
        payload = json.loads(self.tmp_progress.read_text())
        for record in payload["completed"]:
            revision = record.get("revision")
            if isinstance(revision, dict) and revision.get("next_due"):
                revision["next_due"] = "2099-01-01"
        self.tmp_progress.write_text(json.dumps(payload, indent=2))

        # F9: no solution file exists for NEW_PROBLEM_ID in this test, so
        # --no-code is required to get past the code-execution gate too.
        result = self._run([*BASE_ARGS, "--no-code"])
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)


# A curriculum problem id that IS already completed in the live fixture, so
# recording it with --revision-result exercises the revision path.
REVISION_PROBLEM_ID = "OBS-001"

# All 8 revision_evaluation dimensions from progress/scoring.json.
REVISION_DIMENSIONS = [
    "concept_recall",
    "invariant_recall",
    "algorithm_reconstruction",
    "implementation",
    "hint_dependency",
    "confidence",
    "implementation_blueprint",
    "code_from_memory",
]


def _revision_score_args(value: int) -> list[str]:
    args: list[str] = []
    for dimension in REVISION_DIMENSIONS:
        args += ["--revision-score", f"{dimension}={value}"]
    return args


REVISION_BASE_ARGS = [
    "--problem-id", REVISION_PROBLEM_ID,
    "--completed-at", "2026-07-21",
    "--hint-level-used", "1",
    "--confidence-after", "8",
    "--format", "json",
]


class RevisionPassMinimumTests(unittest.TestCase):
    """F5: --revision-result PASS must meet scoring.json's pass_minimum."""

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

    def test_pass_below_pass_minimum_rejected(self) -> None:
        result = self._run(
            [*REVISION_BASE_ARGS, "--revision-result", "PASS", *_revision_score_args(5)]
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("force-pass", result.stderr.lower())
        # Rejected before any write: the temp progress file must be untouched.
        self.assertEqual(self.tmp_progress.read_bytes(), self.original_bytes)

    def test_pass_below_pass_minimum_recorded_with_force_pass(self) -> None:
        reason = "Interviewer accepted the verbal recall live."
        result = self._run(
            [
                *REVISION_BASE_ARGS,
                "--revision-result", "PASS",
                *_revision_score_args(5),
                "--force-pass",
                "--force-pass-reason", reason,
            ]
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = json.loads(self.tmp_progress.read_text())
        record = next(r for r in updated["completed"] if r["problem_id"] == REVISION_PROBLEM_ID)
        history = record["revision"]["history"]
        self.assertEqual(history[-1]["result"], "PASS")
        self.assertEqual(history[-1]["force_pass_reason"], reason)

    def test_revision_recordable_without_any_solve_rubric_args(self) -> None:
        # Only revision scores, result, hint level, confidence-after: no
        # --time-taken-minutes, --confidence-before, --thinking-breakthrough,
        # --main-mistake, --thinking-score, or --interview-score.
        result = self._run(
            [*REVISION_BASE_ARGS, "--revision-result", "PASS", *_revision_score_args(9)]
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = json.loads(self.tmp_progress.read_text())
        record = next(r for r in updated["completed"] if r["problem_id"] == REVISION_PROBLEM_ID)
        self.assertEqual(record["revision"]["history"][-1]["result"], "PASS")

    def test_mode_revision_without_revision_result_rejected(self) -> None:
        # Footgun guard: `--mode revision` used to fall through to the
        # new-solve path when --revision-result was forgotten, silently
        # recording a bogus solve instead of a revision.
        result = self._run([*REVISION_BASE_ARGS, "--mode", "revision"])

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("--revision-result", result.stderr)
        self.assertEqual(self.tmp_progress.read_bytes(), self.original_bytes)

    def test_mode_solve_with_revision_result_rejected(self) -> None:
        # The mirror-image mismatch: an explicit solve mode combined with
        # revision args must not silently record a revision.
        result = self._run(
            [*REVISION_BASE_ARGS, "--mode", "solve", "--revision-result", "PASS",
             *_revision_score_args(9)]
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("--revision-result", result.stderr)
        self.assertEqual(self.tmp_progress.read_bytes(), self.original_bytes)

    def test_fail_below_pass_minimum_recorded_without_force(self) -> None:
        result = self._run(
            [*REVISION_BASE_ARGS, "--revision-result", "FAIL", *_revision_score_args(3)]
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = json.loads(self.tmp_progress.read_text())
        record = next(r for r in updated["completed"] if r["problem_id"] == REVISION_PROBLEM_ID)
        self.assertEqual(record["revision"]["history"][-1]["result"], "FAIL")


WELL_FORMED_MENTOR_THINKING_ARGS = [
    "--mentor-thinking-score", "understanding=3",
    "--mentor-thinking-score", "examples=3",
    "--mentor-thinking-score", "brute_force=3",
    "--mentor-thinking-score", "pattern_detection=3",
    "--mentor-thinking-score", "algorithm_design=3",
    "--mentor-thinking-score", "complexity_analysis=3",
    "--mentor-thinking-score", "implementation=3",
    "--mentor-thinking-score", "communication=3",
]

WELL_FORMED_MENTOR_INTERVIEW_ARGS = [
    "--mentor-interview-score", "understanding=7",
    "--mentor-interview-score", "communication=7",
    "--mentor-interview-score", "algorithm=7",
    "--mentor-interview-score", "coding=7",
    "--mentor-interview-score", "complexity=7",
]


class MentorScoresTests(unittest.TestCase):
    """F7: --mentor-thinking-score / --mentor-interview-score on new solves."""

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

    def test_full_mentor_blocks_recorded_and_validates(self) -> None:
        # Live fixture has overdue revisions (see RevisionFirstGateTests);
        # override that unrelated gate so this exercises mentor-score
        # recording specifically.
        # F9: no solution file exists for NEW_PROBLEM_ID in this test, so
        # --no-code is required to get past the code-execution gate too.
        result = self._run(
            [
                *BASE_ARGS,
                "--override-revisions",
                "--no-code",
                *WELL_FORMED_MENTOR_THINKING_ARGS,
                *WELL_FORMED_MENTOR_INTERVIEW_ARGS,
            ]
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = json.loads(self.tmp_progress.read_text())
        record = next(r for r in updated["completed"] if r["problem_id"] == NEW_PROBLEM_ID)
        mentor_scores = record.get("mentor_scores")
        self.assertIsInstance(mentor_scores, dict)
        self.assertEqual(mentor_scores["thinking_score"]["understanding"], 3)
        self.assertEqual(mentor_scores["interview_score"]["understanding"], 7)

        validate = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate_curriculum.py"),
                "--progress-file", str(self.tmp_progress),
                "--skip-template-progress",
            ],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)

    def test_partial_mentor_block_rejected(self) -> None:
        # Only mentor-thinking dims given, no mentor-interview dims: since
        # ANY mentor score was provided, both blocks must be complete.
        result = self._run([*BASE_ARGS, *WELL_FORMED_MENTOR_THINKING_ARGS])

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("mentor interview score", result.stderr.lower())
        # Rejected before any write: the temp progress file must be untouched.
        self.assertEqual(self.tmp_progress.read_bytes(), self.original_bytes)

    def test_mentor_scores_absent_writes_no_key(self) -> None:
        # F9: no solution file exists for NEW_PROBLEM_ID in this test, so
        # --no-code is required to get past the code-execution gate too.
        result = self._run([*BASE_ARGS, "--override-revisions", "--no-code"])

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = json.loads(self.tmp_progress.read_text())
        record = next(r for r in updated["completed"] if r["problem_id"] == NEW_PROBLEM_ID)
        self.assertNotIn("mentor_scores", record)


class CodeExecutionGateTests(unittest.TestCase):
    """F9: a NEW solve is gated on a runnable solutions/<PROBLEM-ID>.py file.

    Revision mode is never gated. Uses --solutions-dir to point the gate at a
    temp directory so no real solutions/ files are read or written.
    """

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="dsa_os_test_")
        self.tmp_progress = Path(self.tmpdir) / "progress.json"
        shutil.copyfile(LIVE_PROGRESS, self.tmp_progress)
        # Push every overdue revision out of the way so only the F9 code gate
        # (not the F3 revision-first gate) is under test here.
        payload = json.loads(self.tmp_progress.read_text())
        for record in payload["completed"]:
            revision = record.get("revision")
            if isinstance(revision, dict) and revision.get("next_due"):
                revision["next_due"] = "2099-01-01"
        self.tmp_progress.write_text(json.dumps(payload, indent=2))
        self.original_bytes = self.tmp_progress.read_bytes()

        self.solutions_dir = Path(self.tmpdir) / "solutions"
        self.solutions_dir.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, extra_args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--progress-file", str(self.tmp_progress),
                "--solutions-dir", str(self.solutions_dir),
                *extra_args,
            ],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )

    def test_new_solve_without_solution_file_aborts_with_expected_path(self) -> None:
        result = self._run(BASE_ARGS)

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        expected_path = str(self.solutions_dir / f"{NEW_PROBLEM_ID}.py")
        self.assertIn(expected_path, result.stderr)
        # Gate must fire before any write: the temp progress file must be
        # untouched.
        self.assertEqual(self.tmp_progress.read_bytes(), self.original_bytes)

    def test_new_solve_with_valid_solution_file_proceeds(self) -> None:
        (self.solutions_dir / f"{NEW_PROBLEM_ID}.py").write_text(
            "assert 1 + 1 == 2\nassert sorted([3, 1, 2]) == [1, 2, 3]\n"
        )

        result = self._run(BASE_ARGS)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = json.loads(self.tmp_progress.read_text())
        record = next(r for r in updated["completed"] if r["problem_id"] == NEW_PROBLEM_ID)
        self.assertNotIn("notes", record)

    def test_new_solve_with_failing_solution_file_aborts(self) -> None:
        (self.solutions_dir / f"{NEW_PROBLEM_ID}.py").write_text(
            "assert 1 == 2, 'deliberate failure'\n"
        )

        result = self._run(BASE_ARGS)

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertEqual(self.tmp_progress.read_bytes(), self.original_bytes)

    def test_new_solve_with_bare_assert_failure_surfaces_traceback(self) -> None:
        # A bare `assert expr` (no message) degrades check.message to just
        # "AssertionError"; the file/line/expression only live in stderr.
        # The gate-failure RepositoryError must surface that traceback tail
        # so the learner sees the failing assert, not just "AssertionError".
        (self.solutions_dir / f"{NEW_PROBLEM_ID}.py").write_text(
            "x = 1\nassert x == 2\n"
        )

        result = self._run(BASE_ARGS)

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("Traceback", result.stderr)
        self.assertIn("assert x == 2", result.stderr)
        self.assertEqual(self.tmp_progress.read_bytes(), self.original_bytes)

    def test_no_code_bypasses_gate_and_records_note(self) -> None:
        result = self._run([*BASE_ARGS, "--no-code"])

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = json.loads(self.tmp_progress.read_text())
        record = next(r for r in updated["completed"] if r["problem_id"] == NEW_PROBLEM_ID)
        notes = record.get("notes")
        self.assertIsInstance(notes, list)
        self.assertTrue(notes, "expected a --no-code note recorded on the new record")
        self.assertTrue(any("no-code" in note.lower() for note in notes))

    def test_note_appended_as_dated_object(self) -> None:
        # F22: progress.notes entries append as {"date", "text"} objects going
        # forward; historical string entries are never rewritten.
        payload = json.loads(self.tmp_progress.read_text())
        payload.setdefault("notes", []).append("legacy string note")
        self.tmp_progress.write_text(json.dumps(payload, indent=2))

        result = self._run([*BASE_ARGS, "--no-code", "--note", "structured note text"])

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = json.loads(self.tmp_progress.read_text())
        self.assertIn("legacy string note", updated["notes"])
        self.assertIn(
            {"date": "2026-07-21", "text": "structured note text"},
            updated["notes"],
        )

    def test_revision_mode_unaffected_by_missing_solution_file(self) -> None:
        # No solution file exists for REVISION_PROBLEM_ID in the temp
        # solutions dir, and --no-code is not passed; revision mode must not
        # be gated on code execution at all.
        result = self._run(
            [*REVISION_BASE_ARGS, "--revision-result", "PASS", *_revision_score_args(9)]
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = json.loads(self.tmp_progress.read_text())
        record = next(r for r in updated["completed"] if r["problem_id"] == REVISION_PROBLEM_ID)
        self.assertEqual(record["revision"]["history"][-1]["result"], "PASS")


VALIDATOR = ROOT / "scripts" / "validate_curriculum.py"

MOCK_ARGS = [
    "--mode", "mock",
    "--problem-id", "CPX-004",
    "--completed-at", "2026-07-25",
    "--mock-duration-minutes", "42",
    "--mock-score", "problem_solving=3",
    "--mock-score", "communication=3",
    "--mock-score", "code_quality=3",
    "--mock-score", "testing=2",
    "--mock-score", "time_management=3",
    "--mock-verdict", "hire",
    "--mock-notes", "Found the approach unprompted; missed the self-match edge case.",
    "--mock-weakness", "Started coding before stating complexity.",
    "--format", "json",
]


class MockInterviewRecordingTests(unittest.TestCase):
    """F10: --mode mock records into mock_interviews[] and mirrors weaknesses.

    A mock never touches completion records, revision state, or the current
    problem, so it is not blocked by the overdue-revision gate even though the
    live fixture has overdue revisions.
    """

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="dsa_os_test_")
        self.tmp_progress = Path(self.tmpdir) / "progress.json"
        shutil.copyfile(LIVE_PROGRESS, self.tmp_progress)
        self.original = json.loads(self.tmp_progress.read_text())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, extra_args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--progress-file", str(self.tmp_progress), *extra_args],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )

    def _validate(self) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--progress-file",
                str(self.tmp_progress),
                "--skip-template-progress",
            ],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )

    def test_mock_round_trip(self) -> None:
        result = self._run(MOCK_ARGS)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

        updated = json.loads(self.tmp_progress.read_text())
        self.assertEqual(len(updated["mock_interviews"]), 1)
        entry = updated["mock_interviews"][0]
        self.assertEqual(entry["problem_id"], "CPX-004")
        self.assertEqual(entry["date"], "2026-07-25")
        self.assertEqual(entry["duration_minutes"], 42)
        self.assertEqual(entry["verdict"], "hire")
        self.assertEqual(
            set(entry["scores"]),
            {"problem_solving", "communication", "code_quality", "testing", "time_management"},
        )
        self.assertEqual(entry["scores"]["testing"], 2)
        self.assertEqual(entry["weaknesses"], ["Started coding before stating complexity."])

        # Weakness mirrored into weaknesses_detected as a structured object
        # with source "mock" (F20a; formerly a "Mock: "-prefixed string).
        self.assertIn(
            {
                "text": "Started coding before stating complexity.",
                "status": "open",
                "source": "mock",
                "resolved_on": None,
            },
            updated["weaknesses_detected"]["CPX-004"],
        )

        # A mock does not create or mutate completion records.
        self.assertEqual(updated["completed"], self.original["completed"])

        # The recorded state must pass the validator.
        validation = self._validate()
        self.assertEqual(validation.returncode, 0, msg=validation.stdout + validation.stderr)

    def test_mock_requires_all_scores(self) -> None:
        # Drop the time_management dimension (its "--mock-score" flag and value)
        # so the block is incomplete but still argparse-valid.
        idx = MOCK_ARGS.index("time_management=3")
        incomplete = MOCK_ARGS[: idx - 1] + MOCK_ARGS[idx + 1 :]
        result = self._run(incomplete)
        self.assertNotEqual(result.returncode, 0, msg=result.stdout)
        self.assertIn("mock score", result.stderr)
        # Gate fires before any write.
        self.assertNotIn("mock_interviews", json.loads(self.tmp_progress.read_text()))


if __name__ == "__main__":
    unittest.main()
