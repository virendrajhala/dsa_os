#!/usr/bin/env python3
"""Generate the Blind 75 curriculum track from the main 582-problem curriculum.

Every Blind 75 problem already exists in curriculum/curriculum.json, matched by
LeetCode id. This script selects those 75, mints fresh `B75-###` ids, and emits a
complete, self-contained track under tracks/blind75/ (curriculum, skills, stages,
dependency graph, patterns, scoring, progress, plan, solutions/).

Re-runnable and deterministic: the output depends only on the main track files
and the flags below. It never touches the main track.

Run: python3 scripts/generate_blind75_track.py
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from _shared import (
    ROOT,
    RepositoryError,
    RepositoryState,
    load_json_file,
    normalize_progress,
    save_json_file,
    select_next_problem,
    track_paths,
)

TRACK = "blind75"

# The canonical Blind 75, by LeetCode id, grouped by the list's own categories.
# The category becomes each problem's `source_section` (provenance, not a topic
# tag - same convention as the main curriculum).
BLIND75_BY_CATEGORY: dict[str, list[int]] = {
    "Array": [1, 121, 217, 238, 53, 152, 153, 33, 15, 11],
    "Binary": [371, 191, 338, 268, 190],
    "Dynamic Programming": [70, 322, 300, 1143, 139, 377, 198, 213, 91, 62, 55],
    "Graph": [133, 207, 417, 200, 128, 269, 261, 323],
    "Interval": [57, 56, 435, 252, 253],
    "Linked List": [206, 141, 21, 23, 19, 143],
    "Matrix": [73, 54, 48, 79],
    "String": [3, 424, 76, 242, 49, 20, 125, 5, 647, 271],
    "Tree": [104, 100, 226, 124, 102, 297, 572, 105, 98, 230, 235, 208, 211, 212],
    "Heap": [347, 295],
}

# Sprint plan: 75 solves across 8 weeks, no deload weeks (the whole point of the
# track is speed), one mock per week.
DEFAULT_PLAN_START = "2026-08-03"  # a Monday
PLAN_WEEK_TARGETS = [10, 10, 10, 9, 9, 9, 9, 9]

META_SKILL_ID = "SK-IE-00"


# Main-curriculum notes open with provenance to the source PDF ("PDF subsection:
# ...") or to the supplemental backfill ("SUPPLEMENTAL (added to close a coverage
# gap): ..."). Neither is true of a problem in this track, so the prefix is
# stripped and the teaching content behind it is kept.
NOTE_PREFIXES = (
    "SUPPLEMENTAL (added to close a coverage gap): ",
    "PDF subsection: ",
)


def clean_note(note: str) -> str:
    for prefix in NOTE_PREFIXES:
        if note.startswith(prefix):
            return note[len(prefix) :].strip()
    return note.strip()


def category_by_lc_id() -> dict[int, str]:
    mapping: dict[int, str] = {}
    for category, lc_ids in BLIND75_BY_CATEGORY.items():
        for lc_id in lc_ids:
            if lc_id in mapping:
                raise RepositoryError(f"LeetCode id {lc_id} listed twice in BLIND75_BY_CATEGORY.")
            mapping[lc_id] = category
    if len(mapping) != 75:
        raise RepositoryError(f"BLIND75_BY_CATEGORY must list exactly 75 problems, found {len(mapping)}.")
    return mapping


def select_source_problems(curriculum: dict, stage_order: list[str]) -> list[tuple[dict, str]]:
    """Pick the 75 main-curriculum problems, ordered stage-major.

    Within a stage, main-curriculum file order is preserved - that order is the
    scheduler's tiebreaker, so the compressed track walks the same learning path.
    """

    categories = category_by_lc_id()
    problems = curriculum["problems"]
    file_index = {problem["id"]: index for index, problem in enumerate(problems)}

    by_lc: dict[int, list[dict]] = {}
    for problem in problems:
        lc_id = problem.get("lc_id")
        if isinstance(lc_id, int):
            by_lc.setdefault(lc_id, []).append(problem)

    selected: list[tuple[dict, str]] = []
    missing: list[int] = []
    for lc_id, category in categories.items():
        candidates = by_lc.get(lc_id)
        if not candidates:
            missing.append(lc_id)
            continue
        # Prefer the original slot over a later `revisit_of` twin, then the
        # earliest slot in file order.
        chosen = sorted(
            candidates,
            key=lambda p: (1 if p.get("revisit_of") else 0, file_index[p["id"]]),
        )[0]
        selected.append((chosen, category))
    if missing:
        raise RepositoryError(
            "No curriculum problem carries these LeetCode ids: "
            + ", ".join(str(lc_id) for lc_id in sorted(missing))
        )

    stage_index = {name: i for i, name in enumerate(stage_order)}
    selected.sort(key=lambda pair: (stage_index[pair[0]["stage"]], file_index[pair[0]["id"]]))
    return selected


def build_curriculum(selected: list[tuple[dict, str]]) -> tuple[dict, dict[str, str]]:
    """Emit the track curriculum and the main-id -> B75-id map.

    Roles are re-derived per skill: the first problem of a skill (in emitted
    order) validates it, the rest reinforce it. The track carries no CHALLENGE
    problems, so the challenge stage gate is a no-op here.
    """

    id_map = {
        problem["id"]: f"B75-{index:03d}" for index, (problem, _) in enumerate(selected, start=1)
    }

    seen_skills: set[str] = set()
    problems: list[dict] = []
    for source, category in selected:
        skill_id = source["primary_skill"]
        role = "REINFORCEMENT" if skill_id in seen_skills else "PRIMARY"
        seen_skills.add(skill_id)
        problems.append(
            {
                "id": id_map[source["id"]],
                "derived_from_id": source["id"],
                "original_number": None,
                "title": source["title"],
                "difficulty": source["difficulty"],
                "source_section": category,
                "stage": source["stage"],
                "primary_skill": skill_id,
                "problem_role": role,
                "difficulty_weight": source["difficulty_weight"],
                "importance": source["importance"],
                "status": "not_started",
                "revision_count": 0,
                "supplemental": False,
                "notes": clean_note(source["notes"]),
                "lc_id": source["lc_id"],
                "url": source["url"],
            }
        )

    curriculum = {
        "repository": "DSA_OS",
        "track": TRACK,
        "source": {
            "origin": "Blind 75",
            "derived_from": "curriculum/curriculum.json",
            "generator": "scripts/generate_blind75_track.py",
            "track_derived": True,
            "integrity": (
                "Every problem is the main curriculum's slot for the same LeetCode id, "
                "re-identified as B75-### and re-roled within this track. Stage and "
                "primary_skill are inherited unchanged, so the learning path matches."
            ),
            "total_problem_count": len(problems),
        },
        "_comment": "source_section = the Blind 75 list's own category; NOT a topic tag.",
        "problems": problems,
        "version": "1.0.0",
        "changelog": [
            {
                "version": "1.0.0",
                "summary": "Generated from the main 582-problem curriculum by lc_id match.",
            }
        ],
    }
    return curriculum, id_map


def build_skills(main_skills: dict, curriculum: dict) -> dict:
    """Emit the track's skills: those owning a B75 problem, plus the meta skill."""

    by_skill: dict[str, list[dict]] = {}
    for problem in curriculum["problems"]:
        by_skill.setdefault(problem["primary_skill"], []).append(problem)

    kept = [sid for sid in main_skills["skill_order"] if sid in by_skill or sid == META_SKILL_ID]
    skills: dict[str, dict] = {}
    for skill_id in kept:
        source = dict(main_skills["skills"][skill_id])
        source["prerequisites"] = [p for p in source.get("prerequisites", []) if p in kept]
        if skill_id == META_SKILL_ID:
            skills[skill_id] = source
            continue
        owned = by_skill[skill_id]
        source["primary_validation_problem"] = owned[0]["id"]
        source["reinforcement_problems"] = [p["id"] for p in owned[1:]]
        source["challenge_problems"] = []
        skills[skill_id] = source

    return {
        "schema_version": main_skills.get("schema_version", 1),
        "source_of_truth": True,
        "track": TRACK,
        "note": (
            "Generated for the Blind 75 track from knowledge/skills.json. Only skills "
            "owning a Blind 75 problem are kept (plus the SK-IE-00 meta-skill). Roles "
            "are re-derived: the first problem of a skill validates it, the rest "
            "reinforce it. A skill with no reinforcement problems masters from its "
            "primary alone."
        ),
        "skill_order": kept,
        "skills": skills,
    }


