#!/usr/bin/env python3
"""Shared repository utilities for DSA_OS command-line tools."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CURRICULUM_PATH = ROOT / "curriculum" / "curriculum.json"
GRAPH_PATH = ROOT / "curriculum" / "dependency_graph.json"
STAGES_PATH = ROOT / "curriculum" / "stages.json"
SCORING_PATH = ROOT / "progress" / "scoring.json"
PROGRESS_PATH = ROOT / "progress" / "progress.json"
PROGRESS_TEMPLATE_PATH = ROOT / "progress" / "progress_template.json"

REVISION_PRIORITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}
OPEN_REVISION_STATUSES = {"scheduled"}
THINKING_DIMENSION_LABELS = {
    "understanding": "Understanding",
    "examples": "Examples",
    "brute_force": "Brute Force",
    "pattern_detection": "Observation",
    "algorithm_design": "Algorithm Design",
    "complexity_analysis": "Complexity",
    "implementation": "Implementation",
    "communication": "Communication",
}

JsonDict = dict[str, Any]


class RepositoryError(RuntimeError):
    """Raised when repository state cannot be loaded or interpreted safely."""


@dataclass(frozen=True)
class RepositoryState:
    """Loaded repository data required by the CLI scripts."""

    curriculum: JsonDict
    graph: JsonDict
    stages: JsonDict
    scoring: JsonDict
    progress: JsonDict
    progress_path: Path


@dataclass(frozen=True)
class SelectionResult:
    """The result of choosing the next problem to work on."""

    mode: str
    reason: str
    problem: JsonDict | None
    suggested_stage: str | None = None
    revision_entry: JsonDict | None = None


def load_json_file(path: Path) -> JsonDict:
    """Load a JSON file and raise a typed repository error on failure."""

    try:
        return json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise RepositoryError(f"Missing required file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RepositoryError(f"Invalid JSON in {path}: {exc}") from exc


def save_json_file(path: Path, payload: JsonDict) -> None:
    """Persist a JSON payload using stable formatting."""

    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def resolve_progress_path(explicit_path: str | None = None) -> Path:
    """Resolve the progress file path, preferring the live progress file."""

    if explicit_path:
        return Path(explicit_path).expanduser().resolve()
    if PROGRESS_PATH.exists():
        return PROGRESS_PATH
    return PROGRESS_TEMPLATE_PATH


def load_repository_state(explicit_progress_path: str | None = None) -> RepositoryState:
    """Load curriculum, graph, stages, scoring, and progress state."""

    progress_path = resolve_progress_path(explicit_progress_path)
    return RepositoryState(
        curriculum=load_json_file(CURRICULUM_PATH),
        graph=load_json_file(GRAPH_PATH),
        stages=load_json_file(STAGES_PATH),
        scoring=load_json_file(SCORING_PATH),
        progress=load_json_file(progress_path),
        progress_path=progress_path,
    )


def parse_iso_date(value: str, field_name: str) -> date:
    """Parse an ISO-8601 date string or raise a repository error."""

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise RepositoryError(
            f"Invalid date for `{field_name}`: expected YYYY-MM-DD, found `{value}`."
        ) from exc


def format_iso_date(value: date) -> str:
    """Format a date as an ISO-8601 string."""

    return value.isoformat()


def ensure_list(value: Any, field_name: str) -> list[Any]:
    """Return a list field or raise a repository error."""

    if not isinstance(value, list):
        raise RepositoryError(f"`{field_name}` must be a list.")
    return value


def problem_lookup(curriculum: JsonDict) -> dict[str, JsonDict]:
    """Return problems keyed by problem id."""

    problems = ensure_list(curriculum.get("problems"), "curriculum.problems")
    return {problem["id"]: problem for problem in problems if isinstance(problem, dict)}


def problem_order_index(curriculum: JsonDict) -> dict[str, int]:
    """Return the repository order of problems."""

    problems = ensure_list(curriculum.get("problems"), "curriculum.problems")
    return {
        problem["id"]: index
        for index, problem in enumerate(problems)
        if isinstance(problem, dict) and "id" in problem
    }


def module_name_to_code(graph: JsonDict) -> dict[str, str]:
    """Return a mapping from module name to module code."""

    modules = graph.get("modules")
    if not isinstance(modules, dict):
        raise RepositoryError("dependency_graph.json: `modules` must be an object.")
    mapping: dict[str, str] = {}
    for code, module in modules.items():
        if isinstance(module, dict) and isinstance(module.get("name"), str):
            mapping[module["name"]] = code
    return mapping


def completed_records(progress: JsonDict) -> list[JsonDict]:
    """Return completion records in append order."""

    records = ensure_list(progress.get("completed"), "progress.completed")
    return [record for record in records if isinstance(record, dict)]


def latest_records_by_problem(progress: JsonDict) -> dict[str, JsonDict]:
    """Return the most recent completion record for each problem id."""

    latest: dict[str, JsonDict] = {}
    for record in completed_records(progress):
        problem_id = record.get("problem_id")
        if isinstance(problem_id, str):
            latest[problem_id] = record
    return latest


def completed_problem_ids(progress: JsonDict) -> set[str]:
    """Return the set of problems that have at least one completion record."""

    return set(latest_records_by_problem(progress))


def current_problem_id(progress: JsonDict) -> str | None:
    """Return the active current problem id if present."""

    value = progress.get("current_problem")
    return value if isinstance(value, str) else None


def last_completion_record(progress: JsonDict) -> JsonDict | None:
    """Return the most recently appended completion record."""

    records = completed_records(progress)
    return records[-1] if records else None


def open_revision_entries(progress: JsonDict) -> list[JsonDict]:
    """Return revision entries that are still actionable."""

    entries = ensure_list(progress.get("revision_schedule"), "progress.revision_schedule")
    return [
        entry
        for entry in entries
        if isinstance(entry, dict) and entry.get("status") in OPEN_REVISION_STATUSES
    ]


def open_revision_entries_due_on_or_before(progress: JsonDict, on_date: date) -> list[JsonDict]:
    """Return actionable revision entries due on or before the given date."""

    due_entries: list[JsonDict] = []
    for entry in open_revision_entries(progress):
        raw_date = entry.get("date")
        if not isinstance(raw_date, str):
            continue
        if parse_iso_date(raw_date, "revision_schedule.date") <= on_date:
            due_entries.append(entry)
    return due_entries


def weighted_thinking_score(record: JsonDict, scoring: JsonDict) -> float | None:
    """Calculate the weighted thinking score for a completion record."""

    weights = scoring.get("weights")
    scores = record.get("thinking_score")
    if not isinstance(weights, dict) or not isinstance(scores, dict):
        return None
    try:
        return round(
            sum(float(scores[dimension]) * float(weight) for dimension, weight in weights.items()),
            4,
        )
    except (KeyError, TypeError, ValueError):
        return None


def average_interview_score(record: JsonDict) -> float | None:
    """Calculate the average interview score for a completion record."""

    scores = record.get("interview_score")
    if not isinstance(scores, dict) or not scores:
        return None
    try:
        return round(mean(float(value) for value in scores.values()), 4)
    except (TypeError, ValueError):
        return None


def determine_stage(progress: JsonDict, stages: JsonDict, scoring: JsonDict) -> str:
    """Determine the learner's stage from unique completed problems and score quality."""

    stage_order = stages.get("stage_order")
    thresholds = scoring.get("promotion_thresholds")
    if not isinstance(stage_order, list) or not stage_order:
        raise RepositoryError("stages.json: `stage_order` must be a non-empty list.")
    if not isinstance(thresholds, dict):
        raise RepositoryError("scoring.json: `promotion_thresholds` must be an object.")

    latest_records = list(latest_records_by_problem(progress).values())
    weighted_scores = [
        score
        for score in (weighted_thinking_score(record, scoring) for record in latest_records)
        if score is not None
    ]
    average_weighted = mean(weighted_scores) if weighted_scores else 0.0
    unique_completed = len(latest_records)

    resolved_stage = stage_order[0]
    for stage_name in stage_order:
        threshold = thresholds.get(stage_name, {})
        if not isinstance(threshold, dict):
            continue
        minimum_completed = threshold.get("minimum_completed_problems", 0)
        minimum_score = threshold.get("minimum_weighted_score", 0.0)
        if unique_completed >= minimum_completed and average_weighted >= minimum_score:
            resolved_stage = stage_name
    return resolved_stage


