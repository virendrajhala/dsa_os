#!/usr/bin/env python3
"""Validate curriculum, skills, dependency graph, stages, scoring, and progress integrity."""

from __future__ import annotations

import argparse
import copy
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

from _shared import (
    CURRICULUM_PATH,
    GRAPH_PATH,
    PROGRESS_PATH,
    PROGRESS_TEMPLATE_PATH,
    SCORING_PATH,
    SKILLS_PATH,
    STAGES_PATH,
    OPEN_REVISION_STATUSES,
    REVISION_PRIORITY_ORDER,
    RepositoryError,
    RepositoryState,
    completed_records,
    load_json_file,
    normalize_progress,
    open_revision_entries,
    parse_iso_date,
    problem_lookup,
)


ID_RE = re.compile(r"^[A-Z]{2,3}-\d{3}$")
SKILL_ID_RE = re.compile(r"^SK-[A-Z]{2}-\d{2}$")
ALLOWED_DIFFICULTIES = {"Easy", "Medium", "Hard"}
ALLOWED_IMPORTANCE = {"CORE", "COMMON", "SPECIALIZED", "NICHE"}
ALLOWED_PROBLEM_ROLES = {"PRIMARY", "REINFORCEMENT", "CHALLENGE"}
ALLOWED_PROBLEM_STATUSES = {"not_started", "active", "completed", "revision"}
ALLOWED_REVISION_STATUSES = OPEN_REVISION_STATUSES | {"completed", "skipped", "cancelled"}

REQUIRED_PROBLEM_FIELDS = {
    "id",
    "original_number",
    "title",
    "difficulty",
    "section",
    "stage",
    "primary_skill",
    "secondary_skill",
    "problem_role",
    "difficulty_weight",
    "importance",
    "status",
    "revision_count",
    "notes",
}
REQUIRED_SKILL_FIELDS = {
    "id",
    "name",
    "description",
    "stage",
    "prerequisites",
    "primary_validation_problem",
    "reinforcement_problems",
    "challenge_problems",
}
REQUIRED_STAGE_FIELDS = {
    "goal",
    "skills",
    "entry_requirements",
    "exit_requirements",
    "mastery_criteria",
    "common_failure_modes",
}
REQUIRED_PROGRESS_FIELDS = {
    "schema_version",
    "last_updated",
    "current_stage",
    "current_problem",
    "completed",
    "mastered_skills",
    "skill_progress",
    "stage_mastery",
    "competency_completion",
    "revision_schedule",
    "thinking_profile",
    "scores",
    "notes",
    "history",
}
REQUIRED_COMPLETION_FIELDS = {
    "problem_id",
    "completed_at",
    "time_taken_minutes",
    "hint_level_used",
    "confidence_before",
    "confidence_after",
    "thinking_breakthrough",
    "main_mistake",
    "thinking_score",
    "interview_score",
    "next_revision_date",
}
REQUIRED_REVISION_FIELDS = {"problem", "date", "reason", "priority", "status"}


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(
        description="Run integrity checks across curriculum, skills, dependency, stages, scoring, and progress files."
    )
    parser.add_argument(
        "--progress-file",
        default=str(PROGRESS_PATH),
        help="Progress file to validate as the live state. Defaults to progress/progress.json.",
    )
    parser.add_argument(
        "--skip-template-progress",
        action="store_true",
        help="Skip validation of progress/progress_template.json.",
    )
    return parser


def add_error(errors: list[str], message: str) -> None:
    """Append a validation error."""

    errors.append(message)


def add_warning(warnings: list[str], message: str) -> None:
    """Append a validation warning."""

    warnings.append(message)


def detect_cycle_nodes(nodes: list[str], edges: dict[str, list[str]]) -> list[str]:
    """Return nodes that participate in or depend on a cycle. `edges[n]` = things `n` depends on."""

    indegree = {node: 0 for node in nodes}
    forward: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        for dep in edges.get(node, []):
            forward[dep].append(node)
            indegree[node] += 1
    queue = deque(node for node, degree in indegree.items() if degree == 0)
    visited_count = 0
    while queue:
        node = queue.popleft()
        visited_count += 1
        for target in forward.get(node, []):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if visited_count == len(nodes):
        return []
    return sorted(node for node, degree in indegree.items() if degree > 0)


def reachable_nodes(roots: list[str], edges: dict[str, list[str]]) -> set[str]:
    """Return all nodes reachable by following `edges` forward from the provided roots.
    `edges[n]` = things that depend on `n` (i.e. unlocked by `n`)."""

    seen: set[str] = set()
    queue = deque(roots)
    while queue:
        node = queue.popleft()
        if node in seen:
            continue
        seen.add(node)
        for target in edges.get(node, []):
            if target not in seen:
                queue.append(target)
    return seen