def build_stages(main_stages: dict, skills: dict) -> dict:
    """Emit the track's stages: those retaining at least one skill."""

    kept_skills = set(skills["skill_order"])
    stage_order: list[str] = []
    stages: dict[str, dict] = {}
    for stage_name in main_stages["stage_order"]:
        source = dict(main_stages["stages"][stage_name])
        stage_skills = [sid for sid in source.get("skills", []) if sid in kept_skills]
        if not stage_skills:
            continue
        source["skills"] = stage_skills
        stage_order.append(stage_name)
        stages[stage_name] = source
    return {"track": TRACK, "stage_order": stage_order, "stages": stages}


def build_graph(main_graph: dict, skills: dict, curriculum: dict, id_map: dict[str, str]) -> dict:
    """Emit the track's dependency graph, filtered and re-identified.

    Dropping a dependency only ever unlocks a problem earlier, which is exactly
    what a compressed track wants. Filtering cannot introduce cycles or orphans:
    a node whose prerequisites all disappear simply becomes a root.
    """

    kept_skills = set(skills["skill_order"])
    skill_dependencies = {
        skill_id: [dep for dep in main_graph["skill_dependencies"].get(skill_id, []) if dep in kept_skills]
        for skill_id in skills["skill_order"]
    }

    main_problem_deps = main_graph["problem_dependencies"]
    problem_dependencies = {
        problem["id"]: [
            id_map[dep]
            for dep in main_problem_deps.get(problem["derived_from_id"], [])
            if dep in id_map
        ]
        for problem in curriculum["problems"]
    }

    return {
        "schema_version": main_graph.get("schema_version", 3),
        "track": TRACK,
        "note": (
            "Generated for the Blind 75 track from curriculum/dependency_graph.json. "
            "Skill and problem prerequisites are the main track's, filtered to what "
            "this track contains and re-identified as B75-### ids."
        ),
        "skill_order": list(skills["skill_order"]),
        "skill_dependencies": skill_dependencies,
        "difficulty_gates": main_graph["difficulty_gates"],
        "problem_dependencies": problem_dependencies,
    }