def recompute_score_summary(
    progress: JsonDict,
    curriculum: JsonDict,
    stages: JsonDict,
    scoring: JsonDict,
) -> JsonDict:
    """Rebuild cached score summaries from completion records."""

    latest_by_problem = latest_records_by_problem(progress)
    latest_records = list(latest_by_problem.values())
    latest_record = last_completion_record(progress)
    thinking_dimensions = list(scoring.get("dimensions", {}).keys())
    interview_dimensions = list(scoring.get("interview_dimensions", {}).keys())

    def average_dimension(records: list[JsonDict], field_name: str, dimension: str) -> float:
        values: list[float] = []
        for record in records:
            score_block = record.get(field_name)
            if isinstance(score_block, dict) and dimension in score_block:
                try:
                    values.append(float(score_block[dimension]))
                except (TypeError, ValueError):
                    continue
        return round(mean(values), 2) if values else 0.0

    weighted_scores = [
        score
        for score in (weighted_thinking_score(record, scoring) for record in latest_records)
        if score is not None
    ]
    interview_scores = [
        score for score in (average_interview_score(record) for record in latest_records) if score is not None
    ]
    confidence_before_values = [
        float(record["confidence_before"])
        for record in latest_records
        if isinstance(record.get("confidence_before"), (int, float))
    ]
    confidence_after_values = [
        float(record["confidence_after"])
        for record in latest_records
        if isinstance(record.get("confidence_after"), (int, float))
    ]

    problems = problem_lookup(curriculum)
    thresholds = scoring.get("promotion_thresholds", {})
    stage_order = stages.get("stage_order", [])
    stage_checks: JsonDict = {}
    for stage_name in stage_order:
        stage_threshold = thresholds.get(stage_name, {})
        minimum_weighted = (
            float(stage_threshold.get("minimum_weighted_score", 0.0))
            if isinstance(stage_threshold, dict)
            else 0.0
        )
        stage_problem_records = [
            record
            for record in latest_records
            if problems.get(record.get("problem_id"), {}).get("stage") == stage_name
        ]
        passed = 0
        for record in stage_problem_records:
            score = weighted_thinking_score(record, scoring)
            if score is not None and score >= minimum_weighted:
                passed += 1
        stage_checks[stage_name] = {
            "attempted": len(stage_problem_records),
            "passed": passed,
        }

    return {
        "latest_thinking_score": latest_record.get("thinking_score", {}) if latest_record else {},
        "latest_interview_score": latest_record.get("interview_score", {}) if latest_record else {},
        "averages": {
            "thinking_weighted": round(mean(weighted_scores), 2) if weighted_scores else 0.0,
            "thinking_dimensions": {
                dimension: average_dimension(latest_records, "thinking_score", dimension)
                for dimension in thinking_dimensions
            },
            "interview_average": round(mean(interview_scores), 2) if interview_scores else 0.0,
            "interview_dimensions": {
                dimension: average_dimension(latest_records, "interview_score", dimension)
                for dimension in interview_dimensions
            },
            "confidence_before": (
                round(mean(confidence_before_values), 2) if confidence_before_values else 0.0
            ),
            "confidence_after": (
                round(mean(confidence_after_values), 2) if confidence_after_values else 0.0
            ),
            "solved_unique_problems": len(latest_records),
        },
        "stage_checks": stage_checks,
    }


