#!/usr/bin/env python3
"""Update live progress after a problem solve or revision session."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from typing import Any

from pathlib import Path

from _shared import (
    DEFERRED_LEARNING_CATEGORIES,
    DEFERRED_LEARNING_PRIORITIES,
    RepositoryError,
    append_history_event,
    apply_revision_result,
    completed_problem_ids,
    current_problem_id,
    create_deferred_learning,
    format_iso_date,
    initial_revision_state,
    latest_records_by_problem,
    load_repository_state,
    normalize_progress,
    parse_iso_date,
    problem_lookup,
    reactivate_revision,
    resolve_deferred_learning,
    revision_due_entries,
    save_json_file,
    select_next_problem,
)
from run_checks import (
    DEFAULT_TIMEOUT_SECONDS,
    SOLUTIONS_DIR,
    run_solution_file,
    solution_path_for,
)


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Mark a new problem complete or record an active-recall revision result, update "
            "progress summaries, and choose the next problem automatically."
        ),
        epilog=(
            "Example:\n"
            "  python3 scripts/update_progress.py "
            "--problem-id OBS-001 "
            "--time-taken-minutes 42 "
            "--hint-level-used 2 "
            "--confidence-before 3 "
            "--confidence-after 8 "
            "--thinking-breakthrough \"Reframed the problem as an invariant scan.\" "
            "--main-mistake \"Tried to optimize before writing the baseline.\" "
            "--thinking-score understanding=3 --thinking-score examples=3 "
            "--thinking-score brute_force=3 --thinking-score pattern_detection=4 "
            "--thinking-score algorithm_design=3 --thinking-score complexity_analysis=3 "
            "--thinking-score implementation=3 --thinking-score communication=4 "
            "--algorithm-thinking-score 7.5 --implementation-engineering-score 7.5 "
            "--interview-score understanding=7 --interview-score communication=8 "
            "--interview-score algorithm=7 --interview-score coding=7 --interview-score complexity=8\n\n"
            "Revision example (no solve-rubric args needed):\n"
            "  python3 scripts/update_progress.py "
            "--problem-id OBS-001 --revision-result PASS "
            "--hint-level-used 1 --confidence-after 8 "
            "--revision-score concept_recall=9 --revision-score invariant_recall=8 "
            "--revision-score algorithm_reconstruction=8 --revision-score implementation=8 "
            "--revision-score implementation_blueprint=8 --revision-score code_from_memory=8 "
            "--revision-score hint_dependency=9 --revision-score confidence=8\n\n"
            "Force-pass example (average revision score below scoring.json pass_minimum):\n"
            "  python3 scripts/update_progress.py "
            "--problem-id OBS-001 --revision-result PASS "
            "--hint-level-used 3 --confidence-after 5 "
            "--revision-score concept_recall=5 --revision-score invariant_recall=5 "
            "--revision-score algorithm_reconstruction=5 --revision-score implementation=5 "
            "--revision-score implementation_blueprint=5 --revision-score code_from_memory=5 "
            "--revision-score hint_dependency=5 --revision-score confidence=5 "
            "--force-pass --force-pass-reason \"Interviewer accepted the verbal recall live.\"\n\n"
            "Prerequisite reinforcement example:\n"
            "  Add to a normal progress command: --reactivate-problem OBS-005 "
            "--reactivation-reason \"Jump Game reachability invariant was weak.\""
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--progress-file",
        help="Override the progress file path. Defaults to progress/progress.json.",
    )
    parser.add_argument(
        "--problem-id",
        help="Problem to mark complete. Defaults to the active current problem.",
    )
    parser.add_argument(
        "--completed-at",
        default=date.today().isoformat(),
        help="Completion date in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument(
        "--time-taken-minutes",
        type=int,
        help="Minutes spent in the session. Required for a new solve; ignored for --revision-result.",
    )
    parser.add_argument(
        "--hint-level-used",
        required=True,
        type=int,
        help="Hint level used during the session. See progress/scoring.json. Required in both modes.",
    )
    parser.add_argument(
        "--confidence-before",
        type=int,
        help="Confidence before solving on a 0-10 scale. Required for a new solve; ignored for --revision-result.",
    )
    parser.add_argument(
        "--confidence-after",
        required=True,
        type=int,
        help="Confidence after solving on a 0-10 scale. Required in both modes.",
    )
    parser.add_argument(
        "--thinking-breakthrough",
        help="Short description of what unlocked the solve. Required for a new solve; ignored for --revision-result.",
    )
    parser.add_argument(
        "--main-mistake",
        help="Primary mistake or trap encountered during the solve. Required for a new solve; ignored for --revision-result.",
    )
    parser.add_argument(
        "--thinking-score",
        action="append",
        default=[],
        metavar="DIMENSION=VALUE",
        help=(
            "Thinking-rubric score entry. Repeat once per dimension. Required (all dimensions) "
            "for a new solve; ignored for --revision-result."
        ),
    )
    parser.add_argument(
        "--interview-score",
        action="append",
        default=[],
        metavar="DIMENSION=VALUE",
        help=(
            "Interview-rubric score entry. Repeat once per dimension. Required (all dimensions) "
            "for a new solve; ignored for --revision-result."
        ),
    )
    parser.add_argument(
        "--mentor-thinking-score",
        action="append",
        default=[],
        metavar="DIMENSION=VALUE",
        help=(
            "Mentor-graded thinking-rubric score entry. Repeat once per dimension. Optional; if "
            "any mentor score is given, all mentor-thinking and mentor-interview dimensions are "
            "required. Ignored for --revision-result."
        ),
    )
    parser.add_argument(
        "--mentor-interview-score",
        action="append",
        default=[],
        metavar="DIMENSION=VALUE",
        help=(
            "Mentor-graded interview-rubric score entry. Repeat once per dimension. Optional; if "
            "any mentor score is given, all mentor-thinking and mentor-interview dimensions are "
            "required. Ignored for --revision-result."
        ),
    )
    parser.add_argument(
        "--algorithm-thinking-score",
        type=float,
        help="Independent Algorithm Thinking score on a 0-10 scale.",
    )
    parser.add_argument(
        "--implementation-engineering-score",
        type=float,
        help="Independent Implementation Engineering score on a 0-10 scale.",
    )
    parser.add_argument(
        "--implementation-error",
        action="append",
        default=[],
        help="Implementation Engineering error to append to progress tracking.",
    )
    parser.add_argument(
        "--implementation-strength",
        action="append",
        default=[],
        help="Implementation Engineering strength to append to progress tracking.",
    )
    parser.add_argument(
        "--implementation-weakness",
        action="append",
        default=[],
        help="Implementation Engineering weakness to append to progress tracking.",
    )
    parser.add_argument(
        "--implementation-note",
        action="append",
        default=[],
        help="Implementation Engineering improvement note to append to progress tracking.",
    )
    parser.add_argument(
        "--revision-result",
        choices=("PASS", "FAIL"),
        help=(
            "Record an active-recall revision result for an already completed problem. "
            "PASS requires the average --revision-score to meet scoring.json's pass_minimum, "
            "or --force-pass with --force-pass-reason."
        ),
    )
    parser.add_argument(
        "--override-revisions",
        action="store_true",
        help=(
            "Bypass the overdue-revision gate when recording a NEW solve. "
            "Records an override note on the new completion record."
        ),
    )
    parser.add_argument(
        "--revision-score",
        action="append",
        default=[],
        metavar="DIMENSION=VALUE",
        help="Revision rubric score entry. Repeat once per revision dimension. Required for --revision-result.",
    )
    parser.add_argument(
        "--no-code",
        action="store_true",
        help=(
            "F9: bypass the runnable-solution gate for a NEW solve (whiteboard-style "
            "session with no code). Records a note on the new completion record. "
            "Ignored for --revision-result."
        ),
    )
    parser.add_argument(
        "--solutions-dir",
        help=(
            "Override the solutions/ directory used by the F9 code-execution gate. "
            "Defaults to solutions/ at the repository root. Mainly for tests."
        ),
    )
    parser.add_argument(
        "--code-check-timeout",
        type=float,
        help=f"Override the F9 code-execution gate's subprocess timeout in seconds. Defaults to {DEFAULT_TIMEOUT_SECONDS:g}.",
    )
    parser.add_argument(
        "--force-pass",
        action="store_true",
        help=(
            "Record --revision-result PASS even though the average --revision-score is below "
            "scoring.json's pass_minimum. Requires --force-pass-reason."
        ),
    )
    parser.add_argument(
        "--force-pass-reason",
        help="Reason recorded on the revision history event when using --force-pass.",
    )
    parser.add_argument(
        "--reactivate-problem",
        action="append",
        default=[],
        metavar="PROBLEM_ID",
        help="Schedule an earlier related problem for prerequisite/concept reinforcement.",
    )
    parser.add_argument(
        "--reactivation-reason",
        default="Related problem exposed a weak prerequisite concept.",
        help="Reason attached to any --reactivate-problem revision history event.",
    )
    parser.add_argument(
        "--deferred-learning",
        action="append",
        default=[],
        metavar="CATEGORY=DESCRIPTION",
        help=(
            "Create an open deferred learning for this session. Repeatable. "
            f"Categories: {', '.join(sorted(DEFERRED_LEARNING_CATEGORIES))}."
        ),
    )
    parser.add_argument(
        "--deferred-learning-priority",
        choices=("LOW", "MEDIUM", "HIGH"),
        default="MEDIUM",
        help="Priority for any created deferred learning. Defaults to MEDIUM.",
    )
    parser.add_argument(
        "--deferred-learning-skill",
        help="Skill id for any created deferred learning. Defaults to the problem's primary skill.",
    )
    parser.add_argument(
        "--resolve-deferred-learning",
        action="append",
        default=[],
        metavar="DL_ID",
        help="Resolve an existing deferred learning with evidence from this session. Repeatable.",
    )
    parser.add_argument(
        "--deferred-learning-evidence",
        help="Evidence used when resolving deferred learnings.",
    )
    parser.add_argument(
        "--note",
        action="append",
        default=[],
        help="Optional note to append to progress.notes.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output format.",
    )
    return parser


def parse_score_block(
    entries: list[str],
    required_dimensions: set[str],
    minimum: float,
    maximum: float,
    label: str,
) -> dict[str, float]:
    """Parse repeated DIMENSION=VALUE arguments into a validated score map."""

    parsed: dict[str, float] = {}
    for entry in entries:
        if "=" not in entry:
            raise RepositoryError(f"Invalid {label} entry `{entry}`. Use DIMENSION=VALUE.")
        dimension, raw_value = entry.split("=", 1)
        if dimension not in required_dimensions:
            raise RepositoryError(f"Unknown {label} dimension `{dimension}`.")
        try:
            value = float(raw_value)
        except ValueError as exc:
            raise RepositoryError(f"Invalid numeric value in {label} entry `{entry}`.") from exc
        if not minimum <= value <= maximum:
            raise RepositoryError(
                f"{label} `{dimension}` must be between {minimum:g} and {maximum:g}."
            )
        parsed[dimension] = int(value) if value.is_integer() else value
    if set(parsed) != required_dimensions:
        missing = sorted(required_dimensions - set(parsed))
        extra = sorted(set(parsed) - required_dimensions)
        details: list[str] = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unexpected " + ", ".join(extra))
        raise RepositoryError(f"Incomplete {label} block: {'; '.join(details)}.")
    return parsed


def render_text(payload: dict[str, Any]) -> str:
    """Render a human-readable update summary."""

    if payload["mode"] == "revision":
        revision = payload["revision"]
        lines = [
            f"Revision: {payload['problem_id']} / {payload['revision_result']}",
            f"Revision state: {revision['status']} stage {revision['stage']}",
            f"Next due: {revision['next_due'] or 'None'}",
            f"Next problem: {payload['next_problem'] or 'None'}",
        ]
        for entry in payload["reactivated_problems"]:
            lines.append(f"Reactivated: {entry['problem_id']} stage {entry['revision_stage']}")
        for entry in payload["deferred_learnings_created"]:
            lines.append(f"Deferred learning opened: {entry['id']} ({entry['category']})")
        for entry in payload["deferred_learnings_resolved"]:
            lines.append(f"Deferred learning resolved: {entry['id']} by {entry['resolved_by_problem']}")
        return "\n".join(lines)

    lines = [
        f"Completed: {payload['problem_id']}",
        f"Stage: {payload['stage_before']} -> {payload['stage_after']}",
        f"Revision state: {payload['revision']['status']} stage {payload['revision']['stage']}",
        f"Next due: {payload['revision']['next_due'] or 'None'}",
        f"Next problem: {payload['next_problem'] or 'None'}",
    ]
    for entry in payload["reactivated_problems"]:
        lines.append(f"Reactivated: {entry['problem_id']} stage {entry['revision_stage']}")
    for entry in payload["deferred_learnings_created"]:
        lines.append(f"Deferred learning opened: {entry['id']} ({entry['category']})")
    for entry in payload["deferred_learnings_resolved"]:
        lines.append(f"Deferred learning resolved: {entry['id']} by {entry['resolved_by_problem']}")
    return "\n".join(lines)


def parse_deferred_learning(entry: str) -> tuple[str, str]:
    """Parse CATEGORY=DESCRIPTION into a deferred learning tuple."""

    if "=" not in entry:
        raise RepositoryError(
            f"Invalid deferred learning `{entry}`. Use CATEGORY=DESCRIPTION."
        )
    category, description = entry.split("=", 1)
    return category.strip(), description.strip()


def fallback_algorithm_score(thinking_score: dict[str, float]) -> float:
    """Derive a backward-compatible 0-10 algorithm score from the old rubric."""

    dimensions = [
        "understanding",
        "examples",
        "brute_force",
        "pattern_detection",
        "algorithm_design",
        "complexity_analysis",
    ]
    values = [float(thinking_score.get(dimension, 0)) for dimension in dimensions]
    return round((sum(values) / len(values)) * 2.5, 2) if values else 0.0


def fallback_implementation_score(thinking_score: dict[str, float]) -> float:
    """Derive a backward-compatible 0-10 implementation score from the old rubric."""

    return round(float(thinking_score.get("implementation", 0)) * 2.5, 2)


def validate_zero_to_ten(value: float | None, label: str) -> float | None:
    """Validate an optional 0-10 score."""

    if value is None:
        return None
    if not 0 <= value <= 10:
        raise RepositoryError(f"`{label}` must be between 0 and 10.")
    return round(float(value), 2)


def update_implementation_engineering(progress: dict[str, Any], args: argparse.Namespace) -> None:
    """Append implementation engineering observations to top-level progress state."""

    section = progress.setdefault(
        "implementation_engineering",
        {
            "score": 0,
            "strengths": [],
            "weaknesses": [],
            "common_errors": [],
            "improvement_notes": [],
        },
    )
    score = validate_zero_to_ten(args.implementation_engineering_score, "--implementation-engineering-score")
    if score is not None:
        section["score"] = score
    section.setdefault("strengths", []).extend(
        item.strip() for item in args.implementation_strength if item.strip()
    )
    section.setdefault("weaknesses", []).extend(
        item.strip() for item in args.implementation_weakness if item.strip()
    )
    section.setdefault("common_errors", []).extend(
        item.strip() for item in args.implementation_error if item.strip()
    )
    section.setdefault("improvement_notes", []).extend(
        item.strip() for item in args.implementation_note if item.strip()
    )


def main() -> int:
    """Run the CLI."""

    parser = build_parser()
    args = parser.parse_args()
    try:
        state = load_repository_state(args.progress_file)
        problems = problem_lookup(state.curriculum)
        progress = state.progress
        completed_on = parse_iso_date(args.completed_at, "completed_at")

        problem_id = args.problem_id or current_problem_id(progress)
        if not problem_id:
            raise RepositoryError("No problem id provided and no active current problem is set.")
        if problem_id not in problems:
            raise RepositoryError(f"Unknown problem id `{problem_id}`.")
        deferred_learning_skill = args.deferred_learning_skill or problems[problem_id].get("primary_skill")
        if deferred_learning_skill not in state.skills.get("skills", {}):
            raise RepositoryError(f"Unknown deferred learning skill `{deferred_learning_skill}`.")
        if args.resolve_deferred_learning and not args.deferred_learning_evidence:
            raise RepositoryError(
                "`--resolve-deferred-learning` requires `--deferred-learning-evidence`."
            )

        is_revision = bool(args.revision_result)

        if not 0 <= args.hint_level_used <= 7:
            raise RepositoryError("`--hint-level-used` must be between 0 and 7.")
        if not 0 <= args.confidence_after <= 10:
            raise RepositoryError("`--confidence-after` must be between 0 and 10.")
        algorithm_thinking_score = validate_zero_to_ten(
            args.algorithm_thinking_score,
            "--algorithm-thinking-score",
        )
        implementation_engineering_score = validate_zero_to_ten(
            args.implementation_engineering_score,
            "--implementation-engineering-score",
        )

        if args.force_pass or args.force_pass_reason:
            if not is_revision or args.revision_result != "PASS":
                raise RepositoryError(
                    "`--force-pass` / `--force-pass-reason` only apply to `--revision-result PASS`."
                )
            if args.force_pass and not (args.force_pass_reason and args.force_pass_reason.strip()):
                raise RepositoryError("`--force-pass` requires `--force-pass-reason \"<why>\"`.")
            if args.force_pass_reason and not args.force_pass:
                raise RepositoryError("`--force-pass-reason` requires `--force-pass`.")

        thinking_dimensions = set(state.scoring.get("dimensions", {}))
        interview_dimensions = set(state.scoring.get("interview_dimensions", {}))
        revision_dimensions = set(state.scoring.get("revision_evaluation", {}).get("dimensions", {}))

        mentor_scores: dict[str, Any] | None = None
        if is_revision:
            # F8: revision mode does not need (and ignores) the solve rubric.
            thinking_score: dict[str, Any] = {}
            interview_score: dict[str, Any] = {}
        else:
            if args.time_taken_minutes is None:
                raise RepositoryError("`--time-taken-minutes` is required for a new solve.")
            if args.time_taken_minutes <= 0:
                raise RepositoryError("`--time-taken-minutes` must be greater than zero.")
            if args.confidence_before is None:
                raise RepositoryError("`--confidence-before` is required for a new solve.")
            if not 0 <= args.confidence_before <= 10:
                raise RepositoryError("`--confidence-before` must be between 0 and 10.")
            if not args.thinking_breakthrough or not args.thinking_breakthrough.strip():
                raise RepositoryError("`--thinking-breakthrough` is required for a new solve and must not be empty.")
            if not args.main_mistake or not args.main_mistake.strip():
                raise RepositoryError("`--main-mistake` is required for a new solve and must not be empty.")

            thinking_score = parse_score_block(
                entries=args.thinking_score,
                required_dimensions=thinking_dimensions,
                minimum=float(state.scoring["scale"]["minimum"]),
                maximum=float(state.scoring["scale"]["maximum"]),
                label="thinking score",
            )
            interview_score = parse_score_block(
                entries=args.interview_score,
                required_dimensions=interview_dimensions,
                minimum=float(state.scoring["interview_scale"]["minimum"]),
                maximum=float(state.scoring["interview_scale"]["maximum"]),
                label="interview score",
            )
            if algorithm_thinking_score is None:
                algorithm_thinking_score = fallback_algorithm_score(thinking_score)
            if implementation_engineering_score is None:
                implementation_engineering_score = fallback_implementation_score(thinking_score)

            # F7: mentor_scores is entirely optional (absent -> no key written,
            # backward compat). But if the mentor graded ANY dimension, both
            # sub-blocks must be complete, mirroring the self-report rule.
            if args.mentor_thinking_score or args.mentor_interview_score:
                mentor_thinking_score = parse_score_block(
                    entries=args.mentor_thinking_score,
                    required_dimensions=thinking_dimensions,
                    minimum=float(state.scoring["scale"]["minimum"]),
                    maximum=float(state.scoring["scale"]["maximum"]),
                    label="mentor thinking score",
                )
                mentor_interview_score = parse_score_block(
                    entries=args.mentor_interview_score,
                    required_dimensions=interview_dimensions,
                    minimum=float(state.scoring["interview_scale"]["minimum"]),
                    maximum=float(state.scoring["interview_scale"]["maximum"]),
                    label="mentor interview score",
                )
                mentor_scores = {
                    "thinking_score": mentor_thinking_score,
                    "interview_score": mentor_interview_score,
                }

        revision_score: dict[str, Any] = {}
        if is_revision:
            revision_score = parse_score_block(
                entries=args.revision_score,
                required_dimensions=revision_dimensions,
                minimum=float(state.scoring["revision_evaluation"]["scale"]["minimum"]),
                maximum=float(state.scoring["revision_evaluation"]["scale"]["maximum"]),
                label="revision score",
            )
            if args.revision_result == "PASS":
                pass_minimum = float(
                    state.scoring.get("revision_evaluation", {}).get("scale", {}).get("pass_minimum", 0)
                )
                avg_revision_score = sum(revision_score.values()) / len(revision_score)
                if avg_revision_score < pass_minimum and not args.force_pass:
                    raise RepositoryError(
                        f"Revision scores average {avg_revision_score:.2f}, below pass_minimum "
                        f"{pass_minimum:g}; scores say FAIL. Pass explicitly with `--force-pass` "
                        "and `--force-pass-reason \"<why>\"`, or record `--revision-result FAIL`."
                    )

        stage_before = str(progress.get("current_stage"))
        prior_completed = completed_problem_ids(progress)
        latest_by_problem = latest_records_by_problem(progress)

        if problem_id in prior_completed and not args.revision_result:
            raise RepositoryError(
                f"`{problem_id}` is already completed. Use `--revision-result PASS|FAIL` "
                "to record an active-recall revision."
            )
        if problem_id not in prior_completed and args.revision_result:
            raise RepositoryError("`--revision-result` can only be used for completed problems.")

        revision_event = None
        if args.revision_result:
            target_record = latest_by_problem[problem_id]
            revision_event = apply_revision_result(
                record=target_record,
                result=args.revision_result,
                completed_on=completed_on,
                confidence=args.confidence_after,
                hint_level=args.hint_level_used,
                revision_score=revision_score,
                force_pass_reason=args.force_pass_reason if args.force_pass else None,
            )
            # F8: algorithm/implementation scores are no longer derived from a
            # forced solve rubric in revision mode; only record them if the
            # caller explicitly passed one of the independent score flags.
            if algorithm_thinking_score is not None:
                revision_event["algorithm_thinking_score"] = algorithm_thinking_score
            if implementation_engineering_score is not None:
                revision_event["implementation_engineering_score"] = implementation_engineering_score
            solve_mode = "revision"
        else:
            solve_mode = "new_problem"

        override_note = None
        if solve_mode == "new_problem":
            overdue = revision_due_entries(progress, completed_on)
            if overdue:
                overdue_ids = sorted({str(entry["problem"]) for entry in overdue})
                if not args.override_revisions:
                    raise RepositoryError(
                        "Revision-first violation: overdue revisions must be recorded before "
                        f"a new solve as of {format_iso_date(completed_on)}: "
                        f"{', '.join(overdue_ids)}. Record those revisions first, or pass "
                        "--override-revisions to bypass (logged on the new record)."
                    )
                override_note = (
                    "Recorded new solve via --override-revisions while overdue: "
                    f"{', '.join(overdue_ids)}."
                )

        # F9: "solved means it ran." A NEW solve is gated on a runnable
        # solutions/<PROBLEM-ID>.py (learner's solution + embedded asserts).
        # Runs AFTER the F3 revision gate (revisions are higher priority) and
        # BEFORE any state mutation/write. Revision mode is never gated.
        no_code_note = None
        if solve_mode == "new_problem":
            if args.no_code:
                no_code_note = (
                    "Recorded via --no-code (whiteboard-style session); no solution "
                    "file executed."
                )
            else:
                solutions_dir = Path(args.solutions_dir) if args.solutions_dir else SOLUTIONS_DIR
                solution_path = solution_path_for(problem_id, solutions_dir)
                timeout_seconds = (
                    args.code_check_timeout
                    if args.code_check_timeout is not None
                    else DEFAULT_TIMEOUT_SECONDS
                )
                check = run_solution_file(solution_path, timeout_seconds=timeout_seconds)
                if not check.passed:
                    raise RepositoryError(
                        f"Code-execution gate failed for `{problem_id}`: {check.message} "
                        f"Expected a runnable solution at {solution_path} with 3-5 embedded "
                        "asserts (see solutions/README.md). Fix it and rerun, or pass "
                        "--no-code for a whiteboard-style session."
                    )

        if not args.revision_result:
            completion_record: dict[str, Any] = {
                "problem_id": problem_id,
                "completed_at": format_iso_date(completed_on),
                "time_taken_minutes": args.time_taken_minutes,
                "hint_level_used": args.hint_level_used,
                "confidence_before": args.confidence_before,
                "confidence_after": args.confidence_after,
                "thinking_breakthrough": args.thinking_breakthrough.strip(),
                "main_mistake": args.main_mistake.strip(),
                "thinking_score": thinking_score,
                "algorithm_thinking_score": algorithm_thinking_score,
                "implementation_engineering_score": implementation_engineering_score,
                "interview_score": interview_score,
                "revision": initial_revision_state(completed_on),
            }
            if mentor_scores is not None:
                completion_record["mentor_scores"] = mentor_scores
            solve_notes = [note for note in (override_note, no_code_note) if note]
            if solve_notes:
                completion_record["notes"] = solve_notes
            progress.setdefault("completed", []).append(completion_record)
        else:
            completion_record = latest_by_problem[problem_id]

        reactivated: list[dict[str, Any]] = []
        for reactivation_id in args.reactivate_problem:
            if reactivation_id not in problems:
                raise RepositoryError(f"Unknown reactivation problem id `{reactivation_id}`.")
            reactivation_record = latest_records_by_problem(progress).get(reactivation_id)
            if reactivation_record is None:
                raise RepositoryError(
                    f"`--reactivate-problem {reactivation_id}` requires a completed problem."
                )
            reactivation_event = reactivate_revision(
                record=reactivation_record,
                activated_on=completed_on,
                reason=args.reactivation_reason,
            )
            reactivated.append(
                {
                    "problem_id": reactivation_id,
                    "revision_stage": reactivation_event["stage"],
                    "reason": args.reactivation_reason,
                }
            )

        deferred_created: list[dict[str, Any]] = []
        origin_revision_stage = (
            revision_event["attempted_stage"]
            if isinstance(revision_event, dict)
            else None
        )
        for raw_learning in args.deferred_learning:
            category, description = parse_deferred_learning(raw_learning)
            deferred_created.append(
                create_deferred_learning(
                    progress,
                    origin_problem=problem_id,
                    origin_revision_stage=origin_revision_stage,
                    skill=str(deferred_learning_skill),
                    category=category,
                    description=description,
                    priority=args.deferred_learning_priority,
                    created_on=completed_on,
                )
            )

        deferred_resolved: list[dict[str, Any]] = []
        for learning_id in args.resolve_deferred_learning:
            deferred_resolved.append(
                resolve_deferred_learning(
                    progress,
                    learning_id=learning_id,
                    resolved_on=completed_on,
                    resolved_by_problem=problem_id,
                    evidence=args.deferred_learning_evidence or "",
                )
            )

        if args.note:
            progress.setdefault("notes", []).extend(note for note in args.note if note.strip())
        update_implementation_engineering(progress, args)

        progress["last_updated"] = format_iso_date(completed_on)
        normalize_progress(state, progress)
        stage_after = str(progress.get("current_stage"))

        selection = select_next_problem(state, on_date=completed_on)
        next_problem_id = selection.problem["id"] if selection.problem else None
        progress["current_problem"] = next_problem_id

        append_history_event(
            progress,
            {
                "timestamp": format_iso_date(completed_on),
                "event": "revision_recorded" if args.revision_result else "problem_completed",
                "problem_id": problem_id,
                "mode": solve_mode,
                "stage_before": stage_before,
                "stage_after": stage_after,
                "revision_result": args.revision_result,
                "revision_stage": (
                    revision_event["stage"] if isinstance(revision_event, dict) else 0
                ),
                "revision_status": completion_record["revision"]["status"],
                "next_due": completion_record["revision"]["next_due"],
                "reactivated_problems": reactivated,
                "deferred_learnings_created": [entry["id"] for entry in deferred_created],
                "deferred_learnings_resolved": [entry["id"] for entry in deferred_resolved],
                "next_problem": next_problem_id,
            },
        )
        if stage_before != stage_after:
            append_history_event(
                progress,
                {
                    "timestamp": format_iso_date(completed_on),
                    "event": "stage_changed",
                    "problem_id": problem_id,
                    "from_stage": stage_before,
                    "to_stage": stage_after,
                },
            )

        save_json_file(state.progress_path, progress)
        payload = {
            "mode": solve_mode,
            "problem_id": problem_id,
            "revision_result": args.revision_result,
            "revision": completion_record["revision"],
            "reactivated_problems": reactivated,
            "deferred_learnings_created": deferred_created,
            "deferred_learnings_resolved": deferred_resolved,
            "stage_before": stage_before,
            "stage_after": stage_after,
            "next_problem": next_problem_id,
            "selection_mode": selection.mode,
            "selection_reason": selection.reason,
            "progress_file": str(state.progress_path),
        }
        if args.format == "json":
            print(json.dumps(payload, indent=2))
        else:
            print(render_text(payload))
        return 0
    except RepositoryError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
