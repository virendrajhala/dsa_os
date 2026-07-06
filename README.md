# DSA_OS

DSA_OS is a long-horizon apprenticeship repository for data structures and algorithms.

It is not a problem dump and it is not a Leetcode tracker. It is a dependency-first operating system for a 6-9 month preparation cycle whose real target is transferable interview thinking: reading precisely, building examples, extracting invariants, choosing the right pattern, explaining tradeoffs, and revising systematically.

The repository is built from the PDF syllabus `DSA_Questions_and_Patterns_500.pdf (1).pdf` and preserves all 507 numbered problems from that source. The curriculum has then been reorganized by learning dependency so the work can be done in an order that compounds skill instead of merely following the PDF sequence.

## Purpose

DSA_OS exists to make a full preparation journey maintainable.

- The curriculum is one canonical JSON source with stable IDs, source mapping, dependencies, estimated effort, and revision state.
- The mentor protocol defines how a session should be run so that help strengthens reasoning instead of shortcutting it.
- The progress model tracks stage, completed work, revision pressure, and thinking quality.
- The scripts make the repository operational instead of passive.

## Architecture

The repository has five layers.

1. `curriculum/` is the syllabus engine.
   It stores the extracted problems, the module dependency graph, and the stage model.
2. `docs/` is the project constitution.
   It explains the philosophy, rules, scoring, session flow, and revision model.
3. `mentor/` defines how one guided session should behave.
4. `progress/` stores the working state for an apprentice.
5. `scripts/` validates the data model and selects the next problem from actual progress.

The main design choice is separation of concerns:

- `curriculum.json` answers: what exists, where it came from, and how it is ordered.
- `dependency_graph.json` answers: what unlocks what.
- `stages.json` answers: what capability each stage is meant to build.
- `progress_template.json` answers: where the student currently stands.
- `scoring.json` answers: how performance is judged.

## Workflow

Use the repository in this order.

1. Run `python3 scripts/validate_curriculum.py`.
2. Use `python3 scripts/next_problem.py` to select the next unlocked problem.
3. Open `templates/case_file_template.md` and create a case file for the session.
4. Solve using the rules in [`docs/DSA_OS_MASTER.md`](docs/DSA_OS_MASTER.md) and [`mentor/mentor_protocol.md`](mentor/mentor_protocol.md).
5. Score the session with `progress/scoring.json`.
6. Update `progress/progress_template.json` with the result and any revision follow-up.

## Folder Structure

```text
dsa_os/
├── README.md
├── docs/
│   └── DSA_OS_MASTER.md
├── mentor/
│   └── mentor_protocol.md
├── curriculum/
│   ├── curriculum.json
│   ├── dependency_graph.json
│   └── stages.json
├── progress/
│   ├── progress_template.json
│   └── scoring.json
├── templates/
│   └── case_file_template.md
└── scripts/
    ├── next_problem.py
    └── validate_curriculum.py
```

## How To Continue Learning

Treat the repository as a loop, not a checklist.

- Stay inside the current stage until its graduation criteria are consistently met.
- Prefer depth over breadth: one thoroughly solved problem with a strong reflection is worth more than five shallow submissions.
- Keep the revision queue alive. Any weak solve should return later with a narrower objective.
- When a pattern feels familiar, intentionally switch to unseen variants before moving on.
- Re-read the constitution periodically. The process matters as much as the eventual code.

Recommended cadence:

- `5` active solve sessions per week.
- `1` revision-heavy session per week.
- `1` communication-only session per week where the solution is explained aloud without coding.

## How Progress Works

Progress is stage-based, not streak-based.

- `current_stage` records the active capability band.
- `current_problem` records the active problem being worked.
- `completed` stores finished problem IDs.
- `revision_queue` stores follow-up work triggered by weak spots or time-delayed review.
- `thinking_profile` records repeated strengths and repeated failure modes.
- `scores` stores the latest and aggregate scoring view.
- `history` stores session-level events.

The scoring system uses weighted dimensions such as understanding, brute force quality, pattern detection, algorithm design, complexity analysis, implementation, and communication. Promotion is earned only when both volume and quality clear the thresholds defined in `progress/scoring.json`.

## Maintenance

This repository is intended to survive long-term use.

- Run the validator after any curriculum edit.
- Keep `original_number` untouched so the PDF mapping never breaks.
- Keep new IDs stable once work has started against them.
- If the pedagogy changes, change the dependency graph and stage model deliberately, then revalidate.