def normalize_progress(state: RepositoryState, payload: JsonDict) -> JsonDict:
    """Refresh derived progress fields in-place and return the payload."""

    payload["scores"] = recompute_score_summary(
        progress=payload,
        curriculum=state.curriculum,
        stages=state.stages,
        scoring=state.scoring,
    )
    payload["current_stage"] = determine_stage(payload, state.stages, state.scoring)
    return payload


def derive_current_module_code(state: RepositoryState) -> str | None:
    """Infer the active module from the current problem or latest solved work."""

    problems = problem_lookup(state.curriculum)
    module_map = module_name_to_code(state.graph)

    active_problem_id = current_problem_id(state.progress)
    if active_problem_id and active_problem_id in problems:
        return module_map.get(problems[active_problem_id]["module"])

    latest_record = last_completion_record(state.progress)
    if latest_record and isinstance(latest_record.get("problem_id"), str):
        latest_problem = problems.get(latest_record["problem_id"])
        if latest_problem:
            return module_map.get(latest_problem["module"])

    return None


def is_problem_unlocked(problem: JsonDict, completed_ids: set[str]) -> bool:
    """Return whether a curriculum problem is unlocked for first-pass solving."""

    dependencies = problem.get("dependency", [])
    if not isinstance(dependencies, list):
        return False
    return all(isinstance(dep, str) and dep in completed_ids for dep in dependencies)


