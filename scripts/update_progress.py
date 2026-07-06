#!/usr/bin/env python3
"""Update live progress after a problem solve or revision session."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from typing import Any

from _shared import (
    RepositoryError,
    append_history_event,
    close_open_revision_entries,
    completed_problem_ids,
    current_problem_id,
    format_iso_date,
    load_repository_state,
    normalize_progress,
    parse_iso_date,
    problem_lookup,
    revision_decision,
    save_json_file,
    select_next_problem,
)


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Mark a problem session complete, update progress summaries, rotate the revision "
            "schedule, and choose the next problem automatically."
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
            "--interview-score understanding=7 --interview-score communication=8 "
            "--interview-score algorithm=7 --interview-score coding=7 --interview-score complexity=8"
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
        required=True,
        type=int,
        help="Minutes spent in the session.",
    )
    parser.add_argument(
        "--hint-level-used",
        required=True,
        type=int,
        help="Hint level used during the session. See progress/scoring.json.",
    )
    parser.add_argument(
        "--confidence-before",
        required=True,
        type=int,
        help="Confidence before solving on a 0-10 scale.",
    )
    parser.add_argument(
        "--confidence-after",
        required=True,
        type=int,
        help="Confidence after solving on a 0-10 scale.",
    )
    parser.add_argument(
        "--thinking-breakthrough",
        required=True,
        help="Short description of what unlocked the solve.",
    )
    parser.add_argument(
        "--main-mistake",
        required=True,
        help="Primary mistake or trap encountered during the solve.",
    )
    parser.add_argument(
        "--thinking-score",
        action="append",
        default=[],
        metavar="DIMENSION=VALUE",
        help="Thinking-rubric score entry. Repeat once per dimension.",
    )
    parser.add_argument(
        "--interview-score",
        action="append",
        default=[],
        metavar="DIMENSION=VALUE",
        help="Interview-rubric score entry. Repeat once per dimension.",
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

    lines = [
        f"Completed: {payload['completed_record']['problem_id']}",
        f"Stage: {payload['stage_before']} -> {payload['stage_after']}",
        "Scheduled revision: "
        f"{payload['scheduled_revision']['date']} / "
        f"{payload['scheduled_revision']['priority']}",
        f"Next problem: {payload['next_problem'] or 'None'}",
    ]
    return "\n".join(lines)


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

        if args.time_taken_minutes <= 0:
            raise RepositoryError("`--time-taken-minutes` must be greater than zero.")
        if not 0 <= args.hint_level_used <= 7:
            raise RepositoryError("`--hint-level-used` must be between 0 and 7.")
        if not 0 <= args.confidence_before <= 10 or not 0 <= args.confidence_after <= 10:
            raise RepositoryError("Confidence values must be between 0 and 10.")
        if not args.thinking_breakthrough.strip():
            raise RepositoryError("`--thinking-breakthrough` must not be empty.")
        if not args.main_mistake.strip():
            raise RepositoryError("`--main-mistake` must not be empty.")

        thinking_dimensions = set(state.scoring.get("dimensions", {}))
        interview_dimensions = set(state.scoring.get("interview_dimensions", {}))
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

        stage_before = str(progress.get("current_stage"))
        prior_completed = completed_problem_ids(progress)
        solve_mode = "revision" if problem_id in prior_completed else "new_problem"
        closed_revisions = close_open_revision_entries(progress, problem_id)

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
            "interview_score": interview_score,
            "next_revision_date": "",
        }

        priority, next_revision_date, reason = revision_decision(
            record=completion_record,
            scoring=state.scoring,
            completed_on=completed_on,
        )
        completion_record["next_revision_date"] = next_revision_date

        revision_entry = {
            "problem": problem_id,
            "date": next_revision_date,
            "reason": reason,
            "priority": priority,
            "status": "scheduled",
        }

        progress.setdefault("completed", []).append(completion_record)
        progress.setdefault("revision_schedule", []).append(revision_entry)
        if args.note:
            progress.setdefault("notes", []).extend(note for note in args.note if note.strip())

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
                "event": "problem_completed",
                "problem_id": problem_id,
                "mode": solve_mode,
                "stage_before": stage_before,
                "stage_after": stage_after,
                "closed_revisions": closed_revisions,
                "scheduled_revision_date": next_revision_date,
                "scheduled_revision_priority": priority,
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
            "completed_record": completion_record,
            "scheduled_revision": revision_entry,
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
