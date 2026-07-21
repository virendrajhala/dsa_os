# DSA_OS

DSA_OS is a production-grade apprenticeship repository for data structures and algorithms.

It is not a problem dump and it is not a Leetcode tracker. The repository is designed to support a 6-9 month preparation journey focused on transferable interview thinking: reading precisely, building examples, grounding in brute force, identifying invariants, selecting the right pattern, communicating tradeoffs, and revising weak spots deliberately.

The curriculum is derived from the PDF source `DSA_Questions_and_Patterns_500.pdf (1).pdf`. All 507 original problems are preserved and mapped back through `original_number`, then reorganized by learning dependency instead of PDF order. An additional 50 supplemental problems (marked `"supplemental": true`, `original_number: null`) were added on top to close specific coverage gaps — see `curriculum/curriculum.json`'s `source` block and `curriculum/dsa-skill-map.md` for the full breakdown. The curriculum currently totals 557 problems across 90 skills and 13 stages (see `knowledge/skills.json` and `curriculum/stages.json`); every problem's `primary_skill` determines its stage, replacing the old `pattern`/`module` fields.

## Installation

DSA_OS has no external runtime dependencies. Python `3.10+` is sufficient — nothing to `pip install`.

```bash
python3 --version
```

## Quick Start

1. Validate the repository state.
   `make validate`
2. Inspect the current dashboard.
   `make dashboard`
3. Open the full web dashboard.
   `make web-dashboard`
4. Select the next problem.
   `make next`
5. Solve the problem using the case file template and constitution.
6. Record the session or revision result.
   `make progress ARGS="--problem-id OBS-001 ..."`
7. Review revision pressure.
   `make revise`
8. Generate a weakness-targeted practice plan.
   `make weakness`

## Workflow

The repository operates in a tight loop.

1. `scripts/validate_curriculum.py` checks curriculum, dependency, stage, scoring, and progress integrity.
2. `scripts/next_problem.py` selects the next dependency-safe task using revision urgency, skill continuity, and stage order.
3. `templates/case_file_template.md` captures the session thinking process.
4. `scripts/update_progress.py` records a new solve or active-recall revision result, appends history, updates revision state, promotes stage when earned, and selects the next problem automatically.
5. `scripts/revision_report.py` reports due active-recall revisions, quarterly maintenance, open deferred learnings, and trend data.
6. `scripts/dashboard.py` gives a compact console operating view for daily use.
7. `scripts/serve_dashboard.py` serves the full browser dashboard from `web_dashboard/`.
8. `scripts/weakness_lab.py` accumulates learner weaknesses and generates targeted practice questions.

## Repository Architecture

The repository keeps one source of truth per concern.

- `curriculum/curriculum.json`
  The canonical syllabus, problem metadata, dependency-aware ordering, and PDF mapping.
- `curriculum/dependency_graph.json`
  Module prerequisites and unlock flow.
- `curriculum/stages.json`
  The stage model and graduation criteria.
- `progress/progress.json`
  The live learner state.
- `progress/progress_template.json`
  A resettable seed file with the same schema as the live progress file.
- `knowledge/patterns.json`
  Stable knowledge-layer index of transferable thinking models, recognition
  signals, proof ideas, contrasts, and linked problems/skills.
- `progress/scoring.json`
  Thinking rubric, independent implementation engineering rubric, interview rubric, revision recall rubric, promotion thresholds, hint levels, and revision policy.
- `docs/DSA_OS_MASTER.md`
  The constitution: philosophy, rules, thinking pipeline, revision model, and scoring logic.
- `mentor/mentor_protocol.md`
  The operational protocol for guided sessions.
- `mentor/error_taxonomy.md`
  Mandatory mistake taxonomy for separating algorithm knowledge errors from
  implementation translation errors.
- `scripts/`
  Operational tooling for validation, next selection, progress updates, reports, and dashboard output.

## Daily Usage

Typical daily flow:

1. `make dashboard`
2. `make web-dashboard`
3. `make next`
4. Open `templates/case_file_template.md`
5. Solve the selected problem
6. Record the session with `make progress ARGS="..."`
7. Re-run `make dashboard`
8. Run `make weakness` when you want focused practice for repeated mistakes.

Typical progress update command:

```bash
make progress ARGS="\
  --problem-id OBS-001 \
  --time-taken-minutes 42 \
  --hint-level-used 2 \
  --confidence-before 3 \
  --confidence-after 8 \
  --thinking-breakthrough 'Reframed it as an invariant scan.' \
  --main-mistake 'Tried to optimize before locking the brute force.' \
  --thinking-score understanding=3 \
  --thinking-score examples=3 \
  --thinking-score brute_force=3 \
  --thinking-score pattern_detection=4 \
  --thinking-score algorithm_design=3 \
  --thinking-score complexity_analysis=3 \
  --thinking-score implementation=3 \
  --thinking-score communication=4 \
  --algorithm-thinking-score 7.5 \
  --implementation-engineering-score 7.5 \
  --interview-score understanding=7 \
  --interview-score communication=8 \
  --interview-score algorithm=7 \
  --interview-score coding=7 \
  --interview-score complexity=8"
```

