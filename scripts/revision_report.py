#!/usr/bin/env python3
"""Report due revisions and progress quality trends."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from typing import Any

from _shared import (
    REVISION_PRIORITY_ORDER,
    RepositoryError,
    confidence_trend,
    interview_trend,
    load_repository_state,
    open_revision_entries,
    parse_iso_date,
    problem_lookup,
    weakest_modules,
)


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Summarize today's revisions, overdue revisions, weakest solved modules, "
            "confidence trend, and interview-score trend."
        )
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
        "--today-only",
        action="store_true",
        help="Only print today's and overdue revision schedule entries.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="text",
        help="Output format.",
    )
    return parser


def build_payload(state_date: date, state: Any) -> dict[str, Any]:
    """Build the report payload."""

    problems = problem_lookup(state.curriculum)
    all_open = open_revision_entries(state.progress)
    todays = [
        entry
        for entry in all_open
        if parse_iso_date(entry["date"], "revision_schedule.date") == state_date
    ]
    overdue = [
        entry
        for entry in all_open
        if parse_iso_date(entry["date"], "revision_schedule.date") < state_date
    ]

    def enrich(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                **entry,
                "title": problems[entry["problem"]]["title"],
                "module": problems[entry["problem"]]["module"],
                "stage": problems[entry["problem"]]["stage"],
            }
            for entry in sorted(
                entries,
                key=lambda item: (
                    item["date"],
                    REVISION_PRIORITY_ORDER.get(item["priority"], 999),
                    item["problem"],
                ),
            )
        ]

    completed = [
        record
        for record in state.progress.get("completed", [])
        if isinstance(record, dict)
    ]
    return {
        "date": state_date.isoformat(),
        "todays_revisions": enrich(todays),
        "overdue_revisions": enrich(overdue),
        "weakest_modules": weakest_modules(state),
        "confidence_trend": confidence_trend(completed),
        "interview_score_trend": interview_trend(completed),
    }


def render_text(payload: dict[str, Any], today_only: bool) -> str:
    """Render the report as console text."""

    lines = [f"Revision Report: {payload['date']}", ""]
    lines.append("Today's Revisions")
    if payload["todays_revisions"]:
        for entry in payload["todays_revisions"]:
            lines.append(
                f"- {entry['problem']} | {entry['title']} | {entry['module']} | "
                f"{entry['priority']} | {entry['reason']}"
            )
    else:
        lines.append("- None")
    lines.append("")

    lines.append("Overdue Revisions")
    if payload["overdue_revisions"]:
        for entry in payload["overdue_revisions"]:
            lines.append(
                f"- {entry['problem']} | {entry['date']} | {entry['priority']} | {entry['reason']}"
            )
    else:
        lines.append("- None")
    lines.append("")

    if not today_only:
        lines.append("Weakest Modules")
        if payload["weakest_modules"]:
            for module in payload["weakest_modules"]:
                lines.append(
                    f"- {module['module']} | score {module['average_weighted_thinking_score']:.2f} | "
                    f"solved {module['solved_problems']}"
                )
        else:
            lines.append("- No solved modules yet")
        lines.append("")

        confidence = payload["confidence_trend"]
        lines.append(
            "Confidence Trend\n"
            f"- Recent average: {confidence['recent_average']:.2f}\n"
            f"- Previous average: {confidence['previous_average']:.2f}\n"
            f"- Direction: {confidence['direction']} ({confidence['delta']:+.2f})"
        )
        lines.append("")

        interview = payload["interview_score_trend"]
        lines.append(
            "Interview Score Trend\n"
            f"- Recent average: {interview['recent_average']:.2f}\n"
            f"- Previous average: {interview['previous_average']:.2f}\n"
            f"- Direction: {interview['direction']} ({interview['delta']:+.2f})"
        )

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
            print(render_text(payload, args.today_only))
        return 0
    except ValueError:
        print("Invalid `--date`. Expected YYYY-MM-DD.", file=sys.stderr)
        return 2
    except RepositoryError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