def build_patterns(main_patterns: dict, id_map: dict[str, str], skills: dict) -> dict:
    """Emit the track's patterns: those still appearing in at least one problem."""

    kept_skills = set(skills["skill_order"])
    survivors = [
        pattern_id
        for pattern_id in main_patterns["pattern_order"]
        if any(pid in id_map for pid in main_patterns["patterns"][pattern_id].get("appears_in", []))
    ]
    survivor_set = set(survivors)

    patterns: dict[str, dict] = {}
    for pattern_id in survivors:
        pattern = dict(main_patterns["patterns"][pattern_id])
        pattern["appears_in"] = [id_map[pid] for pid in pattern.get("appears_in", []) if pid in id_map]
        pattern["skills"] = [sid for sid in pattern.get("skills", []) if sid in kept_skills]
        pattern["related_patterns"] = [
            rid for rid in pattern.get("related_patterns", []) if rid in survivor_set and rid != pattern_id
        ]
        pattern["contrast_with"] = [
            cid for cid in pattern.get("contrast_with", []) if cid in survivor_set and cid != pattern_id
        ]
        patterns[pattern_id] = pattern

    return {
        "schema_version": main_patterns.get("schema_version", 1),
        "source_of_truth": True,
        "track": TRACK,
        "note": (
            "Generated for the Blind 75 track from knowledge/patterns.json. Problem, "
            "skill, and cross-pattern references are filtered to this track's contents."
        ),
        "pattern_order": survivors,
        "patterns": patterns,
    }