def validate_curriculum(
    curriculum: dict[str, Any],
    graph: dict[str, Any],
    stages: dict[str, Any],
    skills: dict[str, Any],
    scoring: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Validate curriculum, skills, dependency graph, stages, and scoring files."""

    errors: list[str] = []
    warnings: list[str] = []

    problems = curriculum.get("problems")
    if not isinstance(problems, list):
        add_error(errors, "curriculum.json: `problems` must be a list.")
        return errors, warnings

    # -- source / count metadata ------------------------------------------------
    source = curriculum.get("source", {})
    original_count = 507
    if not isinstance(source, dict):
        add_error(errors, "curriculum.json: `source` must be an object.")
    else:
        original_count = source.get("original_problem_count", source.get("problem_count"))
        if not isinstance(original_count, int) or original_count <= 0:
            add_error(errors, "curriculum.json: `source.original_problem_count` must be a positive integer.")
            original_count = 507
        total_count = source.get("total_problem_count", original_count)
        if not isinstance(total_count, int) or total_count < original_count:
            add_error(errors, "curriculum.json: `source.total_problem_count` must be an integer >= original_problem_count.")
            total_count = original_count
        if len(problems) != total_count:
            add_error(
                errors,
                f"curriculum.json: expected {total_count} problems per `source.total_problem_count`, "
                f"found {len(problems)}.",
            )
        supplemental_declared = source.get("supplemental_problems_added", 0)
        supplemental_actual = sum(1 for p in problems if isinstance(p, dict) and p.get("supplemental"))
        if supplemental_declared != supplemental_actual:
            add_error(
                errors,
                f"curriculum.json: `source.supplemental_problems_added` ({supplemental_declared}) does not "
                f"match the actual count of problems marked `supplemental` ({supplemental_actual}).",
            )

    # -- stages.json --------------------------------------------------------------
    stage_order = stages.get("stage_order")
    stage_defs = stages.get("stages")
    if not isinstance(stage_order, list) or not stage_order:
        add_error(errors, "stages.json: `stage_order` must be a non-empty list.")
        stage_order = []
    if not isinstance(stage_defs, dict) or not stage_defs:
        add_error(errors, "stages.json: `stages` must be a non-empty object.")
        stage_defs = {}
    if len(stage_order) != len(set(stage_order)):
        add_error(errors, "stages.json: `stage_order` contains duplicates.")
    if set(stage_order) != set(stage_defs):
        add_error(errors, "stages.json: `stage_order` and `stages` keys must match exactly.")

    stage_skill_occurrences: Counter[str] = Counter()
    for stage_name in stage_order:
        stage = stage_defs.get(stage_name, {})
        if not isinstance(stage, dict):
            add_error(errors, f"stages.json: stage `{stage_name}` must be an object.")
            continue
        missing = sorted(REQUIRED_STAGE_FIELDS - stage.keys())
        if missing:
            add_error(errors, f"stages.json: stage `{stage_name}` missing fields: {', '.join(missing)}.")
            continue
        for field in ("entry_requirements", "exit_requirements", "mastery_criteria", "common_failure_modes"):
            if not isinstance(stage[field], list) or not stage[field]:
                add_error(errors, f"stages.json: stage `{stage_name}` must define a non-empty `{field}`.")
        if not isinstance(stage["goal"], str) or not stage["goal"]:
            add_error(errors, f"stages.json: stage `{stage_name}` missing a valid `goal`.")
        stage_skills = stage.get("skills")
        if not isinstance(stage_skills, list) or not stage_skills:
            add_error(errors, f"stages.json: stage `{stage_name}` must define a non-empty `skills` list.")
            continue
        for skill_id in stage_skills:
            stage_skill_occurrences[skill_id] += 1

    # -- knowledge/skills.json ------------------------------------------------------
    skill_order = skills.get("skill_order")
    skill_defs = skills.get("skills")
    if not isinstance(skill_order, list) or not skill_order:
        add_error(errors, "knowledge/skills.json: `skill_order` must be a non-empty list.")
        skill_order = []
    if not isinstance(skill_defs, dict) or not skill_defs:
        add_error(errors, "knowledge/skills.json: `skills` must be a non-empty object.")
        skill_defs = {}
    if len(skill_order) != len(set(skill_order)):
        add_error(errors, "knowledge/skills.json: `skill_order` contains duplicates.")
    if set(skill_order) != set(skill_defs):
        add_error(errors, "knowledge/skills.json: `skill_order` and `skills` keys must match exactly.")

    for skill_id in skill_order:
        if stage_skill_occurrences[skill_id] != 1:
            add_error(
                errors,
                f"stages.json / knowledge/skills.json: skill `{skill_id}` must appear in exactly one "
                f"stage's `skills` list, found {stage_skill_occurrences[skill_id]}.",
            )

    problems_by_id_raw = {p["id"]: p for p in problems if isinstance(p, dict) and isinstance(p.get("id"), str)}

    for skill_id in skill_order:
        skill = skill_defs.get(skill_id, {})
        if not isinstance(skill, dict):
            add_error(errors, f"knowledge/skills.json: skill `{skill_id}` must be an object.")
            continue
        missing = sorted(REQUIRED_SKILL_FIELDS - skill.keys())
        if missing:
            add_error(errors, f"knowledge/skills.json: skill `{skill_id}` missing fields: {', '.join(missing)}.")
            continue
        if not SKILL_ID_RE.match(skill_id):
            add_error(errors, f"knowledge/skills.json: skill id `{skill_id}` has an unexpected format.")
        if skill["stage"] not in stage_defs:
            add_error(errors, f"knowledge/skills.json: skill `{skill_id}` references unknown stage `{skill['stage']}`.")
        if not isinstance(skill["description"], str) or not skill["description"].strip():
            add_error(errors, f"knowledge/skills.json: skill `{skill_id}` must have a non-empty `description`.")
        prereqs = skill.get("prerequisites")
        if not isinstance(prereqs, list):
            add_error(errors, f"knowledge/skills.json: skill `{skill_id}` `prerequisites` must be a list.")
        else:
            for p in prereqs:
                if p not in skill_defs:
                    add_error(errors, f"knowledge/skills.json: skill `{skill_id}` references missing prerequisite `{p}`.")

        primary_id = skill.get("primary_validation_problem")
        if primary_id not in problems_by_id_raw:
            add_error(errors, f"knowledge/skills.json: skill `{skill_id}` primary_validation_problem `{primary_id}` not found.")
        elif problems_by_id_raw[primary_id].get("problem_role") != "PRIMARY":
            add_error(
                errors,
                f"knowledge/skills.json: skill `{skill_id}` primary_validation_problem `{primary_id}` "
                f"must have `problem_role: PRIMARY` in curriculum.json.",
            )
        elif problems_by_id_raw[primary_id].get("primary_skill") != skill_id:
            add_error(errors, f"knowledge/skills.json: `{primary_id}`.primary_skill does not point back to `{skill_id}`.")

        reinforcement = skill.get("reinforcement_problems")
        if not isinstance(reinforcement, list) or not reinforcement:
            add_error(errors, f"knowledge/skills.json: skill `{skill_id}` must have at least one reinforcement problem.")
        challenge = skill.get("challenge_problems", [])
        for pid in list(reinforcement or []) + list(challenge or []):
            if pid not in problems_by_id_raw:
                add_error(errors, f"knowledge/skills.json: skill `{skill_id}` references missing problem `{pid}`.")

    # skill dependency graph must be acyclic, and (per the frozen curriculum rule)
    # every non-root skill has exactly one prerequisite so that each curriculum
    # transition introduces exactly one new reasoning model at a time.
    skill_dependencies = graph.get("skill_dependencies", {})
    if not isinstance(skill_dependencies, dict):
        add_error(errors, "dependency_graph.json: `skill_dependencies` must be an object.")
        skill_dependencies = {}
    for skill_id in skill_order:
        deps = skill_dependencies.get(skill_id)
        if not isinstance(deps, list):
            add_error(errors, f"dependency_graph.json: `skill_dependencies.{skill_id}` must be a list.")
            continue
        if len(deps) > 1:
            add_error(
                errors,
                f"dependency_graph.json: skill `{skill_id}` has {len(deps)} prerequisites; the frozen "
                f"curriculum rule requires at most one, so each transition unlocks a single new skill.",
            )
        for dep in deps:
            if dep not in skill_defs:
                add_error(errors, f"dependency_graph.json: skill `{skill_id}` depends on missing skill `{dep}`.")

    skill_cycle_nodes = detect_cycle_nodes(skill_order, skill_dependencies)
    if skill_cycle_nodes:
        add_error(errors, "dependency_graph.json: skill graph contains a cycle involving " + ", ".join(skill_cycle_nodes[:10]) + ".")

    skill_roots = [s for s in skill_order if not skill_dependencies.get(s)]
    if not skill_roots:
        add_error(errors, "dependency_graph.json: skill graph has no root skill.")
    else:
        skill_unlock_edges: dict[str, list[str]] = defaultdict(list)
        for s, deps in skill_dependencies.items():
            for dep in deps:
                skill_unlock_edges[dep].append(s)
        reachable_skills = reachable_nodes(skill_roots, skill_unlock_edges)
        orphan_skills = sorted(set(skill_order) - reachable_skills)
        if orphan_skills:
            add_error(errors, "dependency_graph.json: orphan skills detected (unreachable from any root): " + ", ".join(orphan_skills[:10]) + ".")

    # -- per-problem validation ------------------------------------------------------
    problem_ids: list[str] = []
    original_numbers: list[int] = []
    title_occurrences: dict[str, list[dict[str, Any]]] = defaultdict(list)
    problem_order: dict[str, int] = {}

    for index, problem in enumerate(problems):
        if not isinstance(problem, dict):
            add_error(errors, f"curriculum.json: problem #{index + 1} must be an object.")
            continue
        missing_fields = sorted(REQUIRED_PROBLEM_FIELDS - problem.keys())
        if missing_fields:
            add_error(errors, f"curriculum.json: problem #{index + 1} missing fields: {', '.join(missing_fields)}.")
            continue

        problem_id = problem["id"]
        if not isinstance(problem_id, str) or not ID_RE.match(problem_id):
            add_error(errors, f"curriculum.json: invalid problem id `{problem_id}`.")
            continue
        problem_ids.append(problem_id)
        problem_order[problem_id] = index

        original_number = problem["original_number"]
        is_supplemental = problem.get("supplemental") is True
        if is_supplemental:
            if original_number is not None:
                add_error(errors, f"curriculum.json: supplemental problem `{problem_id}` must have `original_number: null`.")
        elif not isinstance(original_number, int) or not 1 <= original_number <= original_count:
            add_error(errors, f"curriculum.json: `{problem_id}` has invalid `original_number` `{original_number}`.")
        else:
            original_numbers.append(original_number)

        title = problem["title"]
        if not isinstance(title, str) or not title:
            add_error(errors, f"curriculum.json: `{problem_id}` missing a valid `title`.")
        else:
            title_occurrences[title].append(problem)

        if problem["difficulty"] not in ALLOWED_DIFFICULTIES:
            add_error(errors, f"curriculum.json: `{problem_id}` has invalid difficulty `{problem['difficulty']}`.")
        expected_weight = {"Easy": 1, "Medium": 2, "Hard": 4}.get(problem["difficulty"])
        if problem.get("difficulty_weight") != expected_weight:
            add_error(
                errors,
                f"curriculum.json: `{problem_id}` `difficulty_weight` ({problem.get('difficulty_weight')}) "
                f"does not match its difficulty ({problem['difficulty']} -> {expected_weight}).",
            )
        if problem.get("importance") not in ALLOWED_IMPORTANCE:
            add_error(errors, f"curriculum.json: `{problem_id}` has invalid `importance` `{problem.get('importance')}`.")
        if problem.get("problem_role") not in ALLOWED_PROBLEM_ROLES:
            add_error(errors, f"curriculum.json: `{problem_id}` has invalid `problem_role` `{problem.get('problem_role')}`.")
        if not isinstance(problem["notes"], str) or not problem["notes"]:
            add_error(errors, f"curriculum.json: `{problem_id}` must include non-empty `notes`.")
        if problem["status"] not in ALLOWED_PROBLEM_STATUSES:
            add_error(errors, f"curriculum.json: `{problem_id}` has invalid status `{problem['status']}`.")
        if not isinstance(problem["revision_count"], int) or problem["revision_count"] < 0:
            add_error(errors, f"curriculum.json: `{problem_id}` has invalid `revision_count`.")

        primary_skill = problem.get("primary_skill")
        if primary_skill not in skill_defs:
            add_error(errors, f"curriculum.json: `{problem_id}` references unknown `primary_skill` `{primary_skill}`.")
        secondary_skill = problem.get("secondary_skill")
        if secondary_skill is not None and secondary_skill not in skill_defs:
            add_error(errors, f"curriculum.json: `{problem_id}` references unknown `secondary_skill` `{secondary_skill}`.")
        if secondary_skill is not None and secondary_skill == primary_skill:
            add_error(errors, f"curriculum.json: `{problem_id}` `secondary_skill` must differ from `primary_skill`.")

        stage_name = problem.get("stage")
        if stage_name not in stage_defs:
            add_error(errors, f"curriculum.json: `{problem_id}` references unknown stage `{stage_name}`.")
        elif primary_skill in skill_defs and skill_defs[primary_skill].get("stage") != stage_name:
            add_error(
                errors,
                f"curriculum.json: `{problem_id}` stage `{stage_name}` does not match its "
                f"primary_skill `{primary_skill}` stage `{skill_defs[primary_skill].get('stage')}`.",
            )

    duplicate_ids = sorted(problem_id for problem_id, count in Counter(problem_ids).items() if count > 1)
    if duplicate_ids:
        add_error(errors, "curriculum.json: duplicate ids found: " + ", ".join(duplicate_ids[:10]) + ".")

    duplicate_originals = sorted(number for number, count in Counter(original_numbers).items() if count > 1)
    if duplicate_originals:
        add_error(errors, "curriculum.json: duplicate original numbers found: " + ", ".join(str(n) for n in duplicate_originals[:10]) + ".")
    missing_originals = [n for n in range(1, original_count + 1) if n not in set(original_numbers)]
    if missing_originals:
        add_error(errors, "curriculum.json: missing original numbers: " + ", ".join(str(n) for n in missing_originals[:10]) + ".")

    for title, matching_problems in sorted(title_occurrences.items()):
        if len(matching_problems) <= 1:
            continue
        if not all(isinstance(p.get("notes"), str) and "Intentional revisit preserved" in p["notes"] for p in matching_problems):
            add_error(errors, f"curriculum.json: duplicate title `{title}` is missing intentional-duplicate notes.")
        else:
            add_warning(warnings, f"curriculum.json: duplicate title preserved intentionally: `{title}`.")

    # -- problem_dependencies (auto-generated; still validated for safety) -----------
    problem_dependencies = graph.get("problem_dependencies", {})
    if not isinstance(problem_dependencies, dict):
        add_error(errors, "dependency_graph.json: `problem_dependencies` must be an object.")
        problem_dependencies = {}

    problem_edges: dict[str, list[str]] = defaultdict(list)  # dep_id -> [ids that depend on it]
    for problem_id in problem_ids:
        deps = problem_dependencies.get(problem_id, [])
        if not isinstance(deps, list):
            add_error(errors, f"dependency_graph.json: `problem_dependencies.{problem_id}` must be a list.")
            continue
        if len(deps) != len(set(deps)):
            add_error(errors, f"dependency_graph.json: `{problem_id}` contains duplicate dependencies.")
        for dep_id in deps:
            if dep_id == problem_id:
                add_error(errors, f"dependency_graph.json: `{problem_id}` cannot depend on itself.")
            elif dep_id not in problems_by_id_raw:
                add_error(errors, f"dependency_graph.json: `{problem_id}` has broken dependency `{dep_id}`.")
            else:
                problem_edges[dep_id].append(problem_id)

    problem_cycle_nodes = detect_cycle_nodes(problem_ids, problem_dependencies)
    if problem_cycle_nodes:
        add_error(errors, "dependency_graph.json: problem dependency cycle detected involving " + ", ".join(problem_cycle_nodes[:10]) + ".")

    problem_roots = [pid for pid in problem_ids if not problem_dependencies.get(pid)]
    if not problem_roots:
        add_error(errors, "dependency_graph.json: problem dependency graph has no root problem.")
    else:
        reachable_problems = reachable_nodes(problem_roots, problem_edges)
        orphan_problems = sorted(set(problem_ids) - reachable_problems)
        if orphan_problems:
            add_error(errors, "dependency_graph.json: orphan problems detected: " + ", ".join(orphan_problems[:10]) + ".")

    # -- scoring.json -----------------------------------------------------------------
    if set(scoring.get("dimensions", {})) != set(scoring.get("weights", {})):
        add_error(errors, "scoring.json: `dimensions` and `weights` must use the same keys.")
    else:
        total_weight = sum(float(value) for value in scoring["weights"].values())
        if abs(total_weight - 1.0) > 1e-9:
            add_error(errors, f"scoring.json: `weights` must sum to 1.0, found {total_weight}.")

    interview_scale = scoring.get("interview_scale", {})
    interview_dimensions = scoring.get("interview_dimensions", {})
    if not isinstance(interview_scale, dict) or not isinstance(interview_dimensions, dict):
        add_error(errors, "scoring.json: interview scoring metadata is incomplete.")
    elif not interview_dimensions:
        add_error(errors, "scoring.json: `interview_dimensions` must not be empty.")

    hint_levels = scoring.get("hint_levels")
    if not isinstance(hint_levels, dict) or not hint_levels:
        add_error(errors, "scoring.json: `hint_levels` must be a non-empty object.")

    revision_policy = scoring.get("revision_policy", {})
    priority_days = revision_policy.get("days_by_priority", {})
    if not isinstance(priority_days, dict):
        add_error(errors, "scoring.json: `revision_policy.days_by_priority` must be an object.")
    else:
        for priority in REVISION_PRIORITY_ORDER:
            if priority not in priority_days or not isinstance(priority_days[priority], int):
                add_error(errors, f"scoring.json: revision priority `{priority}` must define integer review days.")

    thresholds = scoring.get("promotion_thresholds", {})
    if not isinstance(thresholds, dict):
        add_error(errors, "scoring.json: `promotion_thresholds` must be an object.")
    else:
        for stage_name in stage_order:
            if stage_name not in thresholds:
                add_error(errors, f"scoring.json: missing promotion threshold for stage `{stage_name}`.")

    if not isinstance(scoring.get("skill_mastery", {}).get("minimum_primary_weighted_score"), (int, float)):
        add_error(errors, "scoring.json: `skill_mastery.minimum_primary_weighted_score` must be numeric.")

    return errors, warnings


def validate_progress_payload(
    label: str,
    progress: dict[str, Any],
    curriculum: dict[str, Any],
    graph: dict[str, Any],
    stages: dict[str, Any],
    skills: dict[str, Any],
    scoring: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Validate a progress payload against the repository metadata."""

    errors: list[str] = []
    warnings: list[str] = []
    problems = problem_lookup(curriculum)
    stage_defs = stages.get("stages", {})
    skill_defs = skills.get("skills", {})
    if not isinstance(stage_defs, dict):
        add_error(errors, f"{label}: stages metadata is unreadable.")
        return errors, warnings

    missing_fields = sorted(REQUIRED_PROGRESS_FIELDS - progress.keys())
    if missing_fields:
        add_error(errors, f"{label}: missing fields: {', '.join(missing_fields)}.")

    if not isinstance(progress.get("schema_version"), int):
        add_error(errors, f"{label}: `schema_version` must be an integer.")
    if progress.get("last_updated") is not None:
        if not isinstance(progress["last_updated"], str):
            add_error(errors, f"{label}: `last_updated` must be null or YYYY-MM-DD.")
        else:
            try:
                parse_iso_date(progress["last_updated"], f"{label}.last_updated")
            except RepositoryError as exc:
                add_error(errors, f"{label}: {exc}")

    current_stage = progress.get("current_stage")
    if current_stage not in stage_defs:
        add_error(errors, f"{label}: `current_stage` must be a valid stage.")

    current_problem = progress.get("current_problem")
    if current_problem is not None and current_problem not in problems:
        add_error(errors, f"{label}: `current_problem` references missing problem `{current_problem}`.")

    thinking_profile = progress.get("thinking_profile")
    if not isinstance(thinking_profile, dict):
        add_error(errors, f"{label}: `thinking_profile` must be an object.")
    else:
        for key in ("strengths", "gaps", "common_failures", "preferred_patterns"):
            if not isinstance(thinking_profile.get(key), list):
                add_error(errors, f"{label}: `thinking_profile.{key}` must be a list.")
        if not isinstance(thinking_profile.get("notes"), str):
            add_error(errors, f"{label}: `thinking_profile.notes` must be a string.")

    if not isinstance(progress.get("notes"), list):
        add_error(errors, f"{label}: `notes` must be a list.")
    if not isinstance(progress.get("history"), list):
        add_error(errors, f"{label}: `history` must be a list.")

    mastered_skills = progress.get("mastered_skills")
    if not isinstance(mastered_skills, list):
        add_error(errors, f"{label}: `mastered_skills` must be a list.")
    else:
        for sid in mastered_skills:
            if sid not in skill_defs:
                add_error(errors, f"{label}: `mastered_skills` references unknown skill `{sid}`.")

    skill_progress = progress.get("skill_progress")
    if not isinstance(skill_progress, dict):
        add_error(errors, f"{label}: `skill_progress` must be an object.")

    stage_mastery = progress.get("stage_mastery")
    if not isinstance(stage_mastery, dict):
        add_error(errors, f"{label}: `stage_mastery` must be an object.")
    else:
        for stage_name, entry in stage_mastery.items():
            if stage_name not in stage_defs:
                add_error(errors, f"{label}: `stage_mastery` references unknown stage `{stage_name}`.")
                continue
            if not isinstance(entry, dict) or entry.get("status") not in {"locked", "in_progress", "mastered"}:
                add_error(errors, f"{label}: `stage_mastery.{stage_name}.status` must be locked/in_progress/mastered.")

    competency_completion = progress.get("competency_completion")
    if not isinstance(competency_completion, dict) or "percent" not in competency_completion:
        add_error(errors, f"{label}: `competency_completion` must be an object with a `percent` field.")

    hint_levels = scoring.get("hint_levels", {})
    thinking_dimensions = set(scoring.get("dimensions", {}))
    interview_dimensions = set(scoring.get("interview_dimensions", {}))
    thinking_min = float(scoring.get("scale", {}).get("minimum", 0))
    thinking_max = float(scoring.get("scale", {}).get("maximum", 4))
    interview_min = float(scoring.get("interview_scale", {}).get("minimum", 0))
    interview_max = float(scoring.get("interview_scale", {}).get("maximum", 10))

    completion_records = completed_records(progress)
    completion_dates: list[str] = []
    scheduled_pairs: Counter[tuple[str, str]] = Counter()
    latest_open_pairs: Counter[tuple[str, str]] = Counter()

    for index, record in enumerate(completion_records, start=1):
        missing = sorted(REQUIRED_COMPLETION_FIELDS - record.keys())
        if missing:
            add_error(errors, f"{label}: completion #{index} missing fields: {', '.join(missing)}.")
            continue

        problem_id = record.get("problem_id")
        if problem_id not in problems:
            add_error(errors, f"{label}: completion #{index} references missing problem `{problem_id}`.")

        completed_at = record.get("completed_at")
        if not isinstance(completed_at, str):
            add_error(errors, f"{label}: completion #{index} has invalid `completed_at`.")
        else:
            try:
                parse_iso_date(completed_at, f"{label}.completed[{index}].completed_at")
                completion_dates.append(completed_at)
            except RepositoryError as exc:
                add_error(errors, f"{label}: {exc}")

        if not isinstance(record.get("time_taken_minutes"), int) or record["time_taken_minutes"] <= 0:
            add_error(errors, f"{label}: completion #{index} has invalid `time_taken_minutes`.")

        hint_level = record.get("hint_level_used")
        if str(hint_level) not in hint_levels:
            add_error(errors, f"{label}: completion #{index} uses invalid hint level `{hint_level}`.")

        for confidence_field in ("confidence_before", "confidence_after"):
            value = record.get(confidence_field)
            if not isinstance(value, int) or not 0 <= value <= 10:
                add_error(errors, f"{label}: completion #{index} has invalid `{confidence_field}`.")

        for text_field in ("thinking_breakthrough", "main_mistake"):
            value = record.get(text_field)
            if not isinstance(value, str) or not value.strip():
                add_error(errors, f"{label}: completion #{index} must include non-empty `{text_field}`.")

        thinking_score = record.get("thinking_score")
        if not isinstance(thinking_score, dict) or set(thinking_score) != thinking_dimensions:
            add_error(errors, f"{label}: completion #{index} must define all thinking-score dimensions.")
        else:
            for dimension, value in thinking_score.items():
                if not isinstance(value, (int, float)) or not thinking_min <= float(value) <= thinking_max:
                    add_error(errors, f"{label}: completion #{index} has out-of-range thinking score `{dimension}`.")

        interview_score = record.get("interview_score")
        if not isinstance(interview_score, dict) or set(interview_score) != interview_dimensions:
            add_error(errors, f"{label}: completion #{index} must define all interview-score dimensions.")
        else:
            for dimension, value in interview_score.items():
                if not isinstance(value, (int, float)) or not interview_min <= float(value) <= interview_max:
                    add_error(errors, f"{label}: completion #{index} has out-of-range interview score `{dimension}`.")

        next_revision_date = record.get("next_revision_date")
        if not isinstance(next_revision_date, str):
            add_error(errors, f"{label}: completion #{index} has invalid `next_revision_date`.")
        else:
            try:
                next_revision = parse_iso_date(next_revision_date, f"{label}.completed[{index}].next_revision_date")
                if isinstance(completed_at, str):
                    solved_on = parse_iso_date(completed_at, f"{label}.completed[{index}].completed_at")
                    if next_revision < solved_on:
                        add_error(errors, f"{label}: completion #{index} schedules revision before completion date.")
            except RepositoryError as exc:
                add_error(errors, f"{label}: {exc}")

    if completion_dates != sorted(completion_dates):
        add_error(errors, f"{label}: completion records must be ordered by `completed_at`.")

    revision_entries = progress.get("revision_schedule")
    if not isinstance(revision_entries, list):
        add_error(errors, f"{label}: `revision_schedule` must be a list.")
        revision_entries = []

    for index, entry in enumerate(revision_entries, start=1):
        if not isinstance(entry, dict):
            add_error(errors, f"{label}: revision entry #{index} must be an object.")
            continue
        missing = sorted(REQUIRED_REVISION_FIELDS - entry.keys())
        if missing:
            add_error(errors, f"{label}: revision entry #{index} missing fields: {', '.join(missing)}.")
            continue

        problem_id = entry.get("problem")
        if problem_id not in problems:
            add_error(errors, f"{label}: revision entry #{index} references missing problem `{problem_id}`.")

        entry_date = entry.get("date")
        if not isinstance(entry_date, str):
            add_error(errors, f"{label}: revision entry #{index} has invalid `date`.")
        else:
            try:
                parse_iso_date(entry_date, f"{label}.revision_schedule[{index}].date")
            except RepositoryError as exc:
                add_error(errors, f"{label}: {exc}")

        reason = entry.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            add_error(errors, f"{label}: revision entry #{index} must include non-empty `reason`.")

        priority = entry.get("priority")
        if priority not in REVISION_PRIORITY_ORDER:
            add_error(errors, f"{label}: revision entry #{index} has invalid priority `{priority}`.")

        status = entry.get("status")
        if status not in ALLOWED_REVISION_STATUSES:
            add_error(errors, f"{label}: revision entry #{index} has invalid status `{status}`.")

        pair = (str(problem_id), str(entry_date))
        scheduled_pairs[pair] += 1
        if status in OPEN_REVISION_STATUSES:
            latest_open_pairs[pair] += 1

    duplicate_open_entries = [pair for pair, count in latest_open_pairs.items() if count > 1]
    if duplicate_open_entries:
        add_error(errors, f"{label}: duplicate open revision entries detected for {duplicate_open_entries[:5]}.")

    for record in completion_records:
        pair = (str(record.get("problem_id")), str(record.get("next_revision_date")))
        if scheduled_pairs[pair] == 0:
            add_error(errors, f"{label}: missing revision schedule entry for {pair[0]} on {pair[1]}.")

    for index, event in enumerate(progress.get("history", []), start=1):
        if not isinstance(event, dict):
            add_error(errors, f"{label}: history event #{index} must be an object.")
            continue
        if not isinstance(event.get("timestamp"), str):
            add_error(errors, f"{label}: history event #{index} requires `timestamp`.")
        else:
            try:
                parse_iso_date(event["timestamp"], f"{label}.history[{index}].timestamp")
            except RepositoryError as exc:
                add_error(errors, f"{label}: {exc}")
        if not isinstance(event.get("event"), str) or not event["event"]:
            add_error(errors, f"{label}: history event #{index} requires non-empty `event`.")
        problem_id = event.get("problem_id")
        if problem_id is not None and problem_id not in problems:
            add_error(errors, f"{label}: history event #{index} references missing problem `{problem_id}`.")

    if current_problem is not None and current_problem in {record.get("problem_id") for record in completion_records}:
        open_problem_ids = {entry.get("problem") for entry in open_revision_entries(progress)}
        if current_problem not in open_problem_ids:
            add_warning(warnings, f"{label}: `current_problem` is already completed and not currently scheduled for revision.")

    expected_progress = copy.deepcopy(progress)
    try:
        normalize_progress(
            RepositoryState(
                curriculum=curriculum,
                graph=graph,
                stages=stages,
                skills=skills,
                scoring=scoring,
                progress=expected_progress,
                progress_path=Path(label),
            ),
            expected_progress,
        )
    except RepositoryError as exc:
        add_error(errors, f"{label}: failed to recompute derived progress state: {exc}")
    else:
        for field in ("scores", "current_stage", "mastered_skills", "skill_progress", "stage_mastery", "competency_completion"):
            if expected_progress.get(field) != progress.get(field):
                add_error(errors, f"{label}: cached `{field}` does not match the recomputed value.")

    return errors, warnings


def main() -> int:
    """Run the validator."""

    parser = build_parser()
    args = parser.parse_args()

    try:
        curriculum = load_json_file(CURRICULUM_PATH)
        graph = load_json_file(GRAPH_PATH)
        stages = load_json_file(STAGES_PATH)
        skills = load_json_file(SKILLS_PATH)
        scoring = load_json_file(SCORING_PATH)
        progress_payloads: list[tuple[str, dict[str, Any]]] = [
            (str(Path(args.progress_file)), load_json_file(Path(args.progress_file))),
        ]
        template_path = PROGRESS_TEMPLATE_PATH.resolve()
        live_path = Path(args.progress_file).resolve()
        if not args.skip_template_progress and template_path != live_path:
            progress_payloads.append((str(template_path), load_json_file(template_path)))
    except RepositoryError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    errors, warnings = validate_curriculum(curriculum, graph, stages, skills, scoring)
    for label, payload in progress_payloads:
        progress_errors, progress_warnings = validate_progress_payload(
            label=label,
            progress=payload,
            curriculum=curriculum,
            graph=graph,
            stages=stages,
            skills=skills,
            scoring=scoring,
        )
        errors.extend(progress_errors)
        warnings.extend(progress_warnings)

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
    print(f"- Problems: {len(curriculum['problems'])}")
    print(f"- Skills: {len(skills['skill_order'])}")
    print(f"- Stages: {len(stages['stage_order'])}")
    print(f"- Progress files: {len(progress_payloads)}")
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
