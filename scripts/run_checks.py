#!/usr/bin/env python3
"""Run a learner's solution file as a minimal code-execution check.

F9: "solved means it ran." Convention: `solutions/<PROBLEM-ID>.py` holds the
learner's solution plus 3-5 embedded asserts they write themselves. This
script runs one solution file in a subprocess with a timeout and reports
pass/fail. Exit 0 only if the file exists AND runs to completion without an
assertion failure, exception, or timeout. Deliberately NOT a full test
harness.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOLUTIONS_DIR = ROOT / "solutions"
DEFAULT_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class CheckResult:
    """Outcome of running one solution file."""

    passed: bool
    message: str
    stdout: str = ""
    stderr: str = ""


def solution_path_for(problem_id: str, solutions_dir: Path = SOLUTIONS_DIR) -> Path:
    """Return the conventional solution path for a problem id."""

    return solutions_dir / f"{problem_id}.py"


def resolve_target(target: str, solutions_dir: Path = SOLUTIONS_DIR) -> Path:
    """Resolve a CLI/caller target (problem id or explicit path) to a file path.

    A target ending in `.py` (or that already exists as a file) is treated as
    an explicit path. Anything else is treated as a problem id and resolved
    against `solutions_dir` using the `<PROBLEM-ID>.py` convention.
    """

    candidate = Path(target)
    if candidate.suffix == ".py" or candidate.exists():
        return candidate
    return solution_path_for(target, solutions_dir)


def run_solution_file(path: Path, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> CheckResult:
    """Run one solution file in a subprocess and report pass/fail.

    Passes only if the file exists AND runs to completion (exit 0) within
    `timeout_seconds`. An assertion failure, any other exception, or a
    timeout is a fail.
    """

    if not path.exists():
        return CheckResult(passed=False, message=f"Solution file not found: {path}")

    try:
        completed = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            passed=False,
            message=f"Solution file timed out after {timeout_seconds:g}s: {path}",
        )

    if completed.returncode != 0:
        tail_lines = (completed.stderr or completed.stdout or "").strip().splitlines()
        detail = tail_lines[-1] if tail_lines else f"exit code {completed.returncode}"
        return CheckResult(
            passed=False,
            message=f"Solution file failed: {path} ({detail})",
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    return CheckResult(
        passed=True,
        message=f"Passed: {path}",
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Run a solution file (by problem id or explicit path) as a minimal "
            "code-execution check. Exit 0 only if the file exists and runs "
            "without an assertion failure, exception, or timeout."
        ),
        epilog=(
            "Examples:\n"
            "  python3 scripts/run_checks.py OBS-001\n"
            "  python3 scripts/run_checks.py solutions/OBS-001.py --timeout 10\n"
            "  make check-solution PROBLEM=OBS-001"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("target", help="Problem id (e.g. OBS-001) or explicit path to a solution file.")
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Timeout in seconds. Defaults to {DEFAULT_TIMEOUT_SECONDS:g}.",
    )
    parser.add_argument(
        "--solutions-dir",
        default=str(SOLUTIONS_DIR),
        help="Override the solutions directory used when target is a bare problem id.",
    )
    return parser


def main() -> int:
    """Run the CLI."""

    parser = build_parser()
    args = parser.parse_args()
    path = resolve_target(args.target, Path(args.solutions_dir))
    result = run_solution_file(path, timeout_seconds=args.timeout)
    print(result.message)
    if not result.passed and result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
