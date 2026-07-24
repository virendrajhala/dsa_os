#!/usr/bin/env python3
"""Shared repository utilities for DSA_OS command-line tools (skill-first engine)."""

from __future__ import annotations

import hashlib
import json
import math
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

REVISION_STATUSES = {"ACTIVE", "MASTERED", "FAILED"}
REVISION_RESULTS = {"PASS", "FAIL", "REACTIVATED"}

# Revision policy numbers live in progress/scoring.json `revision_policy`
# (single source of truth; `make validate` checks its coherence). These
# defaults exist only so a missing/corrupt scoring.json can't crash module
# import — they mirror the shipped config.
DEFAULT_REVISION_POLICY = {
    "successful_recall_intervals": {"R1": 3, "R2": 7, "R3": 21, "R4": 60},
    "mastered_after_stage": 4,
    "failure_retry_days": 1,
    "quarterly_maintenance_days": 90,
    "quarterly_maintenance_sample_size": 3,
    # Owner policy: how many due revisions may sit in the queue before recall
    # takes priority over new problems. At or below this, new work proceeds;
    # past it, revisions are served until the backlog drains back under.
    # 0 restores strict revision-first scheduling.
    "revision_backlog_threshold": 4,
}


def resolve_revision_policy(scoring):
    """Overlay scoring.json's `revision_policy` block on the defaults."""

    block = scoring.get("revision_policy") if isinstance(scoring, dict) else None
    if not isinstance(block, dict):
        block = {}
    merged = dict(DEFAULT_REVISION_POLICY)
    for key, default in DEFAULT_REVISION_POLICY.items():
        value = block.get(key, default)
        if key == "successful_recall_intervals":
            merged[key] = dict(value) if isinstance(value, dict) and value else dict(default)
        else:
            try:
                merged[key] = int(value)
            except (TypeError, ValueError):
                merged[key] = default
    return merged


def revision_intervals(policy):
    """Map `R1..Rn` interval config to 0-based revision stage indexes."""

    out = {}
    for name, days in policy["successful_recall_intervals"].items():
        try:
            out[int(str(name)[1:]) - 1] = int(days)
        except (TypeError, ValueError):
            continue
    return out


def _scoring_payload_for_policy(path=None):
    try:
        with (path or SCORING_PATH).open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        # ValueError covers JSONDecodeError and UnicodeDecodeError: a corrupt
        # config falls back to defaults; `make validate` reports it properly.
        return None
    return payload if isinstance(payload, dict) else None


REVISION_POLICY = resolve_revision_policy(_scoring_payload_for_policy())
REVISION_INTERVAL_DAYS = revision_intervals(REVISION_POLICY)
MASTERED_AFTER_STAGE = REVISION_POLICY["mastered_after_stage"]
FAILURE_RETRY_DAYS = REVISION_POLICY["failure_retry_days"]
QUARTERLY_MAINTENANCE_DAYS = REVISION_POLICY["quarterly_maintenance_days"]
QUARTERLY_MAINTENANCE_LIMIT = REVISION_POLICY["quarterly_maintenance_sample_size"]
REVISION_BACKLOG_THRESHOLD = REVISION_POLICY["revision_backlog_threshold"]
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
WEAKNESS_STATUSES = {"open", "resolved"}
WEAKNESS_SOURCES = {"session", "mock", "revision"}
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