def build_scoring(main_scoring: dict, curriculum: dict, stages: dict) -> dict:
    """Copy the main rubric, recalibrating the two volume-coupled blocks.

    `promotion_thresholds` is stage-keyed with problem-count bars calibrated to
    582 problems, and `readiness.stage_scope_count` slices stage_order. Every
    other block (scales, weights, revision policy, taxonomies) is track-neutral
    and copied verbatim - the revision policy in particular MUST stay identical,
    because interval scheduling is still driven by module-level config.
    """

    scoring = json.loads(json.dumps(main_scoring))

    counts: dict[str, int] = {}
    for problem in curriculum["problems"]:
        counts[problem["stage"]] = counts.get(problem["stage"], 0) + 1

    thresholds: dict[str, dict] = {}
    cumulative = 0
    for stage_name in stages["stage_order"]:
        cumulative += counts.get(stage_name, 0)
        source = main_scoring["promotion_thresholds"].get(stage_name, {})
        thresholds[stage_name] = {
            "minimum_weighted_score": source.get("minimum_weighted_score", 2.4),
            "minimum_completed_problems": cumulative,
        }
    scoring["promotion_thresholds"] = thresholds

    readiness = dict(main_scoring["readiness"])
    readiness["stage_scope_count"] = min(
        int(readiness.get("stage_scope_count", 10)), len(stages["stage_order"])
    )
    scoring["readiness"] = readiness
    scoring["track"] = TRACK
    return scoring


def build_progress(main_template: dict, stages: dict) -> dict:
    """A fresh, empty progress payload for the track.

    The derived blocks (scores, skill_progress, stage_mastery,
    competency_completion) still hold the MAIN track's shape here; the caller
    runs `normalize_progress` against the generated state to recompute them, and
    the validator re-runs that same recompute to check the cache.
    """

    payload = json.loads(json.dumps(main_template))
    payload["last_updated"] = None
    payload["current_stage"] = stages["stage_order"][0]
    payload["current_problem"] = None
    payload["completed"] = []
    payload["mock_interviews"] = []
    payload["deferred_learnings"] = []
    payload["notes"] = []
    payload["history"] = []
    return payload


def build_plan(curriculum: dict, plan_start: date) -> dict:
    """A sprint plan: every problem in the track across PLAN_WEEK_TARGETS weeks."""

    total = len(curriculum["problems"])
    if sum(PLAN_WEEK_TARGETS) != total:
        raise RepositoryError(
            f"PLAN_WEEK_TARGETS sums to {sum(PLAN_WEEK_TARGETS)}, but the track has {total} problems."
        )
    weeks = [
        {
            "week": index,
            "start": (plan_start + timedelta(days=7 * (index - 1))).isoformat(),
            "deload": False,
            "target_solves": target,
            "mock": True,
        }
        for index, target in enumerate(PLAN_WEEK_TARGETS, start=1)
    ]
    end = plan_start + timedelta(days=7 * len(PLAN_WEEK_TARGETS) - 1)
    return {
        "schema_version": 1,
        "track": TRACK,
        "quarter": {
            "label": f"Blind 75 sprint - {len(PLAN_WEEK_TARGETS)} weeks",
            "start": plan_start.isoformat(),
            "end": end.isoformat(),
            "target_new_solves": total,
            "target_mocks": len(PLAN_WEEK_TARGETS),
            "daily_review_capacity": 4,
        },
        "weeks": weeks,
        "notes": [
            "The scheduler (make next TRACK=blind75) is the authority; the plan is the pace contract.",
            "No deload weeks: the point of this track is one fast pass over every pattern.",
            "Finishing early is the goal - the burn-up ahead of target means move to the main track.",
        ],
    }


# --- learner-knowledge files -------------------------------------------------
# Tracks share nothing, so each one keeps its own catalog, memory, pattern log
# and playbook. A new track starts them EMPTY: they are observations about how
# you performed on THIS curriculum, and importing another track's would put
# claims in them that this track never evidenced.

EMPTY_MISTAKE_CATALOG = {"version": 1, "track": TRACK, "entries": []}

MENTOR_MEMORY_SEED = """# Mentor Memory - student profile (Blind 75 track)

This file holds *who the student currently is* on the **Blind 75 track** -
durable strengths, gaps, preferred reasoning, and recurring failure modes - so a
new session starts with context. It holds no protocol, session flow, hint ladder
or review policy; those live solely in `mentor/mentor_protocol.md`. Keep it
synced with `tracks/blind75/progress.json.thinking_profile`, the authoritative
source.

This profile is this track's alone. The main track keeps its own at
`mentor_memory.md`, and the two are never merged: a gap is only recorded here
once THIS track's sessions evidenced it.

## Strengths

_None recorded yet._

## Gaps

_None recorded yet._

## Common failure modes

_None recorded yet._

## Preferred reasoning

_None recorded yet._
"""

