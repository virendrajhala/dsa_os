#!/usr/bin/env python3
"""Regression tests for scripts/run_checks.py (stdlib unittest, no deps).

Run: python3 scripts/test_run_checks.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "run_checks.py"

sys.path.insert(0, str(ROOT / "scripts"))
from run_checks import resolve_target, run_solution_file, solution_path_for  # noqa: E402


class RunSolutionFileTests(unittest.TestCase):
    """Direct tests of the run_solution_file check function."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="dsa_os_run_checks_test_")
        self.tmpdir_path = Path(self.tmpdir)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_passes_on_good_solution(self) -> None:
        path = self.tmpdir_path / "GOOD.py"
        path.write_text(
            "assert 1 + 1 == 2\n"
            "assert sorted([3, 1, 2]) == [1, 2, 3]\n"
            "assert sorted([]) == []  # edge case\n"
        )

        result = run_solution_file(path, timeout_seconds=5)

        self.assertTrue(result.passed, msg=result.message)

    def test_fails_on_assert_failure(self) -> None:
        path = self.tmpdir_path / "BAD.py"
        path.write_text("assert 1 == 2, 'deliberately wrong'\n")

        result = run_solution_file(path, timeout_seconds=5)

        self.assertFalse(result.passed)
        self.assertIn(str(path), result.message)

    def test_fails_on_other_exception(self) -> None:
        path = self.tmpdir_path / "RAISES.py"
        path.write_text("raise ValueError('boom')\n")

        result = run_solution_file(path, timeout_seconds=5)

        self.assertFalse(result.passed)

    def test_fails_on_missing_file(self) -> None:
        path = self.tmpdir_path / "MISSING.py"

        result = run_solution_file(path, timeout_seconds=5)

        self.assertFalse(result.passed)
        self.assertIn("not found", result.message.lower())

    def test_times_out_on_infinite_loop(self) -> None:
        path = self.tmpdir_path / "INFINITE.py"
        path.write_text("while True:\n    pass\n")

        # Tiny timeout override so the test itself stays fast.
        result = run_solution_file(path, timeout_seconds=0.5)

        self.assertFalse(result.passed)
        self.assertIn("timed out", result.message.lower())


class ResolveTargetTests(unittest.TestCase):
    """Target resolution: bare problem id vs explicit path."""

    def test_resolve_problem_id_uses_solutions_dir(self) -> None:
        solutions_dir = Path("/tmp/dsa_os_example_solutions")

        resolved = resolve_target("OBS-001", solutions_dir)

        self.assertEqual(resolved, solutions_dir / "OBS-001.py")
        self.assertEqual(resolved, solution_path_for("OBS-001", solutions_dir))

    def test_resolve_explicit_path_used_directly(self) -> None:
        resolved = resolve_target("/some/other/path.py", Path("/tmp/dsa_os_example_solutions"))

        self.assertEqual(resolved, Path("/some/other/path.py"))


class CLITests(unittest.TestCase):
    """End-to-end CLI tests (exit codes)."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="dsa_os_run_checks_cli_test_")
        self.tmpdir_path = Path(self.tmpdir)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )

    def test_cli_exit_zero_on_pass(self) -> None:
        path = self.tmpdir_path / "GOOD.py"
        path.write_text("assert True\n")

        result = self._run([str(path)])

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_cli_exit_nonzero_on_missing_problem_id(self) -> None:
        result = self._run(["NOPE-999", "--solutions-dir", str(self.tmpdir_path)])

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_cli_exit_nonzero_on_failing_solution(self) -> None:
        path = self.tmpdir_path / "BAD.py"
        path.write_text("assert False\n")

        result = self._run([str(path)])

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_cli_respects_timeout_flag(self) -> None:
        path = self.tmpdir_path / "INFINITE.py"
        path.write_text("while True:\n    pass\n")

        result = self._run([str(path), "--timeout", "0.5"])

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("timed out", (result.stdout + result.stderr).lower())


if __name__ == "__main__":
    unittest.main()