# ---------------------------------------------------------------------------
# F10: weekend mock interviews. The five interviewer-rubric dimensions are
# each scored 1-4 (anchored descriptors live in
# `mentor/mock_interview_protocol.md`); the overall verdict uses an
# interviewer-style four-point scale.
# ---------------------------------------------------------------------------
MOCK_DIMENSIONS = {
    "problem_solving": "Approach discovery, decomposition, and recovery under time pressure.",
    "communication": "Structure, precision, and interviewer alignment while thinking aloud.",
    "code_quality": "Clean, correct, readable translation of a stable plan into code.",
    "testing": "Self-driven walkthrough, edge cases, and dry runs without prompting.",
    "time_management": "Pacing across clarify/approach/code/test within the 45-minute cap.",
}
MOCK_SCORE_MINIMUM = 1
MOCK_SCORE_MAXIMUM = 4
MOCK_VERDICTS = ("strong-hire", "hire", "no-hire", "strong-no-hire")

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
    scoring = load_json_file(SCORING_PATH)
    migrate_progress_payload(progress, scoring=scoring)
    return RepositoryState(
        curriculum=load_json_file(CURRICULUM_PATH),
        graph=load_json_file(GRAPH_PATH),
        stages=load_json_file(STAGES_PATH),
        skills=load_json_file(SKILLS_PATH),
        patterns=load_json_file(PATTERNS_PATH),
        scoring=scoring,
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


def is_meta_skill(skill: JsonDict) -> bool:
    """Return whether a skill is a problemless cross-cutting meta-skill
    (e.g. SK-IE-00 Implementation Engineering), not a problem-owning stage skill."""

    return skill.get("scope") == "meta"


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

    return "MASTERED" if stage >= MASTERED_AFTER_STAGE else f"R{stage + 1}"


def initial_revision_state(completed_on: date) -> JsonDict:
    """Create revision state for a newly solved problem."""

    return {
        "status": "ACTIVE",
        "stage": 0,
        "completed": [],
        "next_due": format_iso_date(completed_on + timedelta(days=REVISION_INTERVAL_DAYS[0])),
        "history": [],
    }


def normalize_weakness_entry(entry: Any) -> JsonDict:
    """Return a structured weakness entry from a legacy string or object.

    F20a: `weaknesses_detected` entries are objects
    `{"text", "status", "source", "resolved_on"}`. Legacy plain strings map by
    prefix — "Resolved: " -> status resolved, "Mock: " -> source mock,
    anything else -> open/session — so old data or hand edits never crash a
    reader. Unknown statuses/sources fall back to open/session.
    """

    if isinstance(entry, dict):
        status = entry.get("status")
        source = entry.get("source")
        resolved_on = entry.get("resolved_on")
        return {
            "text": str(entry.get("text", "")).strip(),
            "status": status if status in WEAKNESS_STATUSES else "open",
            "source": source if source in WEAKNESS_SOURCES else "session",
            "resolved_on": resolved_on if isinstance(resolved_on, str) else None,
        }

    text = str(entry).strip()
    status = "open"
    source = "session"
    if text.startswith("Resolved: "):
        status = "resolved"
        text = text.removeprefix("Resolved: ")
    elif text.startswith("Mock: "):
        source = "mock"
        text = text.removeprefix("Mock: ")
    return {"text": text, "status": status, "source": source, "resolved_on": None}


# Fallback for the algorithm_thinking_score backfill when scoring.json has no
# `algorithm_thinking.weights` block (F22: config lives in scoring.json).
DEFAULT_ALGORITHM_THINKING_WEIGHTS = {
    "understanding": 0.18,
    "examples": 0.12,
    "brute_force": 0.12,
    "pattern_detection": 0.24,
    "algorithm_design": 0.24,
    "complexity_analysis": 0.10,
}


def migrate_progress_payload(payload: JsonDict, scoring: JsonDict | None = None) -> JsonDict:
    """Upgrade old date-queue progress payloads to per-problem revision state in memory."""

    if scoring is None:
        try:
            scoring = load_json_file(SCORING_PATH)
        except RepositoryError:
            scoring = {}
    algorithm_weights = scoring.get("algorithm_thinking", {}).get("weights")
    if not isinstance(algorithm_weights, dict) or not algorithm_weights:
        algorithm_weights = DEFAULT_ALGORITHM_THINKING_WEIGHTS

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
            score = weighted_thinking_score(record, {"weights": algorithm_weights})
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

    # F20a: upgrade legacy weaknesses_detected strings to structured objects.
    detected = payload.get("weaknesses_detected")
    if isinstance(detected, dict):
        for problem_id, entries in detected.items():
            if isinstance(entries, list):
                detected[problem_id] = [normalize_weakness_entry(entry) for entry in entries]

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

    The primary problem's mastery bar is scaled by how much hinting it took
    (`scoring.hint_mastery_discount`, keyed by `hint_level_used`) instead of
    discounting the score itself: hint 0-2 leaves the bar unchanged (weight
    1.0), hint 3-4 raises it halfway to the scale maximum (weight 0.5), hint
    5+ makes mastery impossible regardless of score (weight 0, an attempt
    only). Scaling the bar rather than the score keeps every non-zero weight
    tier reachable - multiplying the score instead would let a low enough
    weight push the ceiling below the bar and silently collapse a tier. A
    completion with no numeric thinking score never passes the bar. The
    stored `primary_weighted_score` is always the raw (undiscounted) score.
    """

    latest_by_problem = latest_records_by_problem(progress)
    mastery_cfg = scoring.get("skill_mastery", {})
    min_primary_score = float(mastery_cfg.get("minimum_primary_weighted_score", 2.6))
    require_reinforcement = bool(mastery_cfg.get("require_reinforcement_attempt", True))

    skill_progress: dict[str, JsonDict] = {}
    for skill_id, skill in skill_lookup(skills).items():
        if is_meta_skill(skill):
            continue
        primary = skill.get("primary_validation_problem")
        reinforcement = skill.get("reinforcement_problems", [])
        primary_record = latest_by_problem.get(primary)
        primary_solved = primary_record is not None
        raw_primary_score = weighted_thinking_score(primary_record, scoring) if primary_record else None
        # A completion with no numeric thinking score does NOT pass the bar
        # (no more "provisionally passing" leniency).
        if raw_primary_score is None:
            primary_meets_bar = False
        else:
            weight = hint_mastery_weight(primary_record.get("hint_level_used"), scoring)
            if weight <= 0:
                # hint 5+ (zero weight): attempt only, never mastery.
                primary_meets_bar = False
            else:
                # Margin-scaled effective bar: raise the bar instead of
                # discounting the score. weight 1.0 -> bar unchanged; weight
                # 0.5 -> bar moves halfway to the scale max, so a strong
                # hint-3/4 solve can still master while a mediocre one can't.
                scale_max = float(scoring.get("scale", {}).get("maximum", 4))
                effective_bar = min_primary_score + (scale_max - min_primary_score) * (1 - weight)
                primary_meets_bar = raw_primary_score >= effective_bar
        primary_meets_bar = primary_solved and primary_meets_bar
        reinforcement_done = any(r in latest_by_problem for r in reinforcement)
        mastered = primary_meets_bar and (reinforcement_done or not require_reinforcement)
        skill_progress[skill_id] = {
            "primary_solved": primary_solved,
            "primary_weighted_score": raw_primary_score,
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
        # Problemless meta-skills (e.g. SK-IE-00) are registered under a stage but
        # are not tracked in skill_progress, so they never count toward mastery.
        stage_skills = [
            sid
            for sid in stage_defs.get(stage_name, {}).get("skills", [])
            if sid in skill_progress
        ]
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

    # F22: implementation_engineering.score is a running average over
    # completion records, not last-write-wins - recomputed here so the
    # validator's recompute-vs-cache check stays consistent.
    implementation_engineering = payload.get("implementation_engineering")
    if not isinstance(implementation_engineering, dict):
        implementation_engineering = {}
        payload["implementation_engineering"] = implementation_engineering
    engineering_scores = [
        float(record["implementation_engineering_score"])
        for record in completed_records(payload)
        if isinstance(record.get("implementation_engineering_score"), (int, float))
    ]
    implementation_engineering["score"] = (
        round(mean(engineering_scores), 2) if engineering_scores else 0
    )
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


def challenge_stage_gate(curriculum: JsonDict):
    """Return `is_unlocked(problem, completed_ids)` enforcing the challenge
    rule: a CHALLENGE problem opens only once every PRIMARY/REINFORCEMENT
    problem of its own stage is complete.

    Rationale: challenges name a single reinforcement as their dependency,
    so without this rule a stage's hardest problems unlock immediately after
    one easy problem — putting Hard problems in the learner's first handful
    of solves. Skill-level dependencies stay as they are; this only defers
    the challenge tail to the end of its stage.
    """

    problems = ensure_list(curriculum.get("problems"), "curriculum.problems")
    fundamentals: dict[str, set[str]] = {}
    for problem in problems:
        if not isinstance(problem, dict) or not isinstance(problem.get("id"), str):
            continue
        stage = problem.get("stage")
        fundamentals.setdefault(stage, set())
        if problem.get("problem_role") != "CHALLENGE":
            fundamentals[stage].add(problem["id"])

    def is_unlocked(problem: JsonDict, completed_ids: set[str]) -> bool:
        if problem.get("problem_role") != "CHALLENGE":
            return True
        return fundamentals.get(problem.get("stage"), set()) <= completed_ids

    return is_unlocked


def is_problem_unlocked(
    problem: JsonDict,
    completed_ids: set[str],
    problem_deps: dict[str, list[str]],
    challenge_gate=None,
) -> bool:
    """Return whether a curriculum problem is unlocked for first-pass solving."""

    dependencies = problem_deps.get(problem["id"], [])
    if not isinstance(dependencies, list):
        return False
    if challenge_gate is not None and not challenge_gate(problem, completed_ids):
        return False
    return all(isinstance(dep, str) and dep in completed_ids for dep in dependencies)


def mock_interview_entries(progress: JsonDict) -> list[JsonDict]:
    """Return recorded mock-interview entries in append order (optional field)."""

    entries = progress.get("mock_interviews", [])
    if not isinstance(entries, list):
        raise RepositoryError("`progress.mock_interviews` must be a list.")
    return [entry for entry in entries if isinstance(entry, dict)]


def weekend_window(on_date: date) -> tuple[date, date] | None:
    """Return the (Saturday, Sunday) window containing `on_date`, or None on a weekday."""

    weekday = on_date.weekday()  # Monday=0 .. Sunday=6
    if weekday == 5:  # Saturday
        return on_date, on_date + timedelta(days=1)
    if weekday == 6:  # Sunday
        return on_date - timedelta(days=1), on_date
    return None


def is_mock_due(progress: JsonDict, on_date: date) -> bool:
    """Return whether a weekend mock interview is due on `on_date`.

    A mock is due only on Saturday or Sunday, and only when no mock interview
    has already been recorded with a date inside the current Saturday-Sunday
    window (one mock per weekend minimum).
    """

    window = weekend_window(on_date)
    if window is None:
        return False
    saturday, sunday = window
    for entry in mock_interview_entries(progress):
        raw_date = entry.get("date")
        if not isinstance(raw_date, str):
            continue
        try:
            entry_date = parse_iso_date(raw_date, "mock_interviews.date")
        except RepositoryError:
            continue
        if saturday <= entry_date <= sunday:
            return False
    return True


def select_mock_problem(state: RepositoryState) -> tuple[JsonDict | None, str]:
    """Choose an unseen problem for a mock interview.

    Prefers a problem whose primary skill is mastered or adjacent (shares a
    stage with a mastered skill), never the current in-progress skill, and
    never an already-completed problem. When no skill is mastered yet, falls
    back to an unsolved reinforcement sibling of a completed problem, flagged
    as a "practice_mock". Returns (problem, kind) or (None, "").
    """

    progress = state.progress
    completed = completed_problem_ids(progress)
    problems = ensure_list(state.curriculum.get("problems"), "curriculum.problems")
    problems_by_id = problem_lookup(state.curriculum)
    order = problem_order_index(state.curriculum)
    skills = skill_lookup(state.skills)
    current_skill = derive_current_skill_id(state)

    mastered = [sid for sid in progress.get("mastered_skills", []) if isinstance(sid, str)]
    if mastered:
        mastered_stages = {
            skills.get(sid, {}).get("stage")
            for sid in mastered
            if isinstance(skills.get(sid), dict)
        }
        eligible_skills: set[str] = set()
        for sid, skill in skills.items():
            if is_meta_skill(skill):
                continue
            if sid in mastered or skill.get("stage") in mastered_stages:
                eligible_skills.add(sid)
        eligible_skills.discard(current_skill)
        candidates = [
            problem
            for problem in problems
            if isinstance(problem, dict)
            and isinstance(problem.get("id"), str)
            and problem["id"] not in completed
            # A revisit slot of a completed problem is the same problem seen
            # again — never "unseen" for a mock (protocol rule 5).
            and problem.get("revisit_of") not in completed
            and problem.get("primary_skill") in eligible_skills
        ]
        if candidates:
            chosen = sorted(candidates, key=lambda problem: order[problem["id"]])[0]
            return chosen, "mock"

    # Early-days fallback: an unsolved reinforcement sibling of a solved skill.
    practice: list[JsonDict] = []
    for sid, skill in skills.items():
        if is_meta_skill(skill):
            continue
        reinforcement = skill.get("reinforcement_problems") or []
        skill_touched = skill.get("primary_validation_problem") in completed or any(
            pid in completed for pid in reinforcement
        )
        if not skill_touched:
            continue
        for pid in reinforcement:
            if (
                pid not in completed
                and pid in problems_by_id
                and problems_by_id[pid].get("revisit_of") not in completed
            ):
                practice.append(problems_by_id[pid])
    if practice:
        chosen = sorted(practice, key=lambda problem: order[problem["id"]])[0]
        return chosen, "practice_mock"

    return None, ""


def select_next_problem(state: RepositoryState, on_date: date | None = None) -> SelectionResult:
    """Choose the next problem using revisions, skill continuity, and stage order."""

    today = on_date or date.today()
    problems = ensure_list(state.curriculum.get("problems"), "curriculum.problems")
    problems_by_id = problem_lookup(state.curriculum)
    problem_order = problem_order_index(state.curriculum)
    problem_deps = problem_dependencies_map(state.graph)
    challenge_gate = challenge_stage_gate(state.curriculum)
    stage_order = ensure_list(state.stages.get("stage_order"), "stages.stage_order")
    stage_defs = state.stages.get("stages")
    if not isinstance(stage_defs, dict):
        raise RepositoryError("stages.json: `stages` must be an object.")

    due_revisions = open_revision_entries_due_on_or_before(state.progress, today)
    # A small ordinary-recall backlog no longer blocks forward progress: new
    # work proceeds while the due queue is at or under the configured
    # threshold. The queue itself is untouched, so revision_report.py and the
    # dashboard keep showing every due item.
    #
    # Two kinds are never deferred. A reactivation is a targeted response to a
    # demonstrated weak prerequisite, and quarterly maintenance is generated
    # fresh each day for mastered problems and capped at the daily sample size
    # — it cannot accumulate, so a threshold would stop it firing at all
    # rather than merely delaying it.
    backlog_threshold = resolve_revision_policy(state.scoring)["revision_backlog_threshold"]
    undeferrable = {"reactivation", "quarterly_maintenance"}
    priority_due = [e for e in due_revisions if str(e.get("kind")) in undeferrable]
    if priority_due:
        due_revisions = priority_due
    if due_revisions and (priority_due or len(due_revisions) > backlog_threshold):
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
            # The backlog note only means something when a threshold is
            # actually deferring work; at 0 the policy is plain revision-first.
            backlog_note = (
                f" Recall backlog is {len(due_revisions)}, over the threshold of "
                f"{backlog_threshold}, so revisions take priority until it drains."
                if backlog_threshold > 0
                else " Revisions take priority over new work."
            )
            reason = ("Revision is overdue." if due_date < today else
                      "Revision is due today.") + backlog_note
        return SelectionResult(
            # Fallback must be a real kind name ("revision"), not the old
            # "revision_due" string that matched nothing downstream (F22).
            mode=str(chosen_entry.get("kind", "revision")),
            reason=reason,
            problem=chosen_problem,
            suggested_stage=chosen_problem.get("stage"),
            revision_entry=chosen_entry,
        )

    # F10: on a weekend with no mock recorded this Sat-Sun window, a mock
    # interview outranks new work but never an overdue revision (handled above).
    if is_mock_due(state.progress, today):
        mock_problem, mock_kind = select_mock_problem(state)
        if mock_problem is not None:
            if mock_kind == "practice_mock":
                reason = (
                    "Weekend mock interview is due. No skill is fully mastered yet, so this is a "
                    "practice mock on an unsolved reinforcement sibling of a completed problem."
                )
            else:
                reason = (
                    "Weekend mock interview is due and outranks new work (overdue revisions still "
                    "come first). Problem drawn from a mastered or adjacent skill, never the "
                    "current in-progress skill. See mentor/mock_interview_protocol.md."
                )
            return SelectionResult(
                mode="mock_due",
                reason=reason,
                problem=mock_problem,
                suggested_stage=mock_problem.get("stage"),
            )

    completed_ids = completed_problem_ids(state.progress)
    incomplete_unlocked = [
        problem
        for problem in problems
        if isinstance(problem, dict)
        and isinstance(problem.get("id"), str)
        and problem["id"] not in completed_ids
        and is_problem_unlocked(problem, completed_ids, problem_deps, challenge_gate)
    ]

    active_problem_id = current_problem_id(state.progress)
    if active_problem_id and active_problem_id in problems_by_id and active_problem_id not in completed_ids:
        active_problem = problems_by_id[active_problem_id]
        if is_problem_unlocked(active_problem, completed_ids, problem_deps, challenge_gate):
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
    policy: JsonDict | None = None,
) -> JsonDict:
    """Apply a PASS/FAIL revision result to a completion record's revision state.

    `force_pass_reason`: F5 lets the CLI override a below-pass_minimum average
    revision score via --force-pass; when set, the reason is recorded on the
    history event so a forced pass is auditable later.

    `policy`: resolved revision policy (see resolve_revision_policy); defaults
    to the module-level REVISION_POLICY read from progress/scoring.json.
    """

    if policy is None:
        policy = REVISION_POLICY
    intervals = revision_intervals(policy)
    mastered_after = int(policy["mastered_after_stage"])
    retry = timedelta(days=int(policy["failure_retry_days"]))

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
    beyond_mastery = mastered_after + 1
    demoted_stage = mastered_after - 1
    attempted_stage = beyond_mastery if maintenance else min(current_stage + 1, beyond_mastery)
    event_stage = attempted_stage if result == "PASS" else (demoted_stage if maintenance else current_stage)
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
            revision["stage"] = beyond_mastery
            revision["next_due"] = None
            revision["last_maintenance"] = format_iso_date(completed_on)
            revision.pop("reactivated_on", None)
        else:
            revision["status"] = "ACTIVE"
            revision["stage"] = demoted_stage
            completed = revision.get("completed")
            if isinstance(completed, list):
                revision["completed"] = completed[:demoted_stage]
            else:
                revision["completed"] = []
            revision["next_due"] = format_iso_date(completed_on + retry)
            revision.pop("last_maintenance", None)
            revision.pop("reactivated_on", None)
        return event

    if result == "PASS":
        revision.setdefault("completed", []).append(format_iso_date(completed_on))
        revision["stage"] = attempted_stage
        if attempted_stage >= mastered_after:
            revision["status"] = "MASTERED"
            revision["next_due"] = None
            revision["last_maintenance"] = format_iso_date(completed_on)
            revision.pop("reactivated_on", None)
        else:
            revision["status"] = "ACTIVE"
            if attempted_stage not in intervals:
                raise RepositoryError(
                    f"scoring.json revision_policy has no interval for stage R{attempted_stage + 1}; "
                    "successful_recall_intervals must cover R1.."
                    f"R{int(policy['mastered_after_stage'])}."
                )
            # Scheduling is absolute: the next revision is due a fixed number
            # of days after the ORIGINAL solve, not a gap after this recall
            # (revision_policy.successful_recall_intervals are cumulative
            # offsets from the solve). A floor of one day past this completion
            # keeps a late learner from having two stages fall due the same day.
            solve_date = parse_iso_date(str(record["completed_at"]), "completed_at")
            absolute_due = solve_date + timedelta(days=intervals[attempted_stage])
            revision["next_due"] = format_iso_date(
                max(absolute_due, completed_on + timedelta(days=1))
            )
            revision.pop("reactivated_on", None)
    else:
        revision["status"] = "FAILED"
        revision["stage"] = current_stage
        revision["next_due"] = format_iso_date(completed_on + retry)
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


def revision_adjusted_problem_score(record: JsonDict, scoring: JsonDict) -> float | None:
    """Blend the latest revision recall average into a completion's score.

    F20b: the original solve score alone goes stale once revisions exist.
    When the record's revision history has recall scores, return
    `0.6 x latest-revision-recall-average + 0.4 x solve score`. Recall scores
    are 0-10 while thinking scores are 0-4, so the recall average is scaled
    by 0.4 first. Without recall scores this is exactly the solve score.
    """

    solve_score = weighted_thinking_score(record, scoring)
    if solve_score is None:
        return None
    revision = record.get("revision")
    history = revision.get("history") if isinstance(revision, dict) else None
    if not isinstance(history, list):
        return solve_score
    for event in reversed(history):
        if not isinstance(event, dict):
            continue
        recall = event.get("thinking_score")
        if not isinstance(recall, dict):
            continue
        values = [float(v) for v in recall.values() if isinstance(v, (int, float))]
        if not values:
            continue
        recall_on_thinking_scale = mean(values) * 0.4
        return round(0.6 * recall_on_thinking_scale + 0.4 * solve_score, 4)
    return solve_score


def weakest_skills(state: RepositoryState, limit: int = 5) -> list[JsonDict]:
    """Return the weakest solved skills by average weighted thinking score,
    blended with revision recall via `revision_adjusted_problem_score`."""

    latest_by_problem = latest_records_by_problem(state.progress)
    problems = problem_lookup(state.curriculum)
    grouped: dict[str, list[float]] = {}
    counts: dict[str, int] = {}
    for problem_id, record in latest_by_problem.items():
        problem = problems.get(problem_id)
        if problem is None:
            continue
        score = revision_adjusted_problem_score(record, state.scoring)
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


# ---------------------------------------------------------------------------
# F23: system-derived interview-readiness estimator. Reads scoring.json's
# `readiness` block so thresholds stay editable without code. Readiness gates
# nothing - it is recomputed every run and is purely informational.
# ---------------------------------------------------------------------------
def core_skill_ids_in_scope(
    curriculum: JsonDict,
    stages: JsonDict,
    skills: JsonDict,
    readiness_cfg: JsonDict,
) -> set[str]:
    """Return the "CORE skills in scope" set for the readiness estimator.

    A skill is in scope when its stage is one of the first
    `readiness.stage_scope_count` stages of `stages.stage_order` (config-driven,
    so a later stage reorder keeps working) AND at least one curriculum
    problem with `importance == "CORE"` maps to it via `primary_skill`.
    """

    stage_order = ensure_list(stages.get("stage_order"), "stages.stage_order")
    scope_count = int(readiness_cfg.get("stage_scope_count", len(stage_order)))
    scope_stages = set(stage_order[:scope_count])

    problems = ensure_list(curriculum.get("problems"), "curriculum.problems")
    core_skills_from_problems = {
        problem.get("primary_skill")
        for problem in problems
        if isinstance(problem, dict)
        and problem.get("importance") == "CORE"
        and isinstance(problem.get("primary_skill"), str)
    }

    return {
        skill_id
        for skill_id, skill in skill_lookup(skills).items()
        if not is_meta_skill(skill)
        and skill.get("stage") in scope_stages
        and skill_id in core_skills_from_problems
    }


def compute_core_mastery_status(
    skill_progress: dict[str, JsonDict],
    core_skill_ids: set[str],
) -> JsonDict:
    """Return mastered/total/fraction for the CORE-skills-in-scope set."""

    total = len(core_skill_ids)
    mastered = sum(1 for sid in core_skill_ids if skill_progress.get(sid, {}).get("mastered"))
    fraction = round(mastered / total, 4) if total else 0.0
    return {"mastered": mastered, "total": total, "fraction": fraction}


def compute_revision_pass_rate(progress: JsonDict) -> JsonDict:
    """Return the active-recall revision PASS rate: PASS / (PASS + FAIL).

    REACTIVATED events are excluded - they are a system-scheduled prerequisite
    reinforcement, not a graded recall attempt outcome (mirrors the existing
    dashboard "Revision impact" card in web_dashboard/app.js).
    """

    pass_count = 0
    total = 0
    for record in completed_records(progress):
        revision = record.get("revision")
        if not isinstance(revision, dict):
            continue
        history = revision.get("history")
        if not isinstance(history, list):
            continue
        for event in history:
            if not isinstance(event, dict):
                continue
            result = event.get("result")
            if result not in {"PASS", "FAIL"}:
                continue
            total += 1
            if result == "PASS":
                pass_count += 1
    fraction = round(pass_count / total, 4) if total else 0.0
    return {"pass": pass_count, "total": total, "fraction": fraction}


def compute_recent_mock_status(progress: JsonDict, readiness_cfg: JsonDict) -> JsonDict:
    """Return whether the last `recent_mock_count` mocks all cleared the verdict bar.

    Fewer than `recent_mock_count` recorded mocks means the criterion is
    structurally unmet regardless of verdicts.
    """

    entries = mock_interview_entries(progress)
    required = int(readiness_cfg.get("recent_mock_count", 3))
    allowed_verdicts = set(readiness_cfg.get("min_mock_verdicts", []))
    recent = entries[-required:] if entries else []
    met = len(entries) >= required and all(entry.get("verdict") in allowed_verdicts for entry in recent)
    return {
        "recorded": len(entries),
        "required": required,
        "recent_verdicts": [entry.get("verdict") for entry in recent],
        "met": met,
    }


def _completion_date(record: JsonDict | None) -> date | None:
    """Return the parsed `completed_at` date for a completion record, if valid."""

    if not isinstance(record, dict):
        return None
    completed_at = record.get("completed_at")
    if not isinstance(completed_at, str):
        return None
    try:
        return parse_iso_date(completed_at, "completed_at")
    except RepositoryError:
        return None


def skill_mastery_dates(
    skills: JsonDict,
    progress: JsonDict,
    skill_progress: dict[str, JsonDict],
) -> dict[str, date | None]:
    """Derive when each mastered skill was mastered, for pace calculations.

    Progress does not separately timestamp skill mastery, so this is derived
    (system-derived, per F23): mastery is reached the moment BOTH conditions
    are first satisfied - the primary validation problem is solved AND at
    least one reinforcement problem is solved - so the mastery date is
    `max(primary completion date, earliest reinforcement completion date)`.
    Skills that are not mastered, or are missing a dated primary/reinforcement
    completion, map to None.
    """

    latest_by_problem = latest_records_by_problem(progress)
    result: dict[str, date | None] = {}
    for skill_id, skill in skill_lookup(skills).items():
        if not skill_progress.get(skill_id, {}).get("mastered"):
            continue
        primary_date = _completion_date(latest_by_problem.get(skill.get("primary_validation_problem")))
        reinforcement_ids = skill.get("reinforcement_problems") or []
        reinforcement_dates = [
            d
            for d in (_completion_date(latest_by_problem.get(rid)) for rid in reinforcement_ids)
            if d is not None
        ]
        if primary_date is None or not reinforcement_dates:
            result[skill_id] = None
            continue
        result[skill_id] = max(primary_date, min(reinforcement_dates))
    return result


def compute_pace(
    progress: JsonDict,
    skills: JsonDict,
    skill_progress: dict[str, JsonDict],
    readiness_cfg: JsonDict,
    on_date: date,
) -> JsonDict:
    """Return problems/week and skills-mastered/week over the trailing pace window."""

    window_days = int(readiness_cfg.get("pace_window_days", 28))
    window_start = on_date - timedelta(days=max(window_days - 1, 0))

    problems_in_window = sum(
        1
        for record in completed_records(progress)
        if (completed_on := _completion_date(record)) is not None and window_start <= completed_on <= on_date
    )

    mastery_dates = skill_mastery_dates(skills, progress, skill_progress)
    skills_in_window = sum(
        1
        for mastered_on in mastery_dates.values()
        if mastered_on is not None and window_start <= mastered_on <= on_date
    )

    weeks = window_days / 7 if window_days else 0.0
    return {
        "window_days": window_days,
        "problems_in_window": problems_in_window,
        "skills_mastered_in_window": skills_in_window,
        "problems_per_week": round(problems_in_window / weeks, 4) if weeks else 0.0,
        "skills_mastered_per_week": round(skills_in_window / weeks, 4) if weeks else 0.0,
    }


def project_readiness_date(
    remaining_core_skills: int,
    skills_mastered_per_week: float,
    on_date: date,
) -> JsonDict:
    """Linearly extrapolate the binding constraint (skills-mastered pace vs
    remaining CORE skills needed) to a projected interview-ready date.
    Informational only - never gates anything.
    """

    if remaining_core_skills <= 0:
        return {
            "status": "core_mastery_met",
            "message": (
                "Core-skill mastery target is already met. Any remaining thresholds "
                "(revision pass rate, recent mock verdicts) do not accrue via pace."
            ),
        }
    if skills_mastered_per_week <= 0:
        return {
            "status": "no_pace",
            "message": "no projection yet (need consistent weekly activity)",
        }

    weeks_needed = remaining_core_skills / skills_mastered_per_week
    projected_date = on_date + timedelta(days=round(weeks_needed * 7))
    projected_iso = format_iso_date(projected_date)
    return {
        "status": "projected",
        "date": projected_iso,
        "message": f"interview-ready around {projected_iso}",
    }


def compute_readiness(
    curriculum: JsonDict,
    stages: JsonDict,
    skills: JsonDict,
    scoring: JsonDict,
    progress: JsonDict,
    on_date: date,
) -> JsonDict:
    """Compute the full F23 interview-readiness snapshot for a reference date."""

    readiness_cfg = scoring.get("readiness", {})
    core_fraction_target = float(readiness_cfg.get("core_skill_fraction", 0.8))
    pass_rate_target = float(readiness_cfg.get("revision_pass_rate", 0.9))

    core_skill_ids = core_skill_ids_in_scope(curriculum, stages, skills, readiness_cfg)
    skill_progress = compute_skill_progress(curriculum, skills, scoring, progress)
    core_status = compute_core_mastery_status(skill_progress, core_skill_ids)
    pass_status = compute_revision_pass_rate(progress)
    mock_status = compute_recent_mock_status(progress, readiness_cfg)
    pace = compute_pace(progress, skills, skill_progress, readiness_cfg, on_date)

    core_met = core_status["fraction"] >= core_fraction_target
    pass_met = pass_status["total"] > 0 and pass_status["fraction"] >= pass_rate_target
    mock_met = mock_status["met"]

    core_skills_needed = math.ceil(core_fraction_target * core_status["total"])
    remaining_core = max(core_skills_needed - core_status["mastered"], 0)
    projection = project_readiness_date(remaining_core, pace["skills_mastered_per_week"], on_date)

    return {
        "date": format_iso_date(on_date),
        "thresholds": {
            "core_skill_mastery": {
                "met": core_met,
                "actual": core_status["fraction"],
                "target": core_fraction_target,
                "mastered": core_status["mastered"],
                "total": core_status["total"],
            },
            "revision_pass_rate": {
                "met": pass_met,
                "actual": pass_status["fraction"],
                "target": pass_rate_target,
                "pass": pass_status["pass"],
                "total": pass_status["total"],
            },
            "recent_mocks": {
                "met": mock_met,
                "recorded": mock_status["recorded"],
                "required": mock_status["required"],
                "recent_verdicts": mock_status["recent_verdicts"],
            },
        },
        "pace": pace,
        "projection": projection,
        "all_met": core_met and pass_met and mock_met,
    }


# ---------------------------------------------------------------------------
# Dashboard feed: the single view model the web dashboard renders. Every value
# comes from the functions above (the same ones the CLI uses), so the browser
# can never contradict next_problem.py or revision_report.py. Design spec:
# plans/DASHBOARD_REDESIGN_DESIGN.md section 3. Pure function; JSON-serializable
# output; never mutates state.
# ---------------------------------------------------------------------------

_FORECAST_DAYS = 14


def _feed_queue_kind(raw_kind: object) -> str:
    """Normalize a due-entry kind to the feed contract (design section 3).

    `_shared` due-entry helpers emit `reactivation`; the feed/UI contract uses
    `reactivated`. `revision` and `quarterly_maintenance` pass through.
    """

    return "reactivated" if raw_kind == "reactivation" else str(raw_kind)


def _feed_queue_stage_label(kind: str, stage: int) -> str:
    """Pill text for a revision-queue row: the R-label for revisions, an
    explicit tag for maintenance so the R-scale is not misapplied."""

    if kind == "quarterly_maintenance":
        return "Q-maint"
    return revision_stage_label(stage)


def review_forecast(progress: JsonDict, on_date: date) -> list[JsonDict]:
    """A 14-day review-load forecast from `on_date`. Overdue open revisions
    fold into day 0 (flagged `overdue`); items due beyond the window are
    dropped. Sourced from `open_revision_entries` so it matches the scheduler's
    view of scheduled recall work.

    Quarterly maintenance due *now* is folded into day 0 as well: it is real
    load today and the due queue lists it, so leaving it out made the day-0 bar
    undercount the panel above it. Future maintenance stays out — it is derived
    from a 90-day anchor and is not projectable day by day.
    """

    buckets = [
        {
            "date": format_iso_date(on_date + timedelta(days=offset)),
            "count": 0,
            "overdue": False,
            "problem_ids": [],
        }
        for offset in range(_FORECAST_DAYS)
    ]
    for entry in open_revision_entries(progress):
        due = parse_iso_date(entry["date"], "revision.next_due")
        offset = (due - on_date).days
        if offset < 0:
            index = 0
            buckets[0]["overdue"] = True
        elif offset < _FORECAST_DAYS:
            index = offset
        else:
            continue
        bucket = buckets[index]
        bucket["count"] += 1
        bucket["problem_ids"].append(entry["problem"])

    day_zero = buckets[0]
    scheduled_today = set(day_zero["problem_ids"])
    for entry in quarterly_maintenance_entries(progress, on_date):
        problem_id = entry["problem"]
        if problem_id in scheduled_today:
            continue
        scheduled_today.add(problem_id)
        day_zero["count"] += 1
        day_zero["problem_ids"].append(problem_id)
    return buckets


def revision_calendar(state: RepositoryState, on_date: date) -> list[JsonDict]:
    """Project every active problem's full future revision chain, grouped by
    date, so the dashboard can show the recall load for any future day.

    The schedule is deterministic (absolute offsets from the solve), so each
    ACTIVE problem at stage N contributes one entry per remaining stage
    k in [N, mastered_after): due = solve + offset[k], labelled R(k+1). The
    entry for the problem's current stage is the real `next_due`
    (`projected: false`); later stages assume on-time passes
    (`projected: true`). FAIL retries, reactivations and quarterly maintenance
    cannot be projected and are not included — this is the planned calendar.
    """

    problems = problem_lookup(state.curriculum)
    intervals = revision_intervals(REVISION_POLICY)
    mastered_after = int(REVISION_POLICY["mastered_after_stage"])
    buckets: dict[str, list[JsonDict]] = {}

    for record in completed_records(state.progress):
        revision = record.get("revision")
        if not isinstance(revision, dict) or revision.get("status") == "MASTERED":
            continue
        completed_at = record.get("completed_at")
        if not isinstance(completed_at, str):
            continue
        solve = parse_iso_date(completed_at, "completed_at")
        current_stage = int(revision.get("stage", 0))
        problem = problems.get(record["problem_id"], {})
        for stage in range(current_stage, mastered_after):
            if stage not in intervals:
                continue
            due = solve + timedelta(days=intervals[stage])
            if due < on_date:
                continue
            key = format_iso_date(due)
            buckets.setdefault(key, []).append({
                "problem_id": record["problem_id"],
                "title": problem.get("title"),
                "stage_label": f"R{stage + 1}",
                "projected": stage != current_stage,
            })

    return [
        {"date": key, "items": sorted(buckets[key], key=lambda i: i["stage_label"])}
        for key in sorted(buckets)
    ]


def retention_split(progress: JsonDict) -> JsonDict:
    """Young (attempted at R1-R2) vs mature (R3+) active-recall pass rates,
    the Anki-style leading indicator (design section 2). Walks every completion
    record's revision history; only graded PASS/FAIL events count."""

    young_pass = young_total = mature_pass = mature_total = 0
    for record in completed_records(progress):
        revision = record.get("revision")
        if not isinstance(revision, dict):
            continue
        history = revision.get("history")
        if not isinstance(history, list):
            continue
        for event in history:
            if not isinstance(event, dict):
                continue
            result = event.get("result")
            if result not in {"PASS", "FAIL"}:
                continue
            attempted = event.get("attempted_stage")
            try:
                attempted_stage = int(attempted)
            except (TypeError, ValueError):
                continue
            is_pass = result == "PASS"
            if attempted_stage <= 2:
                young_total += 1
                young_pass += 1 if is_pass else 0
            else:
                mature_total += 1
                mature_pass += 1 if is_pass else 0

    overall_pass = young_pass + mature_pass
    overall_total = young_total + mature_total

    def _rate(passed: int, total: int) -> float | None:
        return round(passed / total, 4) if total else None

    return {
        "overall_pass_rate": _rate(overall_pass, overall_total),
        "young_pass_rate": _rate(young_pass, young_total),
        "mature_pass_rate": _rate(mature_pass, mature_total),
        "counts": {
            "young_pass": young_pass,
            "young_total": young_total,
            "mature_pass": mature_pass,
            "mature_total": mature_total,
        },
    }


def hint_trajectory_events(progress: JsonDict) -> list[JsonDict]:
    """Hint level per solve over time, oldest first (design section 4: hint
    independence). Display transform only; the discount tiers live in
    `scoring.json.hint_mastery_discount`."""

    events: list[JsonDict] = []
    for record in completed_records(progress):
        completed_on = _completion_date(record)
        if completed_on is None:
            continue
        hint_level = record.get("hint_level_used")
        try:
            hint_value = int(hint_level)
        except (TypeError, ValueError):
            continue
        events.append(
            {
                "date": format_iso_date(completed_on),
                "hint_level": hint_value,
                "problem_id": record.get("problem_id"),
            }
        )
    events.sort(key=lambda event: event["date"])
    return events


def _feed_mock_history(progress: JsonDict) -> list[JsonDict]:
    """Pass-through of recorded weekend mocks in append order (design section
    3). Verdict + five 1-4 rubric scores drive the Evidence mock trend."""

    history: list[JsonDict] = []
    mocks = progress.get("mock_interviews")
    if not isinstance(mocks, list):
        return history
    for mock in mocks:
        if not isinstance(mock, dict):
            continue
        scores = mock.get("scores")
        history.append(
            {
                "date": mock.get("date"),
                "problem_id": mock.get("problem_id"),
                "verdict": mock.get("verdict"),
                "duration_minutes": mock.get("duration_minutes"),
                "scores": scores if isinstance(scores, dict) else {},
            }
        )
    return history


def _feed_readiness(state: RepositoryState, on_date: date) -> JsonDict:
    """Reshape `compute_readiness` into the design section 3 gate dict. No
    recomputation - the same numbers the CLI readiness report shows."""

    readiness = compute_readiness(
        state.curriculum, state.stages, state.skills, state.scoring,
        state.progress, on_date,
    )
    thresholds = readiness["thresholds"]
    core = thresholds["core_skill_mastery"]
    pass_rate = thresholds["revision_pass_rate"]
    mocks = thresholds["recent_mocks"]
    projection = readiness["projection"]
    pace = readiness["pace"]
    return {
        "gates": {
            "core_mastery": {
                "met": core["met"],
                "current": core["actual"],
                "target": core["target"],
                "mastered": core["mastered"],
                "total": core["total"],
            },
            "revision_pass": {
                "met": pass_rate["met"],
                "current": pass_rate["actual"],
                "target": pass_rate["target"],
            },
            "mocks": {
                "met": mocks["met"],
                "current": mocks["recorded"],
                "required": mocks["required"],
                "verdicts": mocks["recent_verdicts"],
            },
        },
        "projected_date": projection.get("date"),
        "projection_status": projection.get("status"),
        "projection_message": projection.get("message"),
        "all_met": readiness["all_met"],
        "pace": {
            "problems_per_week": pace["problems_per_week"],
            "skills_per_week": pace["skills_mastered_per_week"],
            "window_days": pace["window_days"],
        },
    }


def build_dashboard_feed(state: RepositoryState, on_date: date) -> JsonDict:
    """Everything the web dashboard renders, computed by the same engine as the
    CLI (design: plans/DASHBOARD_REDESIGN_DESIGN.md section 3). Pure function;
    JSON-serializable output; never mutates state."""

    from datetime import datetime

    problems = problem_lookup(state.curriculum)
    selection = select_next_problem(state, on_date=on_date)

    next_action: JsonDict = {
        "mode": selection.mode,
        "problem_id": None,
        "title": None,
        "url": None,
        "reason": selection.reason,
        "stage_label": None,
    }
    if selection.problem:
        problem = selection.problem
        next_action["problem_id"] = problem.get("id")
        next_action["title"] = problem.get("title")
        next_action["url"] = problem.get("url")

    revision_modes = {"revision", "reactivation", "quarterly_maintenance"}
    if selection.mode in revision_modes and isinstance(selection.revision_entry, dict):
        entry_kind = _feed_queue_kind(selection.revision_entry.get("kind"))
        next_action["stage_label"] = _feed_queue_stage_label(
            "quarterly_maintenance"
            if selection.mode == "quarterly_maintenance"
            else entry_kind,
            int(selection.revision_entry.get("stage", 0)),
        )

    solve_modes = {"resume_current_problem", "current_skill",
                   "current_stage", "earliest_unlocked"}
    if selection.mode in solve_modes and next_action["problem_id"]:
        solution_path = ROOT / "solutions" / f"{next_action['problem_id']}.py"
        next_action["code_gate"] = {
            "solution_expected": f"solutions/{next_action['problem_id']}.py",
            "solution_exists": solution_path.exists(),
        }

    revision_queue: list[JsonDict] = []
    for entry in open_revision_entries_due_on_or_before(state.progress, on_date):
        kind = _feed_queue_kind(entry.get("kind"))
        stage = int(entry.get("stage", 0))
        problem = problems.get(entry["problem"], {})
        revision_queue.append(
            {
                "problem_id": entry["problem"],
                "title": problem.get("title"),
                "stage": stage,
                "stage_label": _feed_queue_stage_label(kind, stage),
                "next_due": entry["date"],
                "status": entry.get("status"),
                "kind": kind,
                "overdue": parse_iso_date(entry["date"], "revision.date") < on_date,
            }
        )

    feed: JsonDict = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "reference_date": format_iso_date(on_date),
        "next_action": next_action,
        "revision_queue": revision_queue,
        "review_forecast": review_forecast(state.progress, on_date),
        "revision_calendar": revision_calendar(state, on_date),
        "readiness": _feed_readiness(state, on_date),
        "retention": retention_split(state.progress),
        "hint_trajectory": hint_trajectory_events(state.progress),
        "mock_history": _feed_mock_history(state.progress),
        # Which problems actually have a runnable solution file (F9). The UI
        # may only link a path that exists; everything else stays plain text.
        "solutions_present": sorted(
            path.stem
            for path in (ROOT / "solutions").glob("*.py")
            if path.stem in problems
        ),
        "policy": {
            "mastered_after_stage": MASTERED_AFTER_STAGE,
            "revision_backlog_threshold": REVISION_BACKLOG_THRESHOLD,
            "intervals": {
                f"R{index + 1}": REVISION_INTERVAL_DAYS[index]
                for index in sorted(REVISION_INTERVAL_DAYS)
            },
        },
    }
    return feed
