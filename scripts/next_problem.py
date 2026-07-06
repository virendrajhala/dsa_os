#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CURRICULUM_PATH = ROOT / "curriculum" / "curriculum.json"
GRAPH_PATH = ROOT / "curriculum" / "dependency_graph.json"
STAGES_PATH = ROOT / "curriculum" / "stages.json"
PROGRESS_PATH = ROOT / "progress" / "progress_template.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def queue_entry_id(entry: object) -> str | None:
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        candidate = entry.get("id")
        if isinstance(candidate, str):
            return candidate
    return None


def main() -> int:
    curriculum = load_json(CURRICULUM_PATH)
    graph = load_json(GRAPH_PATH)
    stages = load_json(STAGES_PATH)
    progress = load_json(PROGRESS_PATH)

    problems = curriculum["problems"]
    stage_order = stages["stage_order"]
    stage_defs = stages["stages"]
    module_order = graph["module_order"]
    modules = graph["modules"]

    problems_by_id = {problem["id"]: problem for problem in problems}
    curriculum_order = {problem["id"]: index for index, problem in enumerate(problems)}
    completed = set(progress.get("completed", []))
    revision_queue = progress.get("revision_queue", [])
    current_stage = progress.get("current_stage", stage_order[0])
    current_problem = progress.get("current_problem")

    for entry in revision_queue:
        entry_id = queue_entry_id(entry)
        if entry_id and entry_id in problems_by_id and entry_id not in completed:
            selected = problems_by_id[entry_id]
            print(
                json.dumps(
                    {
                        "mode": "revision_queue",
                        "reason": "Revision item has priority over new work.",
                        "problem": selected,
                    },
                    indent=2,
                )
            )
            return 0

    def unlocked(problem: dict) -> bool:
        return all(dep in completed for dep in problem["dependency"])

    incomplete = [problem for problem in problems if problem["id"] not in completed]
    unlocked_incomplete = [problem for problem in incomplete if unlocked(problem)]

    if current_problem and current_problem in problems_by_id and current_problem not in completed:
        candidate = problems_by_id[current_problem]
        if unlocked(candidate):
            print(
                json.dumps(
                    {
                        "mode": "resume_current_problem",
                        "reason": "Current problem is still active and unlocked.",
                        "problem": candidate,
                    },
                    indent=2,
                )
            )
            return 0

    module_name_to_code = {module["name"]: code for code, module in modules.items()}

    def sort_key(problem: dict) -> tuple[int, int]:
        module_code = module_name_to_code[problem["module"]]
        return (module_order.index(module_code), curriculum_order[problem["id"]])

    current_stage_index = stage_order.index(current_stage) if current_stage in stage_order else 0

    for stage_name in stage_order[current_stage_index:]:
        stage_modules = stage_defs[stage_name]["modules"]
        stage_candidates = [
            problem
            for problem in unlocked_incomplete
            if module_name_to_code[problem["module"]] in stage_modules
        ]
        if not stage_candidates:
            continue

        if current_problem and current_problem in problems_by_id:
            current_module_code = current_problem.split("-")[0]
            same_module = [
                problem
                for problem in stage_candidates
                if module_name_to_code[problem["module"]] == current_module_code
            ]
            if same_module:
                chosen = sorted(same_module, key=sort_key)[0]
                print(
                    json.dumps(
                        {
                            "mode": "continue_module",
                            "reason": "Continuing within the current module preserves context.",
                            "problem": chosen,
                            "suggested_stage": stage_name,
                        },
                        indent=2,
                    )
                )
                return 0

        chosen = sorted(stage_candidates, key=sort_key)[0]
        print(
            json.dumps(
                {
                    "mode": "next_unlocked",
                    "reason": "First unlocked problem in the active stage order.",
                    "problem": chosen,
                    "suggested_stage": stage_name,
                },
                indent=2,
            )
        )
        return 0

    print(
        json.dumps(
            {
                "mode": "complete",
                "reason": "No unlocked incomplete problems remain.",
                "problem": None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
