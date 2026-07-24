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
import shutil
import subprocess
import sys
import tempfile
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
    """Return the conventional solution path for a problem id.

    Python is the canonical gate file; a Java solution
    (`solutions/<PROBLEM-ID>.java`) is used when no `.py` exists, so a learner
    who codes in Java stores real Java and the gate still runs it. When both
    exist the `.py` wins (e.g. a Python port beside a reference `.java`).
    """

    py = solutions_dir / f"{problem_id}.py"
    if py.exists():
        return py
    java = solutions_dir / f"{problem_id}.java"
    if java.exists():
        return java
    return py


def resolve_target(target: str, solutions_dir: Path = SOLUTIONS_DIR) -> Path:
    """Resolve a CLI/caller target (problem id or explicit path) to a file path.

    A target ending in `.py` (or that already exists as a file) is treated as
    an explicit path. Anything else is treated as a problem id and resolved
    against `solutions_dir` using the `<PROBLEM-ID>.py` convention.
    """

    candidate = Path(target)
    if candidate.suffix in (".py", ".java") or candidate.exists():
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

    if path.suffix == ".java":
        return _run_java_file(path, timeout_seconds)

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


def _find_main_class(class_dir: Path) -> str | None:
    """Return the name of the compiled class that declares `main`, or None.

    A `.java` with no runnable entry point (a reference/library file) has no
    such class, so it is not treated as a gate file.
    """

    for compiled in sorted(class_dir.glob("*.class")):
        name = compiled.stem
        if "$" in name:  # inner/anonymous class
            continue
        inspected = subprocess.run(
            ["javap", "-cp", str(class_dir), name],
            capture_output=True,
            text=True,
        )
        if "public static void main(java.lang.String[])" in inspected.stdout:
            return name
    return None


def _run_java_file(path: Path, timeout_seconds: float) -> CheckResult:
    """Compile and run a Java solution with assertions enabled (`java -ea`).

    F9 for Java mirrors the Python contract: the file compiles, its `main`
    runs its embedded asserts, and it exits 0. javac/java must be on PATH.
    """

    if shutil.which("javac") is None or shutil.which("java") is None:
        return CheckResult(
            passed=False,
            message=f"Java toolchain (javac/java) not found; cannot run {path}",
        )

    with tempfile.TemporaryDirectory(prefix="dsa_os_java_") as tmp:
        try:
            compiled = subprocess.run(
                ["javac", "-d", tmp, str(path)],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return CheckResult(
                passed=False,
                message=f"Java compile timed out after {timeout_seconds:g}s: {path}",
            )
        if compiled.returncode != 0:
            tail = (compiled.stderr or compiled.stdout or "").strip().splitlines()
            detail = tail[-1] if tail else "compile error"
            return CheckResult(
                passed=False,
                message=f"Java solution failed to compile: {path} ({detail})",
                stdout=compiled.stdout,
                stderr=compiled.stderr,
            )

        main_class = _find_main_class(Path(tmp))
        if main_class is None:
            return CheckResult(
                passed=False,
                message=(
                    f"Java solution has no runnable entry point: {path}. Add a class "
                    "with `public static void main(String[])` that runs your asserts."
                ),
            )

        try:
            ran = subprocess.run(
                ["java", "-ea", "-cp", tmp, main_class],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return CheckResult(
                passed=False,
                message=f"Java solution timed out after {timeout_seconds:g}s: {path}",
            )

    if ran.returncode != 0:
        tail = (ran.stderr or ran.stdout or "").strip().splitlines()
        detail = tail[-1] if tail else f"exit code {ran.returncode}"
        return CheckResult(
            passed=False,
            message=f"Java solution failed: {path} ({detail})",
            stdout=ran.stdout,
            stderr=ran.stderr,
        )

    return CheckResult(passed=True, message=f"Passed: {path}", stdout=ran.stdout, stderr=ran.stderr)


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