def select_next_problem(state: RepositoryState, on_date: date | None = None) -> SelectionResult:
    """Choose the next problem using revisions, module continuity, and stage order."""

    today = on_date or date.today()
    problems = ensure_list(state.curriculum.get("problems"), "curriculum.problems")
    problems_by_id = problem_lookup(state.curriculum)
    problem_order = problem_order_index(state.curriculum)
    module_map = module_name_to_code(state.graph)
    module_order = ensure_list(state.graph.get("module_order"), "dependency_graph.module_order")
    stage_order = ensure_list(state.stages.get("stage_order"), "stages.stage_order")
    stage_defs = state.stages.get("stages")
    if not isinstance(stage_defs, dict):
        raise RepositoryError("stages.json: `stages` must be an object.")

    due_revisions = open_revision_entries_due_on_or_before(state.progress, today)
    if due_revisions:
        sorted_due = sorted(
            due_revisions,
            key=lambda entry: (
                parse_iso_date(entry["date"], "revision_schedule.date"),
                REVISION_PRIORITY_ORDER.get(str(entry.get("priority")), 999),
                problem_order.get(str(entry.get("problem")), 10**9),
            ),
        )
        chosen_entry = sorted_due[0]
        chosen_problem = problems_by_id.get(str(chosen_entry["problem"]))
        if chosen_problem is None:
            raise RepositoryError(
                f"Revision schedule references missing problem `{chosen_entry['problem']}`."
            )
        due_date = parse_iso_date(chosen_entry["date"], "revision_schedule.date")
        reason = (
            "Revision is overdue."
            if due_date < today
            else "Revision is due today and takes priority over new work."
        )
        return SelectionResult(
            mode="revision_due",
            reason=reason,
            problem=chosen_problem,
            suggested_stage=chosen_problem.get("stage"),
            revision_entry=chosen_entry,
        )

    completed_ids = completed_problem_ids(state.progress)
    incomplete_unlocked = [
        problem
        for problem in problems
        if isinstance(problem, dict)
        and isinstance(problem.get("id"), str)
        and problem["id"] not in completed_ids
        and is_problem_unlocked(problem, completed_ids)
    ]

    active_problem_id = current_problem_id(state.progress)
    if active_problem_id and active_problem_id in problems_by_id and active_problem_id not in completed_ids:
        active_problem = problems_by_id[active_problem_id]
        if is_problem_unlocked(active_problem, completed_ids):
            return SelectionResult(
                mode="resume_current_problem",
                reason="Current problem is still active and remains unlocked.",
                problem=active_problem,
                suggested_stage=active_problem.get("stage"),
            )

    current_module_code = derive_current_module_code(state)
    if current_module_code:
        current_module_candidates = [
            problem
            for problem in incomplete_unlocked
            if module_map.get(str(problem.get("module"))) == current_module_code
        ]
        if current_module_candidates:
            chosen_problem = sorted(
                current_module_candidates,
                key=lambda problem: problem_order[problem["id"]],
            )[0]
            return SelectionResult(
                mode="current_module",
                reason="Continuing in the current module preserves local reasoning context.",
                problem=chosen_problem,
                suggested_stage=chosen_problem.get("stage"),
            )

    current_stage = state.progress.get("current_stage")
    if not isinstance(current_stage, str) or current_stage not in stage_order:
        current_stage = stage_order[0]
    stage_modules = stage_defs[current_stage]["modules"]
    stage_candidates = [
        problem
        for problem in incomplete_unlocked
        if module_map.get(str(problem.get("module"))) in stage_modules
    ]
    if stage_candidates:
        chosen_problem = sorted(stage_candidates, key=lambda problem: problem_order[problem["id"]])[0]
        return SelectionResult(
            mode="current_stage",
            reason="Selecting the earliest unlocked problem in the active stage.",
            problem=chosen_problem,
            suggested_stage=current_stage,
        )

    if incomplete_unlocked:
        chosen_problem = sorted(incomplete_unlocked, key=lambda problem: problem_order[problem["id"]])[0]
        return SelectionResult(
            mode="earliest_unlocked",
            reason="Choosing the earliest unlocked dependency-safe problem in the curriculum.",
            problem=chosen_problem,
            suggested_stage=chosen_problem.get("stage"),
        )

    return SelectionResult(
        mode="complete",
        reason="No unlocked work remains.",
        problem=None,
        suggested_stage=None,
    )


