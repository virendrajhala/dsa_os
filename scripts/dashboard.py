#!/usr/bin/env python3
"""Render a concise console dashboard for the current DSA_OS state."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from statistics import mean
from typing import Any

from _shared import (
    RepositoryError,
    THINKING_DIMENSION_LABELS,
    completed_problem_ids,
    confidence_trend,
    current_problem_id,
    load_repository_state,
    open_revision_entries_due_on_or_before,
    problem_lookup,
    select_next_problem,
)


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(
        description="Render a console dashboard summarizing stage, revisions, confidence, and next work."
    )
    parser.add_argument(
        "--progress-file",
        help="Override the progress file path. Defaults to progress/progress.json.",
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Reference date in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser


def build_payload(reference_date: date, state: Any) -> dict[str, Any]:
    """Build the dashboard payload."""

    problems = problem_lookup(state.curriculum)
    selection = select_next_problem(state, on_date=reference_date)
    completed_ids = completed_problem_ids(state.progress)
    completed_records = [
        record for record in state.progress.get("completed", []) if isinstance(record, dict)
    ]
    current_problem = current_problem_id(state.progress)
    active_problem = problems.get(current_problem) if current_problem else None
    next_problem = selection.problem
    current_skill = None
    if active_problem is not None:
        current_skill = active_problem["primary_skill"]
    elif next_problem is not None:
        current_skill = next_problem["primary_skill"]

    thinking_dimensions = state.progress.get("scores", {}).get("averages", {}).get(
        "thinking_dimensions",
        {},
    )
    strongest_skill = None
    weakest_skill = None
    if isinstance(thinking_dimensions, dict) and thinking_dimensions and completed_ids:
        strongest_dimension = max(thinking_dimensions.items(), key=lambda item: item[1])[0]
        weakest_dimension = min(thinking_dimensions.items(), key=lambda item: item[1])[0]
        strongest_skill = THINKING_DIMENSION_LABELS.get(strongest_dimension, strongest_dimension)
        weakest_skill = THINKING_DIMENSION_LABELS.get(weakest_dimension, weakest_dimension)

    confidence = confidence_trend(completed_records)
    current_confidence = (
        round(mean(confidence["recent_values"]), 2) if confidence["recent_values"] else 0.0
    )
    due_revisions = open_revision_entries_due_on_or_before(state.progress, reference_date)

    return {
        "current_stage": state.progress.get("current_stage"),
        "current_skill": current_skill,
        "completed": len(completed_ids),
        "total_problems": len(state.curriculum["problems"]),
        "revision_due": len(due_revisions),
        "current_confidence": current_confidence,
        "weakest_skill": weakest_skill,
        "strongest_skill": strongest_skill,
        "todays_problem": next_problem["id"] if next_problem else None,
        "todays_problem_title": next_problem["title"] if next_problem else None,
        "selection_mode": selection.mode,
        "selection_reason": selection.reason,
    }


def render_text(payload: dict[str, Any]) -> str:
    """Render the dashboard as console text."""

    lines = [
        "------------------------------------",
        "",
        f"Current Stage      {payload['current_stage']}",
        f"Current Skill      {payload['current_skill'] or 'None'}",
        f"Completed          {payload['completed']} / {payload['total_problems']}",
        f"Revision Due       {payload['revision_due']}",
        f"Current Confidence {payload['current_confidence']:.2f}",
        f"Weakest Skill      {payload['weakest_skill'] or 'None'}",
        f"Strongest Skill    {payload['strongest_skill'] or 'None'}",
        f"Today's Problem    {payload['todays_problem'] or 'None'}",
        "",
        "------------------------------------",
    ]
    return "\n".join(lines)


def main() -> int:
    """Run the CLI."""

    parser = build_parser()
    args = parser.parse_args()
    try:
        state = load_repository_state(args.progress_file)
        reference_date = date.fromisoformat(args.date)
        payload = build_payload(reference_date, state)
        if args.format == "json":
            print(json.dumps(payload, indent=2))
        else:
            print(render_text(payload))
        return 0
    except ValueError:
        print("Invalid `--date`. Expected YYYY-MM-DD.", file=sys.stderr)
        return 2
    except RepositoryError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