THINKING_PATTERNS_SEED = """# Thinking Patterns (Blind 75 track)

Each entry records a reusable invariant you derived on the **Blind 75 track**.
This log is this track's alone; the main track keeps its own at
`thinking_patterns.md`.

## Template
Pattern:
Trigger:
Invariant:
Why it works:
Related problems:

---

_No patterns recorded yet._
"""

INTERVIEW_PLAYBOOK_SEED = """# Interview Playbook (Blind 75 track)

## Purpose
This file captures interviewer expectations, follow-up questions, edge cases,
and communication patterns from the **Blind 75 track**, organized per topic. It
grows with every problem completion - see `AFTER_PROBLEM_COMPLETION.md` -
instead of staying frozen at whatever problem seeded it.

This playbook is this track's alone; the main track keeps its own at
`interview_playbook.md`.

## How This File Grows

After each completed problem, append the session's interview takeaway to the
section matching the problem's primary topic, creating the section if it does
not exist. Record what an interviewer would probe, the follow-ups that actually
came up, and the edge cases worth naming out loud.

---

_No entries yet._
"""


SOLUTIONS_README = """# Blind 75 solutions

The Blind 75 track's solution files. The contract is **identical** to the main
track's - see `solutions/README.md` for the full rules (3-5 embedded asserts
including an edge case, must run and exit 0, Java support and its two class
rules, `--no-code` for whiteboard sessions, revisions not gated).

Only two things differ here:

- Problem ids are `B75-###`, not `OBS-###`/`CPX-###`.
- Files live in this directory, not `solutions/`.

`update_progress.py --track blind75` finds this directory on its own. To run the
gate by hand you must name it, because `run_checks.py` has no track flag:

    python3 scripts/run_checks.py B75-001 --solutions-dir tracks/blind75/solutions
    make check-solution PROBLEM=B75-001 TRACK=blind75

This file is regenerated by `scripts/generate_blind75_track.py`; your solution
files next to it are never touched.
"""


def has_recorded_work(path: Path) -> bool:
    """Whether a progress file already holds real learner history."""

    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # Unreadable: assume it matters rather than risk clobbering it.
        return True
    if not isinstance(payload, dict):
        return True
    return bool(payload.get("completed")) or bool(payload.get("mock_interviews"))


def has_catalog_entries(path: Path) -> bool:
    """Whether a mistake catalog already holds recorded entries."""

    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return True
    return not isinstance(payload, dict) or bool(payload.get("entries"))