## Revision Workflow

Revisions are state-based active recall, not passive date checks.

- Every solve records a per-problem `revision` object in `progress/progress.json`.
- A problem becomes mastered only after four successful recall stages: R1 after 3 days, R2 after 7 days, R3 after 21 days, and R4 after 60 days.
- A revision only advances when the learner completes pattern recall, state
  recall, transition recall, complexity recall, implementation blueprint, code
  from memory, dry run, edge cases, and interview discussion with minimal or no
  hints.
- Failed revisions do not advance. They keep the same stage and become due again tomorrow.
- `scripts/next_problem.py` prioritizes due ACTIVE/FAILED revisions before new work.
- MASTERED problems leave normal revision scheduling and enter deterministic quarterly maintenance every 90 days.
- If a later problem exposes a weak prerequisite, `scripts/update_progress.py --reactivate-problem PROBLEM_ID` restores that prerequisite to ACTIVE revision; MASTERED prerequisites restart at stage 3.

This is spaced retrieval: elapsed time makes a recall attempt due, but only successful recall changes mastery state.

Older progress files using `revision_schedule` and `next_revision_date` are migrated automatically by the scripts into the current progress schema.

## Deferred Learnings

Some sessions pass while leaving a specific learning unfinished: boundary
reasoning, initialization, proof, optimization intuition, implementation
engineering, or interview explanation. These are recorded as
`progress.deferred_learnings`, not as failures.

Deferred learnings keep only minimal normalized state: id, origin problem,
origin revision stage when applicable, skill, category, description, priority,
status, and resolution evidence. They do not change problem order and they are
not a scheduler priority. The normal curriculum continues; the mentor watches
future problems and revisions for natural evidence that closes the open item.

Examples:

```bash
python3 scripts/update_progress.py ... \
  --deferred-learning "boundary_conditions=Loop boundary reasoning needs one more future proof." \
  --deferred-learning-priority MEDIUM

python3 scripts/update_progress.py ... \
  --resolve-deferred-learning DL-001 \
  --deferred-learning-evidence "Correctly derived loop boundaries on GRE-006 without hints."
```

Older progress files without `deferred_learnings` are migrated automatically by
the scripts into the schema-version-8 progress schema.

## Implementation Engineering

Implementation Engineering is a global core competency, not a new curriculum
stage. It applies inside every stage and every mentor session.

Before writing any code, the learner must complete the Implementation
Blueprint:

- State: what every variable represents.
- Initialization: initial values and why they satisfy the state definition.
- Loop: start, end, direction, and why.
- Previous state: whether old values must be preserved.
- Answer: local/global ownership and update point.
- Return: exact returned value.

Every coding session records two independent 0-10 scores:

- Algorithm Thinking: pattern recognition, state design, transition, complexity.
- Implementation Engineering: initialization, loop bounds, previous-state
  handling, update ordering, answer maintenance, return value, edge cases.

Implementation mistakes update `progress.implementation_engineering` and must
not reduce Algorithm Thinking unless the root cause is actually algorithmic.

## Knowledge Layer

The `knowledge/` directory stores stable curriculum-level concepts, not
learner-specific state.

- `knowledge/skills.json`: abilities the curriculum trains.
- `knowledge/patterns.json`: transferable recognition models that connect
  problems to reusable mental models, proof ideas, complexity reasoning,
  contrasts, and common mistakes.

Patterns are conceptual, not algorithm-name tags. Prefer names such as
`Greedy Candidate Elimination`, `Reachability Frontier`, `Prefix Extremum`,
or `Two Competing States` over problem names or memorized technique labels.

## Developer Experience

The repository ships with a Makefile.

- `make validate`
- `make dashboard`
- `make web-dashboard`
- `make next`
- `make revise`
- `make stats`
- `make weakness`
- `make progress ARGS="..."`

Each Python CLI includes help output:

```bash
python3 scripts/validate_curriculum.py --help
python3 scripts/next_problem.py --help
python3 scripts/update_progress.py --help
python3 scripts/revision_report.py --help
python3 scripts/dashboard.py --help
python3 scripts/serve_dashboard.py --help
python3 scripts/weakness_lab.py --help
```

The browser dashboard is available at `http://127.0.0.1:8765/web_dashboard/`
after running `make web-dashboard`. It reads the canonical repository files
directly and does not mutate progress state.

## Contribution Guide

This repository is meant to stay stable.

- Do not change the philosophy casually.
- Do not change the dependency order without a genuine curriculum inconsistency.
- Keep `original_number` unchanged forever.
- New problems may reference existing patterns. New patterns should be rare
  and require a genuinely new transferable way of thinking.
- Run `make validate` after every data or script change.
- Treat `progress/progress.json` as live state and `progress/progress_template.json` as the reset source.
- Prefer additive, source-preserving fixes over broad rewrites.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).


https://github.com/virendrajhala/dsa_os/archive/refs/heads/main.zip
