#!/usr/bin/env python3
"""Generate targeted practice from accumulated learner weaknesses."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from typing import Any

from _shared import (
    RepositoryError,
    THINKING_DIMENSION_LABELS,
    completed_problem_ids,
    load_repository_state,
    normalize_weakness_entry,
    revision_stage_label,
)


WEAKNESS_PLAYBOOK: dict[str, dict[str, Any]] = {
    "understanding": {
        "title": "Understanding the question",
        "routine": "Say what is given, what to return, and what can go wrong before solving.",
        "search_terms": ["constraint", "input", "output", "edge"],
        "prompts": [
            "What is the exact success condition?",
            "Which input constraint changes the required complexity?",
            "What edge case would break a casual interpretation?",
        ],
    },
    "examples": {
        "title": "Making useful examples",
        "routine": "Create a normal case, a tiny case, and a tricky case before coding.",
        "search_terms": ["edge", "counterexample", "palindrome", "negative"],
        "prompts": [
            "What is the smallest non-trivial example?",
            "What example breaks the obvious greedy choice?",
            "Which example proves the initialization is valid?",
        ],
    },
    "brute_force": {
        "title": "Starting with brute force",
        "routine": "First write the simple correct solution, then find what work is repeated.",
        "search_terms": ["brute force", "hash-map", "nested loops", "complexity"],
        "prompts": [
            "What is the most direct correct solution?",
            "Where exactly is the repeated work?",
            "Which stored state removes that repeated work?",
        ],
    },
    "pattern_detection": {
        "title": "Finding the core rule",
        "routine": "Explain what must stay true after every step before thinking about patterns.",
        "search_terms": ["invariant", "running", "frontier", "state"],
        "prompts": [
            "What does the running variable mean after processing index i?",
            "What condition lets you discard prior state?",
            "What invariant would make the algorithm obviously correct?",
        ],
    },
    "algorithm_design": {
        "title": "Building the algorithm",
        "routine": "Decide what to track, why it is enough, and test the update rule on edge cases.",
        "search_terms": ["greedy", "state", "frontier", "decision"],
        "prompts": [
            "What decision is irreversible here?",
            "Why is the chosen state sufficient?",
            "What proof prevents a skipped candidate from mattering later?",
        ],
    },
    "complexity_analysis": {
        "title": "Knowing time and space cost",
        "routine": "Connect time and space to the loops, data structures, and input size.",
        "search_terms": ["O(n)", "O(1)", "binary search", "heap"],
        "prompts": [
            "Which operation dominates runtime?",
            "What data structure changes the asymptotic bound?",
            "Which constraint rules out the naive solution?",
        ],
    },
    "implementation": {
        "title": "Writing code without breaking the idea",
        "routine": "Check starting values, loop bounds, update order, and return value.",
        "search_terms": ["initialization", "loop", "state", "running", "frontier", "greedy"],
        "prompts": [
            "Does the initial value represent a real valid state?",
            "Should the loop start at index 0 or 1?",
            "Which edge case proves the return value is correct?",
        ],
    },
    "communication": {
        "title": "Explaining the solution clearly",
        "routine": "Explain in this order: simple idea, repeated work, core rule, proof, complexity.",
        "search_terms": ["proof", "explain", "reasoning", "invariant"],
        "prompts": [
            "Can you explain the algorithm without naming the pattern?",
            "What is the one-sentence proof?",
            "What tradeoff should an interviewer hear before code?",
        ],
    },
}

KEYWORD_TO_DIMENSION = [
    (("brute", "repeated work", "baseline"), "brute_force"),
    (("example", "counterexample", "edge case"), "examples"),
    (("invariant", "proof", "correctness"), "pattern_detection"),
    (("greedy", "frontier", "decision", "state compression"), "algorithm_design"),
    (("complexity", "o(", "time", "space"), "complexity_analysis"),
    (("initialization", "loop", "implementation", "code", "return"), "implementation"),
    (("communicat", "explain", "interview"), "communication"),
    (("constraint", "input", "output", "scope"), "understanding"),
]


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Analyze accumulated learner weaknesses and generate targeted "
            "practice questions to strengthen thinking ability."
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
        "--limit",
        type=int,
        default=4,
        help="Number of targeted problems per weakness.",
    )
    parser.add_argument(
        "--focus-count",
        type=int,
        default=5,
        help="Number of weakness clusters to output.",
    )
    parser.add_argument(
        "--include-completed",
        action="store_true",
        help="Allow completed problems as targeted review items.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser


def classify_text(text: str) -> set[str]:
    """Classify free-form text into thinking dimensions."""

    lowered = text.lower()
    dimensions: set[str] = set()
    for keywords, dimension in KEYWORD_TO_DIMENSION:
        if any(keyword in lowered for keyword in keywords):
            dimensions.add(dimension)
    return dimensions


def weighted_score(thinking_score: dict[str, Any], weights: dict[str, Any]) -> float:
    """Compute a weighted thinking score for one completed problem."""

    total = 0.0
    weight_total = 0.0
    for dimension, weight in weights.items():
        value = thinking_score.get(dimension)
        if isinstance(value, (int, float)) and isinstance(weight, (int, float)):
            total += float(value) * float(weight)
            weight_total += float(weight)
    return round(total / weight_total, 2) if weight_total else 0.0


def problem_haystack(problem: dict[str, Any], skill: dict[str, Any] | None) -> str:
    """Return searchable text for a curriculum problem."""

    return " ".join(
        str(value)
        for value in [
            problem.get("id"),
            problem.get("title"),
            problem.get("stage"),
            problem.get("source_section"),
            problem.get("difficulty"),
            problem.get("problem_role"),
            problem.get("importance"),
            problem.get("notes"),
            problem.get("primary_skill"),
            skill.get("name") if isinstance(skill, dict) else None,
            skill.get("description") if isinstance(skill, dict) else None,
        ]
        if value
    ).lower()


def is_unlocked(problem: dict[str, Any], completed_ids: set[str], graph: dict[str, Any]) -> bool:
    """Return whether all problem dependencies are completed."""

    dependencies = graph.get("problem_dependencies", {}).get(problem.get("id"), [])
    if not isinstance(dependencies, list):
        return False
    return all(dep in completed_ids for dep in dependencies)


def target_problems(
    *,
    state: Any,
    dimension: str,
    limit: int,
    include_completed: bool,
) -> list[dict[str, Any]]:
    """Select deterministic targeted problems for a weakness dimension."""

    playbook = WEAKNESS_PLAYBOOK[dimension]
    completed_ids = completed_problem_ids(state.progress)
    current_stage = state.progress.get("current_stage")
    skill_map = state.skills.get("skills", {})
    candidates: list[tuple[tuple[int, int, int, str], dict[str, Any]]] = []
    fallback: list[tuple[tuple[int, int, int, str], dict[str, Any]]] = []

    for problem in state.curriculum.get("problems", []):
        if not include_completed and problem.get("id") in completed_ids:
            continue
        skill = skill_map.get(problem.get("primary_skill"), {})
        haystack = problem_haystack(problem, skill if isinstance(skill, dict) else None)
        unlocked_rank = 0 if is_unlocked(problem, completed_ids, state.graph) else 1
        stage_rank = 0 if problem.get("stage") == current_stage else 1
        role_rank = {"PRIMARY": 0, "REINFORCEMENT": 1, "CHALLENGE": 2}.get(
            str(problem.get("problem_role")),
            3,
        )
        rank = (
            stage_rank,
            unlocked_rank,
            role_rank,
            str(problem.get("id")),
        )
        if problem.get("stage") == current_stage:
            fallback.append((rank, problem))
        if not any(term.lower() in haystack for term in playbook["search_terms"]):
            continue
        candidates.append(
            (
                rank,
                problem,
            )
        )

    chosen: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _, problem in sorted(candidates, key=lambda item: item[0]):
        if problem["id"] not in seen:
            chosen.append(problem)
            seen.add(problem["id"])
        if len(chosen) >= limit:
            return chosen
    for _, problem in sorted(fallback, key=lambda item: item[0]):
        if problem["id"] not in seen:
            chosen.append(problem)
            seen.add(problem["id"])
        if len(chosen) >= limit:
            break
    return chosen


def collect_evidence(state: Any) -> dict[str, list[dict[str, Any]]]:
    """Collect weakness evidence grouped by thinking dimension."""

    evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for problem_id, entries in state.progress.get("weaknesses_detected", {}).items():
        if not isinstance(entries, list):
            continue
        for raw_entry in entries:
            # F20a: entries are structured objects; legacy strings normalize
            # in place. Resolved weaknesses no longer inflate clusters.
            entry = normalize_weakness_entry(raw_entry)
            if entry["status"] == "resolved" or not entry["text"]:
                continue
            for dimension in classify_text(entry["text"]):
                evidence[dimension].append(
                    {
                        "source": "weaknesses_detected",
                        "problem_id": problem_id,
                        "text": entry["text"],
                        "severity": 1.2,
                    }
                )

    for record in state.progress.get("completed", []):
        if not isinstance(record, dict):
            continue
        problem_id = str(record.get("problem_id"))
        mistake = str(record.get("main_mistake", "")).strip()
        if mistake and "none recorded" not in mistake.lower():
            for dimension in classify_text(mistake):
                evidence[dimension].append(
                    {
                        "source": "completed.main_mistake",
                        "problem_id": problem_id,
                        "text": mistake,
                        "severity": 1.1,
                    }
                )

        # F20b: failed revision recalls are weakness evidence too, at the
        # same weight as a solve's main_mistake.
        revision = record.get("revision")
        history = revision.get("history") if isinstance(revision, dict) else None
        if not isinstance(history, list):
            continue
        for event in history:
            if not isinstance(event, dict) or event.get("result") != "FAIL":
                continue
            stage = event.get("stage")
            label = revision_stage_label(int(stage)) if isinstance(stage, int) else "revision"
            notes = str(event.get("notes", "")).strip()
            text = notes or f"Failed {label} recall."
            for dimension in classify_text(text):
                evidence[dimension].append(
                    {
                        "source": "revision.fail",
                        "problem_id": problem_id,
                        "text": text,
                        "severity": 1.1,
                    }
                )

    return evidence


def collect_supporting_context(state: Any, active_dimensions: set[str]) -> dict[str, list[dict[str, Any]]]:
    """Collect non-primary context only for dimensions with real weakness evidence."""

    context: dict[str, list[dict[str, Any]]] = defaultdict(list)
    averages = state.progress.get("scores", {}).get("averages", {}).get("thinking_dimensions", {})
    for dimension in active_dimensions:
        score = averages.get(dimension)
        if isinstance(score, (int, float)):
            context[dimension].append(
                {
                    "source": "thinking_score_average",
                    "text": (
                        f"{THINKING_DIMENSION_LABELS.get(dimension, dimension)} "
                        f"average is {float(score):.2f}/4."
                    ),
                }
            )

    for field in ("gaps", "common_failures"):
        for text in state.progress.get("thinking_profile", {}).get(field, []):
            dimensions = classify_text(str(text)) & active_dimensions
            for dimension in dimensions:
                context[dimension].append(
                    {
                        "source": f"thinking_profile.{field}",
                        "text": str(text),
                    }
                )

    for problem_id, lesson in state.progress.get("lessons_learned", {}).items():
        if not isinstance(lesson, dict):
            continue
        for text in lesson.values():
            if not isinstance(text, str):
                continue
            for dimension in classify_text(text) & active_dimensions:
                context[dimension].append(
                    {
                        "source": "lessons_learned",
                        "problem_id": problem_id,
                        "text": text,
                    }
                )

    return context


def build_payload(reference_date: date, state: Any, limit: int, focus_count: int, include_completed: bool) -> dict[str, Any]:
    """Build the weakness lab payload."""

    evidence = collect_evidence(state)
    weights = state.scoring.get("weights", {})
    completed_records = [
        record for record in state.progress.get("completed", []) if isinstance(record, dict)
    ]
    recent_problem_scores = [
        {
            "problem_id": record.get("problem_id"),
            "weighted_thinking_score": weighted_score(record.get("thinking_score", {}), weights),
            "main_mistake": record.get("main_mistake"),
        }
        for record in completed_records[-8:]
    ]
    supporting_context = collect_supporting_context(state, set(evidence))

    clusters = []
    for dimension, items in evidence.items():
        if dimension not in WEAKNESS_PLAYBOOK:
            continue
        severity = round(sum(float(item.get("severity", 0.0)) for item in items), 2)
        playbook = WEAKNESS_PLAYBOOK[dimension]
        problems = target_problems(
            state=state,
            dimension=dimension,
            limit=limit,
            include_completed=include_completed,
        )
        clusters.append(
            {
                "dimension": dimension,
                "title": playbook["title"],
                "severity": severity,
                "primary_evidence_count": len(items),
                "primary_evidence": items[:8],
                "supporting_context": supporting_context.get(dimension, [])[:6],
                "correction_routine": playbook["routine"],
                "drill_questions": playbook["prompts"],
                "targeted_problems": [
                    {
                        "id": problem["id"],
                        "title": problem["title"],
                        "stage": problem["stage"],
                        "skill": problem["primary_skill"],
                        "difficulty": problem["difficulty"],
                        "role": problem.get("problem_role"),
                        "lc_id": problem.get("lc_id"),
                        "source_index": problem.get("original_number"),
                    }
                    for problem in problems
                ],
            }
        )

    clusters.sort(key=lambda item: (-item["severity"], item["dimension"]))
    catalog_counter = Counter()
    for entry in state.progress.get("completed", []):
        mistake = str(entry.get("main_mistake", "")).strip()
        if mistake and "none recorded" not in mistake.lower():
            catalog_counter[mistake] += 1
    for text in state.progress.get("thinking_profile", {}).get("common_failures", []):
        catalog_counter[str(text)] += 1

    return {
        "date": reference_date.isoformat(),
        "current_stage": state.progress.get("current_stage"),
        "focus_clusters": clusters[:focus_count],
        "frequent_mistake_signals": [
            {"text": text, "count": count}
            for text, count in catalog_counter.most_common(8)
        ],
        "recent_problem_scores": recent_problem_scores,
        "method": (
            "Primary weakness clusters are built only from question-level evidence in "
            "progress.json: open `weaknesses_detected` entries (resolved ones are skipped), "
            "completed problem `main_mistake`, and failed revision recalls. "
            "Scores, learner profile gaps, and lessons are attached only as supporting context."
        ),
    }


def render_text(payload: dict[str, Any]) -> str:
    """Render the weakness lab payload as text."""

    lines = [
        f"Weakness Lab: {payload['date']}",
        f"Current stage: {payload['current_stage']}",
        "",
        "Focus Weaknesses",
    ]
    for index, cluster in enumerate(payload["focus_clusters"], start=1):
        lines.extend(
            [
                f"{index}. {cluster['title']} ({cluster['dimension']})",
                f"   Severity: {cluster['severity']:.2f} from {cluster['primary_evidence_count']} question-level signals",
                f"   Correction: {cluster['correction_routine']}",
                "   Drill questions:",
            ]
        )
        for prompt in cluster["drill_questions"]:
            lines.append(f"   - {prompt}")
        lines.append("   Targeted problems:")
        if cluster["targeted_problems"]:
            for problem in cluster["targeted_problems"]:
                # `original_number` is the source-PDF index, NOT a LeetCode id;
                # only show "LC <n>" when a real lc_id is set (F16).
                if problem.get("lc_id"):
                    lc = f" | LC {problem['lc_id']}"
                elif problem.get("source_index"):
                    lc = f" | #{problem['source_index']} (source index)"
                else:
                    lc = ""
                lines.append(
                    f"   - {problem['id']} | {problem['title']} | {problem['difficulty']} | "
                    f"{problem['skill']} | {problem['role']}{lc}"
                )
        else:
            lines.append("   - No matching open problems found.")
        lines.append("   Question-level evidence:")
        for item in cluster["primary_evidence"][:3]:
            prefix = f"{item.get('problem_id')} | " if item.get("problem_id") else ""
            lines.append(f"   - {prefix}{item['text']}")
        if cluster["supporting_context"]:
            lines.append("   Supporting context:")
            for item in cluster["supporting_context"][:2]:
                prefix = f"{item.get('problem_id')} | " if item.get("problem_id") else ""
                lines.append(f"   - {prefix}{item['text']}")
        lines.append("")

    lines.append("Frequent Mistake Signals")
    if payload["frequent_mistake_signals"]:
        for item in payload["frequent_mistake_signals"]:
            lines.append(f"- x{item['count']} {item['text']}")
    else:
        lines.append("- None recorded yet")
    return "\n".join(lines)


def main() -> int:
    """Run the CLI."""

    parser = build_parser()
    args = parser.parse_args()
    try:
        reference_date = date.fromisoformat(args.date)
        state = load_repository_state(args.progress_file)
        payload = build_payload(
            reference_date=reference_date,
            state=state,
            limit=max(args.limit, 1),
            focus_count=max(args.focus_count, 1),
            include_completed=args.include_completed,
        )
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
