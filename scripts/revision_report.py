#!/usr/bin/env python3
"""Report due revisions and progress quality trends."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from typing import Any

from _shared import (
    RepositoryError,
    confidence_trend,
    interview_trend,
    load_repository_state,
    open_revision_entries,
    quarterly_maintenance_entries,
    revision_due_entries,
    parse_iso_date,
    problem_lookup,
    weakest_skills,
)


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Summarize active-recall revisions, maintenance reviews, weakest solved skills, "
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
        help="Only print today's and overdue revision entries.",
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
        for entry in revision_due_entries(state.progress, state_date)
        if parse_iso_date(entry["date"], "revision.date") == state_date
    ]
    overdue = [
        entry
        for entry in all_open
        if parse_iso_date(entry["date"], "revision.date") < state_date
    ]
    maintenance = quarterly_maintenance_entries(state.progress, state_date)

    def enrich(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                **entry,
                "title": problems[entry["problem"]]["title"],
                "skill": problems[entry["problem"]]["primary_skill"],
                "curriculum_stage": problems[entry["problem"]]["stage"],
                "revision_stage": entry["stage"],
            }
            for entry in sorted(
                entries,
                key=lambda item: (
                    {"reactivation": 0, "revision": 1, "quarterly_maintenance": 2}.get(
                        str(item.get("kind")),
                        3,
                    ),
                    item["date"],
                    int(item.get("stage", 0)),
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
        "quarterly_maintenance": enrich(maintenance),
        "weakest_skills": weakest_skills(state),
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
                f"- {entry['problem']} | {entry['title']} | {entry['skill']} | "
                f"{entry.get('kind', 'revision')} | {entry['status']} stage {entry['revision_stage']} | "
                f"{entry['reason']}"
            )
    else:
        lines.append("- None")
    lines.append("")

    lines.append("Overdue Revisions")
    if payload["overdue_revisions"]:
        for entry in payload["overdue_revisions"]:
            lines.append(
                f"- {entry['problem']} | {entry['date']} | {entry.get('kind', 'revision')} | "
                f"{entry['status']} stage {entry['revision_stage']} | {entry['reason']}"
            )
    else:
        lines.append("- None")
    lines.append("")

    lines.append("Quarterly Maintenance")
    if payload["quarterly_maintenance"]:
        for entry in payload["quarterly_maintenance"]:
            lines.append(
                f"- {entry['problem']} | {entry['title']} | {entry['skill']} | quick recall"
            )
    else:
        lines.append("- None")
    lines.append("")

    if not today_only:
        lines.append("Weakest Modules")
        if payload["weakest_skills"]:
            for skill in payload["weakest_skills"]:
                lines.append(
                    f"- {skill['skill_name']} | score {skill['average_weighted_thinking_score']:.2f} | "
                    f"solved {skill['solved_problems']}"
                )
        else:
            lines.append("- No solved skills yet")
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
