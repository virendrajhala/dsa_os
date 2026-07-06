#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CURRICULUM_PATH = ROOT / "curriculum" / "curriculum.json"
GRAPH_PATH = ROOT / "curriculum" / "dependency_graph.json"
STAGES_PATH = ROOT / "curriculum" / "stages.json"
PROGRESS_PATH = ROOT / "progress" / "progress_template.json"
SCORING_PATH = ROOT / "progress" / "scoring.json"

REQUIRED_PROBLEM_FIELDS = {
    "id",
    "original_number",
    "title",
    "difficulty",
    "section",
    "pattern",
    "stage",
    "module",
    "dependency",
    "status",
    "revision_count",
    "estimated_minutes",
    "interview_frequency",
    "notes",
}

ID_RE = re.compile(r"^[A-Z]{2,3}-\d{3}$")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise SystemExit(f"Missing required file: {path}")


def normalize_problem_id(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        candidate = value.get("id")
        if isinstance(candidate, str):
            return candidate
    return None


def main() -> int:
    curriculum = load_json(CURRICULUM_PATH)
    graph = load_json(GRAPH_PATH)
    stages = load_json(STAGES_PATH)
    progress = load_json(PROGRESS_PATH)
    scoring = load_json(SCORING_PATH)

    errors: list[str] = []
    warnings: list[str] = []

    problems = curriculum.get("problems")
    if not isinstance(problems, list):
        errors.append("curriculum.json: `problems` must be a list.")
        problems = []

    module_order = graph.get("module_order")
    modules = graph.get("modules")
    stage_order = stages.get("stage_order")
    stage_defs = stages.get("stages")

    if not isinstance(module_order, list) or not isinstance(modules, dict):
        errors.append("dependency_graph.json must contain `module_order` and `modules`.")
        module_order = []
        modules = {}
    if not isinstance(stage_order, list) or not isinstance(stage_defs, dict):
        errors.append("stages.json must contain `stage_order` and `stages`.")
        stage_order = []
        stage_defs = {}

    problem_ids: list[str] = []
    original_numbers: list[int] = []
    module_name_to_code: dict[str, str] = {}
    expected_stage_by_module_name: dict[str, str] = {}

    for code in module_order:
        module = modules.get(code, {})
        name = module.get("name")
        stage = module.get("stage")
        if isinstance(name, str):
            module_name_to_code[name] = code
            if isinstance(stage, str):
                expected_stage_by_module_name[name] = stage

    for index, problem in enumerate(problems, start=1):
        if not isinstance(problem, dict):
            errors.append(f"Problem #{index}: entry must be an object.")
            continue

        missing_fields = sorted(REQUIRED_PROBLEM_FIELDS - problem.keys())
        if missing_fields:
            errors.append(
                f"Problem #{index}: missing required fields: {', '.join(missing_fields)}."
            )
            continue

        problem_id = problem["id"]
        if not isinstance(problem_id, str) or not ID_RE.match(problem_id):
            errors.append(f"Problem #{index}: invalid id format `{problem_id}`.")
        else:
            problem_ids.append(problem_id)

        original_number = problem["original_number"]
        if not isinstance(original_number, int):
            errors.append(f"{problem_id}: `original_number` must be an integer.")
        else:
            original_numbers.append(original_number)

        if problem["difficulty"] not in {"Easy", "Medium", "Hard"}:
            errors.append(f"{problem_id}: invalid difficulty `{problem['difficulty']}`.")

        if not isinstance(problem["dependency"], list):
            errors.append(f"{problem_id}: `dependency` must be a list.")

        module_name = problem["module"]
        stage_name = problem["stage"]
        if module_name not in module_name_to_code:
            errors.append(f"{problem_id}: unknown module `{module_name}`.")
        else:
            expected_stage = expected_stage_by_module_name[module_name]
            if stage_name != expected_stage:
                errors.append(
                    f"{problem_id}: stage `{stage_name}` does not match module stage `{expected_stage}`."
                )

        if stage_name not in stage_defs:
            errors.append(f"{problem_id}: unknown stage `{stage_name}`.")

    id_counter = Counter(problem_ids)
    duplicate_ids = sorted(problem_id for problem_id, count in id_counter.items() if count > 1)
    if duplicate_ids:
        errors.append(f"Duplicate IDs found: {', '.join(duplicate_ids)}.")

    if len(problems) != 507:
        errors.append(f"Expected 507 problems, found {len(problems)}.")

    original_counter = Counter(original_numbers)
    duplicate_originals = sorted(
        number for number, count in original_counter.items() if count > 1
    )
    if duplicate_originals:
        errors.append(
            f"Duplicate original numbers found: {', '.join(map(str, duplicate_originals[:20]))}."
        )

    missing_originals = [number for number in range(1, 508) if number not in original_counter]
    if missing_originals:
        errors.append(
            f"Missing original numbers: {', '.join(map(str, missing_originals[:20]))}."
        )

    if len(problem_ids) != len(set(problem_ids)):
        warnings.append("ID uniqueness warning already covered by duplicate-id check.")

    problems_by_id = {problem["id"]: problem for problem in problems if isinstance(problem, dict)}
    problems_by_module_code: dict[str, list[str]] = defaultdict(list)
    for problem_id in problem_ids:
        code = problem_id.split("-")[0]
        problems_by_module_code[code].append(problem_id)

    for code, ids in sorted(problems_by_module_code.items()):
        sequence = sorted(int(problem_id.split("-")[1]) for problem_id in ids)
        expected = list(range(1, len(sequence) + 1))
        if sequence != expected:
            errors.append(
                f"Missing IDs in module {code}: expected contiguous sequence 001..{len(sequence):03d}."
            )

    for problem in problems:
        if not isinstance(problem, dict):
            continue
        problem_id = problem["id"]
        dependency = problem["dependency"]
        if isinstance(dependency, list):
            for dep in dependency:
                if dep not in problems_by_id:
                    errors.append(f"{problem_id}: broken dependency reference `{dep}`.")

    module_codes = set(module_order)
    for code, module in modules.items():
        prerequisites = module.get("prerequisites", [])
        unlock_targets = module.get("unlocks", [])
        if code not in module_codes:
            errors.append(f"dependency_graph.json: module `{code}` missing from module_order.")
        if not isinstance(prerequisites, list) or not isinstance(unlock_targets, list):
            errors.append(f"dependency_graph.json: module `{code}` must use list references.")
            continue
        for prereq in prerequisites:
            if prereq not in module_codes:
                errors.append(f"dependency_graph.json: `{code}` has missing prerequisite `{prereq}`.")
            elif code not in modules[prereq].get("unlocks", []):
                errors.append(
                    f"dependency_graph.json: `{prereq}` should list `{code}` in `unlocks`."
                )
        for target in unlock_targets:
            if target not in module_codes:
                errors.append(f"dependency_graph.json: `{code}` unlocks missing module `{target}`.")
            elif code not in modules[target].get("prerequisites", []):
                errors.append(
                    f"dependency_graph.json: `{target}` should list `{code}` in `prerequisites`."
                )

    for stage_name in stage_order:
        if stage_name not in stage_defs:
            errors.append(f"stages.json: stage `{stage_name}` missing from `stages`.")

    for stage_name, stage in stage_defs.items():
        modules_in_stage = stage.get("modules", [])
        if not isinstance(modules_in_stage, list):
            errors.append(f"stages.json: stage `{stage_name}` must define `modules` as a list.")
            continue
        for code in modules_in_stage:
            if code not in module_codes:
                errors.append(f"stages.json: stage `{stage_name}` references unknown module `{code}`.")
            elif modules[code].get("stage") != stage_name:
                errors.append(
                    f"stages.json: module `{code}` stage mismatch between stages.json and dependency graph."
                )

    if progress.get("current_stage") not in stage_defs:
        errors.append("progress_template.json: `current_stage` must be a valid stage.")

    current_problem = progress.get("current_problem")
    if current_problem is not None and current_problem not in problems_by_id:
        errors.append("progress_template.json: `current_problem` references a missing problem.")

    for field_name in ("completed", "revision_queue"):
        value = progress.get(field_name)
        if not isinstance(value, list):
            errors.append(f"progress_template.json: `{field_name}` must be a list.")
            continue
        for entry in value:
            entry_id = normalize_problem_id(entry)
            if entry_id is None:
                errors.append(
                    f"progress_template.json: `{field_name}` contains an unreadable entry `{entry}`."
                )
            elif entry_id not in problems_by_id:
                errors.append(
                    f"progress_template.json: `{field_name}` references missing problem `{entry_id}`."
                )

    weights = scoring.get("weights", {})
    if not isinstance(weights, dict) or not weights:
        errors.append("scoring.json: `weights` must be a non-empty object.")
    else:
        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) > 1e-9:
            errors.append(f"scoring.json: weights must sum to 1.0, found {total_weight}.")

    thresholds = scoring.get("promotion_thresholds", {})
    if not isinstance(thresholds, dict):
        errors.append("scoring.json: `promotion_thresholds` must be an object.")
    else:
        for stage_name in stage_order:
            if stage_name not in thresholds:
                errors.append(f"scoring.json: missing promotion threshold for stage `{stage_name}`.")

    if errors:
        print("Validation failed.")
        for error in errors:
            print(f"- {error}")
        if warnings:
            print("Warnings:")
            for warning in warnings:
                print(f"- {warning}")
        return 1

    print("Validation passed.")
    print(f"- Problems: {len(problems)}")
    print(f"- Modules: {len(module_order)}")
    print(f"- Stages: {len(stage_order)}")
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
