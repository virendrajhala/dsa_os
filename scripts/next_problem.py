#!/usr/bin/env python3
"""Select the next dependency-safe problem or revision to work on."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from typing import Any

from _shared import RepositoryError, SelectionResult, load_repository_state, select_next_problem


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Choose the next problem using revision urgency, current skill continuity, "
            "current stage focus, and dependency-safe curriculum order."
        )
    )
    parser.add_argument(
        "--progress-file",
        help="Override the progress file path. Defaults to progress/progress.json.",
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Evaluate due revisions and unlocked work for this date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output format.",
    )
    return parser


def selection_payload(selection: SelectionResult) -> dict[str, Any]:
    """Convert a selection result into a serializable payload."""

    payload: dict[str, Any] = {
        "mode": selection.mode,
        "reason": selection.reason,
        "problem": selection.problem,
    }
    if selection.suggested_stage is not None:
        payload["suggested_stage"] = selection.suggested_stage
    if selection.revision_entry is not None:
        payload["revision_entry"] = selection.revision_entry
    return payload


def render_text(selection: SelectionResult) -> str:
    """Render a human-readable selection summary."""

    if selection.problem is None:
        return "No unlocked work remains."

    lines = [
        f"Mode: {selection.mode}",
        f"Reason: {selection.reason}",
        f"Problem: {selection.problem['id']} - {selection.problem['title']}",
        f"Skill: {selection.problem['primary_skill']}",
        f"Stage: {selection.problem['stage']}",
    ]
    if selection.revision_entry is not None:
        lines.append(
            "Revision: "
            f"{selection.revision_entry['date']} / "
            f"{selection.revision_entry.get('kind', 'revision')} / "
            f"stage {selection.revision_entry['stage']} / "
            f"{selection.revision_entry['status']}"
        )
    return "\n".join(lines)


def main() -> int:
    """Run the CLI."""

    parser = build_parser()
    args = parser.parse_args()
    try:
        state = load_repository_state(args.progress_file)
        selection = select_next_problem(
            state=state,
            on_date=date.fromisoformat(args.date),
        )
        if args.format == "json":
            print(json.dumps(selection_payload(selection), indent=2))
        else:
            print(render_text(selection))
        return 0
    except ValueError:
        print("Invalid `--date`. Expected YYYY-MM-DD.", file=sys.stderr)
        return 2
    except RepositoryError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