def revision_decision(
    record: JsonDict,
    scoring: JsonDict,
    completed_on: date,
) -> tuple[str, str, str]:
    """Determine revision priority, due date, and reason for a solved problem."""

    policy = scoring.get("revision_policy", {})
    priority_days = policy.get("days_by_priority", {})
    thresholds = policy.get("thresholds", {})
    maintenance_reason = str(
        policy.get("maintenance_reason", "Scheduled spaced revision after a stable solve.")
    )

    weighted = weighted_thinking_score(record, scoring) or 0.0
    interview_average = average_interview_score(record) or 0.0
    hint_level = int(record["hint_level_used"])
    confidence_after = int(record["confidence_after"])
    confidence_before = int(record["confidence_before"])
    confidence_delta = confidence_after - confidence_before

    def matches(priority: str) -> bool:
        threshold = thresholds.get(priority, {})
        if not isinstance(threshold, dict):
            return False
        if weighted <= float(threshold.get("max_weighted_thinking_score", -1)):
            return True
        if interview_average <= float(threshold.get("max_interview_average", -1)):
            return True
        if confidence_after <= int(threshold.get("max_confidence_after", -1)):
            return True
        if hint_level >= int(threshold.get("min_hint_level_used", 10**9)):
            return True
        if confidence_delta <= int(threshold.get("max_confidence_delta", -10**9)):
            return True
        return False

    for candidate in ("critical", "high", "medium"):
        if matches(candidate):
            priority = candidate
            break
    else:
        priority = "low"

    reasons: list[str] = []
    if weighted <= float(thresholds.get(priority, {}).get("max_weighted_thinking_score", -1)):
        reasons.append(f"weighted thinking score {weighted:.2f}")
    if interview_average <= float(thresholds.get(priority, {}).get("max_interview_average", -1)):
        reasons.append(f"interview average {interview_average:.2f}")
    if confidence_after <= int(thresholds.get(priority, {}).get("max_confidence_after", -1)):
        reasons.append(f"post-session confidence {confidence_after}")
    if hint_level >= int(thresholds.get(priority, {}).get("min_hint_level_used", 10**9)):
        reasons.append(f"hint level {hint_level}")
    if confidence_delta <= int(thresholds.get(priority, {}).get("max_confidence_delta", -10**9)):
        reasons.append(f"confidence delta {confidence_delta}")

    reason = (
        f"Follow-up needed due to {', '.join(reasons)}; revisit main mistake: {record['main_mistake']}"
        if reasons
        else maintenance_reason
    )
    days_until_revision = int(priority_days.get(priority, 14))
    next_revision_date = completed_on + timedelta(days=days_until_revision)
    return priority, format_iso_date(next_revision_date), reason


