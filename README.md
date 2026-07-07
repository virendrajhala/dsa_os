# DSA_OS

DSA_OS is a production-grade apprenticeship repository for data structures and algorithms.

It is not a problem dump and it is not a Leetcode tracker. The repository is designed to support a 6-9 month preparation journey focused on transferable interview thinking: reading precisely, building examples, grounding in brute force, identifying invariants, selecting the right pattern, communicating tradeoffs, and revising weak spots deliberately.

The curriculum is derived from the PDF source `DSA_Questions_and_Patterns_500.pdf (1).pdf`. All 507 problems are preserved and mapped back through `original_number`, then reorganized by learning dependency instead of PDF order.

## Installation

DSA_OS has no external runtime dependencies. Python `3.10+` is sufficient.

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick Start

1. Validate the repository state.
   `make validate`
2. Inspect the current dashboard.
   `make dashboard`
3. Select the next problem.
   `make next`
4. Solve the problem using the case file template and constitution.
5. Record the session.
   `make progress ARGS="--problem-id OBS-001 ..."`
6. Review revision pressure.
   `make revise`

## Workflow

The repository operates in a tight loop.

1. `scripts/validate_curriculum.py` checks curriculum, dependency, stage, scoring, and progress integrity.
2. `scripts/next_problem.py` selects the next dependency-safe task using revision urgency, module continuity, and stage order.
3. `templates/case_file_template.md` captures the session thinking process.
4. `scripts/update_progress.py` records the solve, appends history, rotates the revision schedule, promotes stage when earned, and selects the next problem automatically.
5. `scripts/revision_report.py` reports revision pressure and trend data.
6. `scripts/dashboard.py` gives a compact operating view for daily use.

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
- `progress/scoring.json`
  Thinking rubric, interview rubric, promotion thresholds, hint levels, and revision policy.
- `docs/DSA_OS_MASTER.md`
  The constitution: philosophy, rules, thinking pipeline, revision model, and scoring logic.
- `mentor/mentor_protocol.md`
  The operational protocol for guided sessions.
- `scripts/`
  Operational tooling for validation, next selection, progress updates, reports, and dashboard output.

## Daily Usage

Typical daily flow:

1. `make dashboard`
2. `make next`
3. Open `templates/case_file_template.md`
4. Solve the selected problem
5. Record the session with `make progress ARGS="..."`
6. Re-run `make dashboard`

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
  --interview-score understanding=7 \
  --interview-score communication=8 \
  --interview-score algorithm=7 \
  --interview-score coding=7 \
  --interview-score complexity=8"
```

## Revision Workflow

Revisions are scheduled, not implied.

- Every solve records `next_revision_date` in `progress/progress.json`.
- `revision_schedule` stores `problem`, `date`, `reason`, `priority`, and `status`.
- `scripts/next_problem.py` prioritizes due revisions before new work.
- `scripts/revision_report.py` separates today's revisions from overdue revisions.

The revision schedule is the authoritative source for follow-up work. It replaces the old queue model.

## Developer Experience

The repository ships with a Makefile.

- `make validate`
- `make dashboard`
- `make next`
- `make revise`
- `make stats`
- `make progress ARGS="..."`

Each Python CLI includes help output:

```bash
python3 scripts/validate_curriculum.py --help
python3 scripts/next_problem.py --help
python3 scripts/update_progress.py --help
python3 scripts/revision_report.py --help
python3 scripts/dashboard.py --help
```

## Contribution Guide

This repository is meant to stay stable.

- Do not change the philosophy casually.
- Do not change the dependency order without a genuine curriculum inconsistency.
- Keep `original_number` unchanged forever.
- Run `make validate` after every data or script change.
- Treat `progress/progress.json` as live state and `progress/progress_template.json` as the reset source.
- Prefer additive, source-preserving fixes over broad rewrites.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).


https://github.com/virendrajhala/dsa_os/archive/refs/heads/main.zip