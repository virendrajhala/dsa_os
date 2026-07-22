# DSA_OS Master Document

## Mission

DSA_OS exists to train problem solvers who can handle unfamiliar interview questions under pressure.

The mission is not memorization.

The mission is to build durable reasoning:

- precise reading
- example construction
- brute-force grounding
- invariant discovery
- pattern selection
- complexity judgment
- implementation engineering
- clear communication

Every artifact in this repository should reinforce those behaviors.

## Learning Philosophy

The curriculum follows six principles.

1. Source accuracy before pedagogy.
   The problem list is preserved from the syllabus source and mapped back with `original_number`.
2. Dependency before variety.
   Problems are sequenced by what they teach, not by where they appeared originally.
3. Brute force before optimization.
   Fast solutions without a baseline usually produce shallow understanding.
4. Explanation before code.
   If the reasoning cannot be explained, the implementation is not trusted.
5. Revision before ego.
   Weak solves return to the revision schedule.
6. Stages before streaks.
   Advancement is earned through capability, not merely volume.

## Mentor Rules

- Ask one question at a time.
- Do not reveal the pattern immediately.
- Do not reveal the final algorithm immediately.
- Force a correct brute-force baseline first.
- Increase hints gradually and only after effort is visible.
- Challenge vague language.
- Ask for invariants, not intuition alone.
- Ask for complexity only after the algorithm is concrete.
- Do not let code begin before the Implementation Blueprint is complete.
- Separate algorithm knowledge errors from implementation engineering errors.
- Update progress after every session.

## Student Rules

- Restate the problem before solving.
- Build examples before proposing an optimization.
- Produce a brute-force solution before pattern talk.
- Name the invariant that makes the optimized version work.
- Explain why rejected approaches fail.
- State time and space complexity without hand-waving.
- Reflect on the miss if the solve required heavy prompting.
- Respect the revision schedule.

## Thinking Framework

Use the same mental pipeline every time.

1. Clarify
   Define input, output, constraints, and the actual objective.
2. Materialize
   Build examples, edge cases, and one adversarial case.
3. Baseline
   Produce the simplest correct solution.
4. Observe
   Ask what work is repeated or what structure is monotonic, ordered, or bounded.
5. Pattern Match
   Choose the narrowest fitting pattern, not the most impressive one.
6. Design
   Describe the algorithm step by step with state changes.
7. Analyze
   Defend time and space complexity.
8. Implementation Blueprint
   Derive state, initialization, loop bounds, previous-state needs, answer
   maintenance, and return value before code.
9. Implement
   Translate the plan without changing the plan.
10. Reflect
   Record what unlocked the problem and what almost caused failure.

## Hint System

The single canonical hint ladder (levels 0-7, matching
`progress/scoring.json.hint_levels`, which is what `update_progress.py`
validates `--hint-level-used` against) lives in the Hint Ladder section of
`mentor/mentor_protocol.md`. That file is authoritative; this document does not
keep a second copy.

## Session Flow

The session flow is defined by the state machine in
`mentor/mentor_protocol.md` — that file is authoritative. It runs from reading
and restating the problem through examples, brute force, invariant discovery,
proof, algorithm design, the Implementation Blueprint, implementation, the
mandatory post-code review, and the retrospective (where Algorithm Thinking and
Implementation Engineering are scored separately and progress is updated). The
pattern is never named for the student — the mentor waits for the student to
discover the governing invariant.

## Implementation Engineering

Implementation Engineering is a global core competency, not a curriculum
stage. It is the ability to translate an understood algorithm into bug-free
code by deriving initialization, loop boundaries, state ownership, update
ordering, previous-state preservation, global answer maintenance, and return
value from the state definition.

Before any code, the learner completes the Implementation Blueprint, and after
code the mentor runs the mandatory post-code review in a fixed order. Both the
blueprint form and the review order are defined once in
`mentor/mentor_protocol.md` — that file is authoritative; they are not copied
here.

## Problem Solving Pipeline

Use this pipeline when the difficulty spikes.

### 1. Understand The Shape

- Is the input linear, hierarchical, or graph-like?
- Are there range queries, dynamic updates, or repeated searches?
- Is the goal exact, minimum, maximum, count, existence, or construction?

### 2. Establish A Baseline

- What is the naive complete search?
- Can it be written with no hidden assumptions?
- What repeated work is obvious in that version?

### 3. Compress The Repeated Work

- Repeated comparisons suggest pointers, windows, or sorting.
- Repeated range work suggests prefix sums or indexed structures.
- Repeated best-choice maintenance suggests stacks, queues, or heaps.
- Repeated subproblems suggest dynamic programming.
- Repeated reachability reasoning suggests graph traversal.

### 4. Stress The Invariant