def write_track(
    out_dir: Path, files: dict[str, dict], seeds: dict[str, str], frequency: Path | None
) -> list[tuple[str, str]]:
    """Write the track, never clobbering anything the learner has written into.

    The generator is re-runnable by design (regenerate after a curriculum fix)
    and everything derived is safe to rewrite. The learner-owned files are not:
    progress.json, the mistake catalog, and the three markdown logs are this
    track's own record and are seeded once, then left alone forever.
    """

    out_dir.mkdir(parents=True, exist_ok=True)
    preserved: list[tuple[str, str]] = []

    for name, payload in files.items():
        target = out_dir / name
        if name == "progress.json" and has_recorded_work(target):
            preserved.append((name, "it already holds recorded work"))
            continue
        if name == "mistake_catalog.json" and has_catalog_entries(target):
            preserved.append((name, "it already holds recorded entries"))
            continue
        save_json_file(target, payload)

    # Markdown logs: seeded on first generation, never rewritten afterwards.
    # Unlike the JSON files these have no machine-readable "is it empty" test,
    # so existence alone protects them.
    for name, text in seeds.items():
        target = out_dir / name
        if target.exists():
            preserved.append((name, "it is seeded once and then owned by you"))
            continue
        target.write_text(text)

    # The interview-frequency snapshot is keyed by LeetCode slug, so the track's
    # copy starts as a copy of the main track's. It is still the track's own
    # file: `fetch_interview_frequency.py --track <name>` refreshes each
    # independently, and neither reads the other's.
    if frequency is not None and frequency.exists():
        target = out_dir / "interview_frequency.json"
        if target.exists():
            preserved.append(("interview_frequency.json", "refresh it with make refresh-frequency"))
        else:
            shutil.copyfile(frequency, target)

    solutions = out_dir / "solutions"
    solutions.mkdir(exist_ok=True)
    (solutions / "README.md").write_text(SOLUTIONS_README)
    return preserved


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the Blind 75 curriculum track.")
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Directory to write the track into. Defaults to tracks/blind75.",
    )
    parser.add_argument(
        "--plan-start",
        default=DEFAULT_PLAN_START,
        help=f"ISO date the sprint plan's week 1 starts. Defaults to {DEFAULT_PLAN_START}.",
    )
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip the validate_curriculum.py run over the generated track.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    out_dir = Path(args.out_dir) if args.out_dir else ROOT / "tracks" / TRACK

    try:
        main_paths = track_paths("main")
        main_curriculum = load_json_file(main_paths.curriculum)
        main_graph = load_json_file(main_paths.graph)
        main_stages = load_json_file(main_paths.stages)
        main_skills = load_json_file(main_paths.skills)
        main_patterns = load_json_file(main_paths.patterns)
        main_scoring = load_json_file(main_paths.scoring)
        main_template = load_json_file(main_paths.progress_template)
        plan_start = date.fromisoformat(args.plan_start)

        selected = select_source_problems(main_curriculum, main_stages["stage_order"])
        curriculum, id_map = build_curriculum(selected)
        skills = build_skills(main_skills, curriculum)
        stages = build_stages(main_stages, skills)
        graph = build_graph(main_graph, skills, curriculum, id_map)
        patterns = build_patterns(main_patterns, id_map, skills)
        scoring = build_scoring(main_scoring, curriculum, stages)
        progress = build_progress(main_template, stages)
        plan = build_plan(curriculum, plan_start)

        if scoring["revision_policy"] != main_scoring["revision_policy"]:
            raise RepositoryError(
                "Track revision_policy must stay identical to the main track's: "
                "interval scheduling is still driven by module-level config."
            )

        state = RepositoryState(
            curriculum=curriculum,
            graph=graph,
            stages=stages,
            skills=skills,
            patterns=patterns,
            scoring=scoring,
            progress=progress,
            progress_path=out_dir / "progress.json",
        )
        normalize_progress(state, progress)
        selection = select_next_problem(state, on_date=plan_start)

        # The emitted curriculum keeps `derived_from_id` for traceability; the
        # validator only knows the required fields, so it is a harmless extra.
        preserved = write_track(
            out_dir,
            {
                "curriculum.json": curriculum,
                "dependency_graph.json": graph,
                "stages.json": stages,
                "skills.json": skills,
                "patterns.json": patterns,
                "scoring.json": scoring,
                "progress.json": progress,
                "progress_template.json": progress,
                "plan.json": plan,
                "mistake_catalog.json": EMPTY_MISTAKE_CATALOG,
            },
            {
                "mentor_memory.md": MENTOR_MEMORY_SEED,
                "thinking_patterns.md": THINKING_PATTERNS_SEED,
                "interview_playbook.md": INTERVIEW_PLAYBOOK_SEED,
            },
            main_paths.interview_frequency,
        )
    except (RepositoryError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Generated the {TRACK} track in {out_dir}:")
    print(f"- Problems: {len(curriculum['problems'])}")
    print(f"- Skills: {len(skills['skill_order'])}")
    print(f"- Stages: {len(stages['stage_order'])} ({', '.join(stages['stage_order'])})")
    print(f"- Patterns: {len(patterns['pattern_order'])}")
    print(f"- Plan: {len(plan['weeks'])} weeks, {plan['quarter']['target_new_solves']} solves")
    first = selection.problem["id"] if selection.problem else "none"
    print(f"- First scheduled problem: {first} ({selection.mode})")
    for name, reason in preserved:
        print(f"- KEPT existing {name}: {reason}, so it was not rewritten.")

    if args.skip_validate:
        return 0
    sys.stdout.flush()  # keep our summary above the validator's output
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_curriculum.py"), "--track", TRACK],
        cwd=ROOT,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
