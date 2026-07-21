#!/usr/bin/env python3
"""Shared repository utilities for DSA_OS command-line tools (skill-first engine)."""

from __future__ import annotations

import hashlib
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
SKILLS_PATH = ROOT / "knowledge" / "skills.json"
PATTERNS_PATH = ROOT / "knowledge" / "patterns.json"
SCORING_PATH = ROOT / "progress" / "scoring.json"
PROGRESS_PATH = ROOT / "progress" / "progress.json"
PROGRESS_TEMPLATE_PATH = ROOT / "progress" / "progress_template.json"

REVISION_INTERVAL_DAYS = {
    0: 3,   # R1 after the original solve.
    1: 7,   # R2 after successful R1.
    2: 21,  # R3 after successful R2.
    3: 60,  # R4 after successful R3.
}
REVISION_STATUSES = {"ACTIVE", "MASTERED", "FAILED"}
REVISION_RESULTS = {"PASS", "FAIL", "REACTIVATED"}
QUARTERLY_MAINTENANCE_DAYS = 90
QUARTERLY_MAINTENANCE_LIMIT = 3
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
IMPLEMENTATION_ENGINEERING_DEFAULT = {
    "score": 0,
    "strengths": [],
    "weaknesses": [],
    "common_errors": [],
    "improvement_notes": [],
}
DEFERRED_LEARNING_STATUSES = {"OPEN", "RESOLVED"}
DEFERRED_LEARNING_PRIORITIES = {"LOW", "MEDIUM", "HIGH"}
DEFERRED_LEARNING_CATEGORIES = {
    "implementation_engineering",
    "invariant_reasoning",
    "proof",
    "boundary_conditions",
    "initialization",
    "optimization",
    "complexity",
    "pattern_recognition",
    "interview_communication",
    "language_syntax",
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
    skills: JsonDict
    patterns: JsonDict
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
    """Load curriculum, graph, stages, skills, scoring, and progress state."""

    progress_path = resolve_progress_path(explicit_progress_path)
    progress = load_json_file(progress_path)
    migrate_progress_payload(progress)
    return RepositoryState(
        curriculum=load_json_file(CURRICULUM_PATH),
        graph=load_json_file(GRAPH_PATH),
        stages=load_json_file(STAGES_PATH),
        skills=load_json_file(SKILLS_PATH),
        patterns=load_json_file(PATTERNS_PATH),
        scoring=load_json_file(SCORING_PATH),
        progress=progress,
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


def skill_lookup(skills: JsonDict) -> dict[str, JsonDict]:
    """Return skills keyed by skill id."""

    data = skills.get("skills")
    if not isinstance(data, dict):
        raise RepositoryError("knowledge/skills.json: `skills` must be an object.")
    return data


def is_global_skill(skill: JsonDict) -> bool:
    """Return whether a skill is a cross-cutting competency, not a stage skill."""

    return skill.get("scope") == "global"


def problem_dependencies_map(graph: JsonDict) -> dict[str, list[str]]:
    """Return the auto-generated problem-level dependency map."""

    deps = graph.get("problem_dependencies")
    if not isinstance(deps, dict):
        raise RepositoryError("dependency_graph.json: `problem_dependencies` must be an object.")
    return deps


def skill_dependencies_map(graph: JsonDict) -> dict[str, list[str]]:
    """Return the skill-level dependency map (source of truth)."""

    deps = graph.get("skill_dependencies")
    if not isinstance(deps, dict):
        raise RepositoryError("dependency_graph.json: `skill_dependencies` must be an object.")
    return deps


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


def deferred_learning_entries(progress: JsonDict) -> list[JsonDict]:
    """Return deferred learning entries in append order."""

    entries = progress.setdefault("deferred_learnings", [])
    if not isinstance(entries, list):
        raise RepositoryError("`progress.deferred_learnings` must be a list.")
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise RepositoryError(
                f"`progress.deferred_learnings[{index}]` must be an object."
            )
    return entries


def open_deferred_learnings(progress: JsonDict) -> list[JsonDict]:
    """Return unresolved deferred learning entries."""

    return [
        entry
        for entry in deferred_learning_entries(progress)
        if entry.get("status") == "OPEN"
    ]


def next_deferred_learning_id(progress: JsonDict) -> str:
    """Return the next deterministic deferred learning id."""

    max_id = 0
    for entry in deferred_learning_entries(progress):
        raw_id = entry.get("id")
        if not isinstance(raw_id, str) or not raw_id.startswith("DL-"):
            continue
        try:
            max_id = max(max_id, int(raw_id.removeprefix("DL-")))
        except ValueError:
            continue
    return f"DL-{max_id + 1:03d}"


def create_deferred_learning(
    progress: JsonDict,
    *,
    origin_problem: str,
    origin_revision_stage: int | None,
    skill: str,
    category: str,
    description: str,
    priority: str,
    created_on: date,
) -> JsonDict:
    """Append an open deferred learning entry to progress state."""

    category = category.strip()
    priority = priority.strip().upper()
    description = description.strip()
    if category not in DEFERRED_LEARNING_CATEGORIES:
        raise RepositoryError(
            f"Unknown deferred learning category `{category}`. "
            f"Allowed: {', '.join(sorted(DEFERRED_LEARNING_CATEGORIES))}."
        )
    if priority not in DEFERRED_LEARNING_PRIORITIES:
        raise RepositoryError(
            f"Unknown deferred learning priority `{priority}`. "
            f"Allowed: {', '.join(sorted(DEFERRED_LEARNING_PRIORITIES))}."
        )
    if not description:
        raise RepositoryError("Deferred learning description must not be empty.")

    entry = {
        "id": next_deferred_learning_id(progress),
        "origin_problem": origin_problem,
        "origin_revision_stage": origin_revision_stage,
        "skill": skill,
        "category": category,
        "description": description,
        "priority": priority,
        "status": "OPEN",
        "created_on": format_iso_date(created_on),
        "resolved_on": None,
        "resolved_by_problem": None,
        "evidence": None,
    }
    deferred_learning_entries(progress).append(entry)
    return entry


def resolve_deferred_learning(
    progress: JsonDict,
    *,
    learning_id: str,
    resolved_on: date,
    resolved_by_problem: str,
    evidence: str,
) -> JsonDict:
    """Resolve a deferred learning with explicit future evidence."""

    evidence = evidence.strip()
    if not evidence:
        raise RepositoryError("Resolving deferred learning requires non-empty evidence.")
    for entry in deferred_learning_entries(progress):
        if entry.get("id") != learning_id:
            continue
        if entry.get("status") == "RESOLVED":
            raise RepositoryError(f"Deferred learning `{learning_id}` is already resolved.")
        entry["status"] = "RESOLVED"
        entry["resolved_on"] = format_iso_date(resolved_on)
        entry["resolved_by_problem"] = resolved_by_problem
        entry["evidence"] = evidence
        return entry
    raise RepositoryError(f"Unknown deferred learning id `{learning_id}`.")


def current_problem_id(progress: JsonDict) -> str | None:
    """Return the active current problem id if present."""

    value = progress.get("current_problem")
    return value if isinstance(value, str) else None


def last_completion_record(progress: JsonDict) -> JsonDict | None:
    """Return the most recently appended completion record."""

    records = completed_records(progress)
    return records[-1] if records else None


def revision_stage_label(stage: int) -> str:
    """Return the next revision label for a completed revision stage count."""

    return "MASTERED" if stage >= 4 else f"R{stage + 1}"


def initial_revision_state(completed_on: date) -> JsonDict:
    """Create revision state for a newly solved problem."""

    return {
        "status": "ACTIVE",
        "stage": 0,
        "completed": [],
        "next_due": format_iso_date(completed_on + timedelta(days=REVISION_INTERVAL_DAYS[0])),
        "history": [],
    }


def migrate_progress_payload(payload: JsonDict) -> JsonDict:
    """Upgrade old date-queue progress payloads to per-problem revision state in memory."""

    schema_version = int(payload.get("schema_version", 0) or 0)
    legacy_schedule = payload.pop("revision_schedule", []) if schema_version < 6 else []
    scheduled_by_problem: dict[str, list[JsonDict]] = {}
    if isinstance(legacy_schedule, list):
        for entry in legacy_schedule:
            if isinstance(entry, dict) and isinstance(entry.get("problem"), str):
                scheduled_by_problem.setdefault(entry["problem"], []).append(entry)

    for record in completed_records(payload):
        completed_at_raw = record.get("completed_at")
        try:
            completed_on = (
                parse_iso_date(completed_at_raw, "completed_at")
                if isinstance(completed_at_raw, str)
                else date.today()
            )
        except RepositoryError:
            completed_on = date.today()

        if not isinstance(record.get("revision"), dict):
            next_due = record.pop("next_revision_date", None)
            scheduled_entries = scheduled_by_problem.get(str(record.get("problem_id")), [])
            if not isinstance(next_due, str) and scheduled_entries:
                next_due = scheduled_entries[-1].get("date")
            if not isinstance(next_due, str):
                next_due = format_iso_date(completed_on + timedelta(days=REVISION_INTERVAL_DAYS[0]))
            record["revision"] = {
                "status": "ACTIVE",
                "stage": 0,
                "completed": [],
                "next_due": next_due,
                "history": [],
            }
        else:
            record.pop("next_revision_date", None)
            record["revision"].setdefault("history", [])
            record["revision"].setdefault("completed", [])

        for event in record.get("revision", {}).get("history", []):
            if not isinstance(event, dict):
                continue
            rev_score = event.get("thinking_score")
            if isinstance(rev_score, dict):
                rev_score.setdefault("implementation_blueprint", rev_score.get("implementation", 0))
                rev_score.setdefault("code_from_memory", rev_score.get("implementation", 0))

        if "algorithm_thinking_score" not in record:
            score = weighted_thinking_score(record, {"weights": {
                "understanding": 0.18,
                "examples": 0.12,
                "brute_force": 0.12,
                "pattern_detection": 0.24,
                "algorithm_design": 0.24,
                "complexity_analysis": 0.10,
            }})
            record["algorithm_thinking_score"] = round((score or 0) * 2.5, 2)
        if "implementation_engineering_score" not in record:
            impl_score = record.get("thinking_score", {}).get("implementation")
            record["implementation_engineering_score"] = (
                round(float(impl_score) * 2.5, 2)
                if isinstance(impl_score, (int, float))
                else 0
            )

    implementation_engineering = payload.get("implementation_engineering")
    if not isinstance(implementation_engineering, dict):
        implementation_engineering = {}
        payload["implementation_engineering"] = implementation_engineering
    for key, default_value in IMPLEMENTATION_ENGINEERING_DEFAULT.items():
        if key == "score":
            if not isinstance(implementation_engineering.get(key), (int, float)):
                implementation_engineering[key] = default_value
        elif not isinstance(implementation_engineering.get(key), list):
            implementation_engineering[key] = list(default_value)
    if not isinstance(payload.get("deferred_learnings"), list):
        payload["deferred_learnings"] = []
    payload["schema_version"] = 8
    return payload


def revision_due_entries(progress: JsonDict, on_date: date) -> list[JsonDict]:
    """Return active/failed revision states due on or before the given date."""

    due_entries: list[JsonDict] = []
    for record in latest_records_by_problem(progress).values():
        revision = record.get("revision")
        if not isinstance(revision, dict):
            continue
        if revision.get("status") not in {"ACTIVE", "FAILED"}:
            continue
        raw_date = revision.get("next_due")
        if not isinstance(raw_date, str):
            continue
        if parse_iso_date(raw_date, "revision.next_due") <= on_date:
            stage = int(revision.get("stage", 0))
            is_reactivated = isinstance(revision.get("reactivated_on"), str)
            due_entries.append(
                {
                    "problem": record["problem_id"],
                    "date": raw_date,
                    "status": revision["status"],
                    "stage": stage,
                    "next_stage": min(stage + 1, 5),
                    "kind": "reactivation" if is_reactivated else "revision",
                    "reason": (
                        "Prerequisite reinforcement is due."
                        if is_reactivated
                        else
                        f"{revision_stage_label(stage)} recall is due."
                        if revision["status"] == "ACTIVE"
                        else f"{revision_stage_label(stage)} previously failed and must be retried."
                    ),
                }
            )
    return due_entries


def quarterly_maintenance_entries(progress: JsonDict, on_date: date) -> list[JsonDict]:
    """Return a deterministic small subset of mastered problems due for maintenance."""

    candidates: list[JsonDict] = []
    for record in latest_records_by_problem(progress).values():
        revision = record.get("revision")
        if not isinstance(revision, dict) or revision.get("status") != "MASTERED":
            continue
        anchor = revision.get("last_maintenance")
        completed = revision.get("completed")
        if not isinstance(anchor, str):
            if not isinstance(completed, list) or not completed:
                continue
            anchor = completed[-1]
        if not isinstance(anchor, str):
            continue
        if parse_iso_date(anchor, "revision.maintenance_anchor") + timedelta(
            days=QUARTERLY_MAINTENANCE_DAYS
        ) > on_date:
            continue
        digest = hashlib.sha256(f"{on_date.isoformat()}:{record['problem_id']}".encode()).hexdigest()
        candidates.append(
            {
                "problem": record["problem_id"],
                "date": on_date.isoformat(),
                "status": "MASTERED",
                "stage": int(revision.get("stage", 5)),
                "next_stage": 5,
                "kind": "quarterly_maintenance",
                "reason": "Quarterly maintenance recall is due.",
                "rank": digest,
            }
        )
    return sorted(candidates, key=lambda entry: (entry["rank"], entry["problem"]))[
        :QUARTERLY_MAINTENANCE_LIMIT
    ]


def open_revision_entries(progress: JsonDict) -> list[JsonDict]:
    """Return active revision states, including overdue and future entries."""

    entries: list[JsonDict] = []
    for record in latest_records_by_problem(progress).values():
        revision = record.get("revision")
        if not isinstance(revision, dict) or revision.get("status") not in {"ACTIVE", "FAILED"}:
            continue
        next_due = revision.get("next_due")
        if not isinstance(next_due, str):
            continue
        stage = int(revision.get("stage", 0))
        is_reactivated = isinstance(revision.get("reactivated_on"), str)
        entries.append(
            {
                "problem": record["problem_id"],
                "date": next_due,
                "status": revision["status"],
                "stage": stage,
                "next_stage": min(stage + 1, 5),
                "kind": "reactivation" if is_reactivated else "revision",
                "reason": (
                    "Prerequisite reinforcement is scheduled."
                    if is_reactivated
                    else f"{revision_stage_label(stage)} recall is scheduled."
                ),
            }
        )
    return entries


def open_revision_entries_due_on_or_before(progress: JsonDict, on_date: date) -> list[JsonDict]:
    """Return actionable revision and maintenance entries due on or before the given date."""

    return revision_due_entries(progress, on_date) + quarterly_maintenance_entries(progress, on_date)


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


def hint_mastery_weight(hint_level: object, scoring: JsonDict) -> float:
    """Return the mastery-evidence weight for a completion's hint_level_used.

    Read from `scoring.json`'s `hint_mastery_discount` map (keyed by hint
    level as a string) so the discount table lives in one place. Unknown or
    missing hint levels default to full weight (1.0) rather than silently
    zeroing out older records that predate this field.
    """

    discounts = scoring.get("hint_mastery_discount")
    if not isinstance(discounts, dict):
        return 1.0
    try:
        return float(discounts.get(str(int(hint_level)), 1.0))
    except (TypeError, ValueError):
        return 1.0


def average_interview_score(record: JsonDict) -> float | None:
    """Calculate the average interview score for a completion record."""

    scores = record.get("interview_score")
    if not isinstance(scores, dict) or not scores:
        return None
    try:
        return round(mean(float(value) for value in scores.values()), 4)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Skill mastery (item #11: the mentor unlocks new material on skill mastery,
# not merely problem completion).
# ---------------------------------------------------------------------------
def compute_skill_progress(
    curriculum: JsonDict,
    skills: JsonDict,
    scoring: JsonDict,
    progress: JsonDict,
) -> dict[str, JsonDict]:
    """Recompute per-skill mastery from completion records.

    A skill is mastered when its primary validation problem is solved at or
    above `scoring.skill_mastery.minimum_primary_weighted_score` AND at least
    one reinforcement problem for that skill has been completed.

    The primary problem's weighted thinking score is discounted by how much
    hinting it took (`scoring.hint_mastery_discount`, keyed by
    `hint_level_used`): hint 0-2 counts at full weight, hint 3-4 at half
    weight, hint 5+ at zero weight (an attempt only, never mastery). A
    completion with no numeric thinking score never passes the bar.
    """

    latest_by_problem = latest_records_by_problem(progress)
    mastery_cfg = scoring.get("skill_mastery", {})
    min_primary_score = float(mastery_cfg.get("minimum_primary_weighted_score", 2.6))
    require_reinforcement = bool(mastery_cfg.get("require_reinforcement_attempt", True))

    skill_progress: dict[str, JsonDict] = {}
    for skill_id, skill in skill_lookup(skills).items():
        if is_global_skill(skill):
            continue
        primary = skill.get("primary_validation_problem")
        reinforcement = skill.get("reinforcement_problems", [])
        primary_record = latest_by_problem.get(primary)
        primary_solved = primary_record is not None
        raw_primary_score = weighted_thinking_score(primary_record, scoring) if primary_record else None
        # A completion with no numeric thinking score does NOT pass the bar
        # (no more "provisionally passing" leniency).
        if raw_primary_score is None:
            primary_score = None
        else:
            weight = hint_mastery_weight(primary_record.get("hint_level_used"), scoring)
            primary_score = round(raw_primary_score * weight, 4)
        primary_meets_bar = primary_solved and primary_score is not None and primary_score >= min_primary_score
        reinforcement_done = any(r in latest_by_problem for r in reinforcement)
        mastered = primary_meets_bar and (reinforcement_done or not require_reinforcement)
        skill_progress[skill_id] = {
            "primary_solved": primary_solved,
            "primary_weighted_score": primary_score,
            "reinforcement_attempted": reinforcement_done,
            "mastered": mastered,
        }
    return skill_progress


def compute_stage_mastery(stages: JsonDict, skill_progress: dict[str, JsonDict]) -> dict[str, JsonDict]:
    """Recompute per-stage mastery from skill mastery."""

    stage_order = ensure_list(stages.get("stage_order"), "stages.stage_order")
    stage_defs = stages.get("stages", {})
    result: dict[str, JsonDict] = {}
    unlocked = True
    for stage_name in stage_order:
        stage_skills = stage_defs.get(stage_name, {}).get("skills", [])
        total = len(stage_skills)
        mastered = sum(1 for sid in stage_skills if skill_progress.get(sid, {}).get("mastered"))
        if not unlocked:
            status = "locked"
        elif total > 0 and mastered == total:
            status = "mastered"
        else:
            status = "in_progress"
        result[stage_name] = {"status": status, "skills_mastered": mastered, "skills_total": total}
        if status != "mastered":
            unlocked = False
    return result


def determine_stage(progress: JsonDict, stages: JsonDict, scoring: JsonDict, skills: JsonDict | None = None) -> str:
    """Determine the learner's current stage: earliest non-mastered stage in order."""

    stage_order = ensure_list(stages.get("stage_order"), "stages.stage_order")
    stage_mastery = progress.get("stage_mastery")
    if isinstance(stage_mastery, dict) and stage_mastery:
        for stage_name in stage_order:
            status = stage_mastery.get(stage_name, {}).get("status")
            if status != "mastered":
                return stage_name
        return stage_order[-1]
    return stage_order[0]


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
    skill_progress = compute_skill_progress(state.curriculum, state.skills, state.scoring, payload)
    payload["skill_progress"] = skill_progress
    payload["mastered_skills"] = [sid for sid, sp in skill_progress.items() if sp["mastered"]]
    stage_mastery = compute_stage_mastery(state.stages, skill_progress)
    payload["stage_mastery"] = stage_mastery
    total_skills = len(skill_progress)
    payload["competency_completion"] = {
        "mastered_skills": len(payload["mastered_skills"]),
        "total_skills": total_skills,
        "percent": round(100 * len(payload["mastered_skills"]) / total_skills, 2) if total_skills else 0.0,
    }
    payload["current_stage"] = determine_stage(payload, state.stages, state.scoring, state.skills)
    return payload


def derive_current_skill_id(state: RepositoryState) -> str | None:
    """Infer the active skill from the current problem or latest solved work."""

    problems = problem_lookup(state.curriculum)

    active_problem_id = current_problem_id(state.progress)
    if active_problem_id and active_problem_id in problems:
        return problems[active_problem_id].get("primary_skill")

    latest_record = last_completion_record(state.progress)
    if latest_record and isinstance(latest_record.get("problem_id"), str):
        latest_problem = problems.get(latest_record["problem_id"])
        if latest_problem:
            return latest_problem.get("primary_skill")

    return None


def is_problem_unlocked(problem: JsonDict, completed_ids: set[str], problem_deps: dict[str, list[str]]) -> bool:
    """Return whether a curriculum problem is unlocked for first-pass solving."""

    dependencies = problem_deps.get(problem["id"], [])
    if not isinstance(dependencies, list):
        return False
    return all(isinstance(dep, str) and dep in completed_ids for dep in dependencies)


def select_next_problem(state: RepositoryState, on_date: date | None = None) -> SelectionResult:
    """Choose the next problem using revisions, skill continuity, and stage order."""

    today = on_date or date.today()
    problems = ensure_list(state.curriculum.get("problems"), "curriculum.problems")
    problems_by_id = problem_lookup(state.curriculum)
    problem_order = problem_order_index(state.curriculum)
    problem_deps = problem_dependencies_map(state.graph)
    stage_order = ensure_list(state.stages.get("stage_order"), "stages.stage_order")
    stage_defs = state.stages.get("stages")
    if not isinstance(stage_defs, dict):
        raise RepositoryError("stages.json: `stages` must be an object.")

    due_revisions = open_revision_entries_due_on_or_before(state.progress, today)
    if due_revisions:
        sorted_due = sorted(
            due_revisions,
            key=lambda entry: (
                {"reactivation": 0, "revision": 1, "quarterly_maintenance": 2}.get(
                    str(entry.get("kind")),
                    3,
                ),
                parse_iso_date(entry["date"], "revision.date"),
                int(entry.get("stage", 0)),
                problem_order.get(str(entry.get("problem")), 10**9),
            ),
        )
        chosen_entry = sorted_due[0]
        chosen_problem = problems_by_id.get(str(chosen_entry["problem"]))
        if chosen_problem is None:
            raise RepositoryError(
                f"Revision state references missing problem `{chosen_entry['problem']}`."
            )
        due_date = parse_iso_date(chosen_entry["date"], "revision.date")
        if chosen_entry.get("kind") == "quarterly_maintenance":
            reason = "Quarterly maintenance recall is due and takes priority over new work."
        elif chosen_entry.get("kind") == "reactivation":
            reason = "Prerequisite reinforcement is due and takes priority over new work."
        else:
            reason = "Revision is overdue." if due_date < today else (
                "Revision is due today and takes priority over new work."
            )
        return SelectionResult(
            mode=str(chosen_entry.get("kind", "revision_due")),
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
        and is_problem_unlocked(problem, completed_ids, problem_deps)
    ]

    active_problem_id = current_problem_id(state.progress)
    if active_problem_id and active_problem_id in problems_by_id and active_problem_id not in completed_ids:
        active_problem = problems_by_id[active_problem_id]
        if is_problem_unlocked(active_problem, completed_ids, problem_deps):
            return SelectionResult(
                mode="resume_current_problem",
                reason="Current problem is still active and remains unlocked.",
                problem=active_problem,
                suggested_stage=active_problem.get("stage"),
            )

    current_skill_id = derive_current_skill_id(state)
    if current_skill_id:
        current_skill_candidates = [
            problem for problem in incomplete_unlocked if problem.get("primary_skill") == current_skill_id
        ]
        if current_skill_candidates:
            chosen_problem = sorted(
                current_skill_candidates,
                key=lambda problem: problem_order[problem["id"]],
            )[0]
            return SelectionResult(
                mode="current_skill",
                reason="Continuing in the current skill preserves local reasoning context.",
                problem=chosen_problem,
                suggested_stage=chosen_problem.get("stage"),
            )

    current_stage = state.progress.get("current_stage")
    if not isinstance(current_stage, str) or current_stage not in stage_order:
        current_stage = stage_order[0]
    stage_skill_ids = set(stage_defs[current_stage]["skills"])
    stage_candidates = [
        problem for problem in incomplete_unlocked if problem.get("primary_skill") in stage_skill_ids
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


def apply_revision_result(
    record: JsonDict,
    result: str,
    completed_on: date,
    confidence: int,
    hint_level: int,
    revision_score: JsonDict,
    force_pass_reason: str | None = None,
) -> JsonDict:
    """Apply a PASS/FAIL revision result to a completion record's revision state.

    `force_pass_reason`: F5 lets the CLI override a below-pass_minimum average
    revision score via --force-pass; when set, the reason is recorded on the
    history event so a forced pass is auditable later.
    """

    if result not in REVISION_RESULTS:
        raise RepositoryError("Revision result must be PASS or FAIL.")
    revision = record.get("revision")
    if not isinstance(revision, dict):
        completed_at = parse_iso_date(str(record["completed_at"]), "completed_at")
        revision = initial_revision_state(completed_at)
        record["revision"] = revision

    current_stage = int(revision.get("stage", 0))
    prior_status = str(revision.get("status", "ACTIVE"))
    maintenance = prior_status == "MASTERED"
    attempted_stage = 5 if maintenance else min(current_stage + 1, 5)
    event_stage = attempted_stage if result == "PASS" else (3 if maintenance else current_stage)
    event = {
        "date": format_iso_date(completed_on),
        "result": result,
        "stage": event_stage,
        "attempted_stage": attempted_stage,
        "confidence": confidence,
        "hint_level": hint_level,
        "thinking_score": revision_score,
    }
    if force_pass_reason:
        event["force_pass_reason"] = force_pass_reason
    revision.setdefault("history", []).append(event)

    if maintenance:
        if result == "PASS":
            revision["status"] = "MASTERED"
            revision["stage"] = 5
            revision["next_due"] = None
            revision["last_maintenance"] = format_iso_date(completed_on)
            revision.pop("reactivated_on", None)
        else:
            revision["status"] = "ACTIVE"
            revision["stage"] = 3
            completed = revision.get("completed")
            if isinstance(completed, list):
                revision["completed"] = completed[:3]
            else:
                revision["completed"] = []
            revision["next_due"] = format_iso_date(completed_on + timedelta(days=1))
            revision.pop("last_maintenance", None)
            revision.pop("reactivated_on", None)
        return event

    if result == "PASS":
        revision.setdefault("completed", []).append(format_iso_date(completed_on))
        revision["stage"] = attempted_stage
        if attempted_stage >= 4:
            revision["status"] = "MASTERED"
            revision["next_due"] = None
            revision["last_maintenance"] = format_iso_date(completed_on)
            revision.pop("reactivated_on", None)
        else:
            revision["status"] = "ACTIVE"
            revision["next_due"] = format_iso_date(
                completed_on + timedelta(days=REVISION_INTERVAL_DAYS[attempted_stage])
            )
            revision.pop("reactivated_on", None)
    else:
        revision["status"] = "FAILED"
        revision["stage"] = current_stage
        revision["next_due"] = format_iso_date(completed_on + timedelta(days=1))
        revision.pop("last_maintenance", None)
        revision.pop("reactivated_on", None)
    return event


def reactivate_revision(
    record: JsonDict,
    activated_on: date,
    reason: str,
) -> JsonDict:
    """Schedule a problem for prerequisite/concept reinforcement."""

    revision = record.get("revision")
    if not isinstance(revision, dict):
        completed_at = parse_iso_date(str(record["completed_at"]), "completed_at")
        revision = initial_revision_state(completed_at)
        record["revision"] = revision

    prior_status = str(revision.get("status", "ACTIVE"))
    prior_stage = int(revision.get("stage", 0))
    new_stage = 3 if prior_status == "MASTERED" else min(prior_stage, 3)
    completed = revision.get("completed")
    revision["status"] = "ACTIVE"
    revision["stage"] = new_stage
    revision["completed"] = completed[:new_stage] if isinstance(completed, list) else []
    revision["next_due"] = format_iso_date(activated_on)
    revision["reactivated_on"] = format_iso_date(activated_on)
    revision.pop("last_maintenance", None)
    event = {
        "date": format_iso_date(activated_on),
        "result": "REACTIVATED",
        "stage": new_stage,
        "reason": reason,
        "prior_status": prior_status,
        "prior_stage": prior_stage,
    }
    revision.setdefault("history", []).append(event)
    return event


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


def weakest_skills(state: RepositoryState, limit: int = 5) -> list[JsonDict]:
    """Return the weakest solved skills by average weighted thinking score."""

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
        skill_id = str(problem["primary_skill"])
        grouped.setdefault(skill_id, []).append(score)
        counts[skill_id] = counts.get(skill_id, 0) + 1
    skills_data = skill_lookup(state.skills)
    results = [
        {
            "skill": skill_id,
            "skill_name": skills_data.get(skill_id, {}).get("name", skill_id),
            "average_weighted_thinking_score": round(mean(scores), 2),
            "solved_problems": counts[skill_id],
        }
        for skill_id, scores in grouped.items()
    ]
    return sorted(
        results,
        key=lambda item: (item["average_weighted_thinking_score"], item["skill"]),
    )[:limit]