def close_open_revision_entries(
    progress: JsonDict,
    problem_id: str,
) -> int:
    """Mark scheduled revisions for a problem as completed."""

    closed = 0
    entries = ensure_list(progress.get("revision_schedule"), "progress.revision_schedule")
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("problem") != problem_id or entry.get("status") not in OPEN_REVISION_STATUSES:
            continue
        entry["status"] = "completed"
        closed += 1
    return closed


def append_history_event(progress: JsonDict, event: JsonDict) -> None:
    """Append a structured history event."""

    history = ensure_list(progress.get("history"), "progress.history")
    history.append(event)


def confidence_trend(records: list[JsonDict]) -> JsonDict:
    """Return a compact confidence trend summary from completion records."""

    values = [
        float(record["confidence_after"])
        for record in records
        if isinstance(record.get("confidence_after"), (int, float))
    ]
    recent = values[-5:]
    previous = values[-10:-5]
    recent_average = round(mean(recent), 2) if recent else 0.0
    previous_average = round(mean(previous), 2) if previous else 0.0
    delta = round(recent_average - previous_average, 2)
    direction = "flat"
    if delta > 0.15:
        direction = "up"
    elif delta < -0.15:
        direction = "down"
    return {
        "recent_average": recent_average,
        "previous_average": previous_average,
        "delta": delta,
        "direction": direction,
        "recent_values": recent,
    }


def interview_trend(records: list[JsonDict]) -> JsonDict:
    """Return a compact interview-score trend summary from completion records."""

    values = [
        score
        for score in (average_interview_score(record) for record in records)
        if score is not None
    ]
    recent = values[-5:]
    previous = values[-10:-5]
    recent_average = round(mean(recent), 2) if recent else 0.0
    previous_average = round(mean(previous), 2) if previous else 0.0
    delta = round(recent_average - previous_average, 2)
    direction = "flat"
    if delta > 0.15:
        direction = "up"
    elif delta < -0.15:
        direction = "down"
    return {
        "recent_average": recent_average,
        "previous_average": previous_average,
        "delta": delta,
        "direction": direction,
        "recent_values": recent,
    }


def weakest_modules(state: RepositoryState, limit: int = 5) -> list[JsonDict]:
    """Return the weakest solved modules by average weighted thinking score."""

    latest_by_problem = latest_records_by_problem(state.progress)
    problems = problem_lookup(state.curriculum)
    grouped: dict[str, list[float]] = {}
    counts: dict[str, int] = {}
    for problem_id, record in latest_by_problem.items():
        problem = problems.get(problem_id)
        if problem is None:
            continue
        score = weighted_thinking_score(record, state.scoring)
        if score is None:
            continue
        module_name = str(problem["module"])
        grouped.setdefault(module_name, []).append(score)
        counts[module_name] = counts.get(module_name, 0) + 1
    results = [
        {
            "module": module_name,
            "average_weighted_thinking_score": round(mean(scores), 2),
            "solved_problems": counts[module_name],
        }
        for module_name, scores in grouped.items()
    ]
    return sorted(
        results,
        key=lambda item: (item["average_weighted_thinking_score"], item["module"]),
    )[:limit]