- What must be true after each iteration or recursive return?
- How is the invariant restored after mutation?
- Which operation would break it first?

### 5. Finalize The Algorithm

- List the state.
- List the transitions.
- List the exit condition.
- Complete the Implementation Blueprint.
- Then write code.

## Interview Communication Rules

- Start with a concise problem restatement.
- Declare the brute-force baseline before jumping to optimization.
- Name the invariant explicitly.
- Speak in steps, not in code syntax.
- Call out tradeoffs and rejected options.
- When debugging, narrate the mismatch between expectation and current state.
- End with time and space complexity.

Silence is acceptable while thinking. Vagueness is not.

## Revision Strategy

The repository uses state-based spaced retrieval. Time passing only makes a
revision due; it does not prove mastery — only successful active recall
advances a problem toward MASTERED.

The mechanics — the R1-R4 stage intervals, the recall gates a PASS requires,
FAIL rescheduling, and how MASTERED problems return (including quarterly
maintenance) — are defined once in `mentor/mentor_protocol.md` under
"Revision Protocol" and mirrored as config in `progress/scoring.json`
(`revision_policy`). That file is authoritative; they are not copied here.

Revision is not repetition for its own sake. Each return should have a narrow purpose:

- recover the invariant
- shorten the explanation
- remove prompts
- improve implementation hygiene

## Deferred Learning

A passed solve or revision can still leave unfinished learning. That is not a
failure. It should be recorded as a deferred learning when the learner solved
the problem but still needs future evidence for a narrow skill such as
initialization, loop boundaries, invariant proof, optimization intuition,
implementation engineering, complexity derivation, pattern recognition, or
interview communication.

Deferred learnings live in `progress.deferred_learnings`. They reference the
origin problem, skill, category, priority, status, and explicit resolution
evidence. They do not create extra revision sessions and they do not interrupt
the curriculum scheduler. The mentor checks them as context and resolves them
opportunistically when a later problem, revision, explanation, implementation,
or mentor verification naturally proves the learning is now stable.

## Scoring Rubric

Scores are recorded per dimension on a `0-4` scale.

- `understanding`: accurate restatement of task and constraints
- `examples`: quality of examples and edge cases
- `brute_force`: correctness of the baseline approach
- `pattern_detection`: whether the real lever was identified
- `algorithm_design`: correctness and clarity of the optimized plan
- `complexity_analysis`: precision of time and space reasoning
- `implementation`: execution quality after the plan was fixed
- `communication`: clarity, structure, and interview readiness

Every coding session also records two independent `0-10` scores:

- Algorithm Thinking: pattern recognition, state design, transition, and
  complexity.
- Implementation Engineering: initialization, loop bounds, previous-state
  handling, update ordering, answer maintenance, return value, and edge cases.

Never combine these scores. An initialization or loop-boundary miss is an
Implementation Engineering gap unless the underlying algorithm was also wrong.

Interpretation:

- `0`: missed
- `1`: heavily prompt-dependent
- `2`: partially stable
- `3`: independently solid
- `4`: teachable and interview-ready

Promotion is based on both weighted score and completed problem count. Stage thresholds live in `progress/scoring.json`.

## Problem Selection Strategy

The next problem is not chosen randomly.

Priority order:

1. due active-recall revision items
2. unlocked problems in the current skill
3. unlocked problems in the current stage
4. the earliest unlocked dependency-safe problem in the curriculum

Open deferred learnings are deliberately absent from this priority list. They
enrich mentor observation during the selected work; they do not select work by
themselves.

Selection rules:

- Stay within one active cognitive context when possible.
- Prefer breadth only after the current invariant family is stable.
- Hard variants should follow a stable solve of the easier base family.
- Revisited problems from the source should stay in the system because they measure transfer, not memory.

## Knowledge Layer

Stable curriculum-level concepts live under `knowledge/`. Learner-specific
state lives under `progress/`. This boundary must stay clear.

- `knowledge/skills.json` defines abilities trained by the curriculum.
- `knowledge/patterns.json` defines transferable thinking models used for
  recognition, proof, contrast, and cross-problem transfer.

Patterns are not another algorithm catalog. A new pattern should be created
only when it represents a genuinely new transferable way of thinking; otherwise
link the problem to an existing pattern. Pattern entries should explain the
mental model, recognition signals, core invariant, proof idea, complexity
reasoning, contrasts, and common mistakes.

## Repository Discipline

- Keep `original_number` unchanged forever.
- Keep generated IDs stable once they are published.
- Keep knowledge-layer artifacts stable and separate from learner progress.
- Add new patterns rarely; prefer reusing or enriching existing patterns.
- Change the dependency graph only with a deliberate curriculum reason.
- Run validation after any structural edit.
- Treat the repository as an operating system, not a notebook.
