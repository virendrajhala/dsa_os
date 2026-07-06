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
- Do not let code begin before the data flow is stable.
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
8. Implement
   Translate the plan without changing the plan.
9. Reflect
   Record what unlocked the problem and what almost caused failure.

## Hint System

Hints escalate by level.

1. Constraint Hint
   Focus on what must stay true.
2. Example Hint
   Ask for a sharper example or edge case.
3. State Hint
   Ask what variable, pointer, count, stack, or table should be tracked.
4. Structure Hint
   Ask whether the problem has ordering, monotonicity, adjacency, or subproblem overlap.
5. Pattern Hint
   Narrow the pattern family without giving the algorithm.
6. Algorithm Hint
   Reveal the next concrete step, not the full solution.
7. Recovery Hint
   If the student is stuck after partial progress, point to the broken invariant.

Hints should move from local friction to global structure.

## Session Flow

Each session follows the same operating sequence.

1. Select the next problem from the unlocked set.
2. Open a case file.
3. Restate the problem and constraints.
4. Build examples.
5. Produce brute force.
6. Search for the invariant.
7. Name the pattern.
8. Design the optimized algorithm.
9. Analyze complexity.
10. Implement.
11. Explain the solution as if in an interview.
12. Score the session and update progress.

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

The repository uses layered revision.

### Immediate Revision

Triggered when the solve is incorrect or overly prompt-dependent.

### Short-Horizon Revision

Triggered within a few sessions for problems with weak invariants or weak communication.

### Pattern Revision

Triggered when multiple problems in one pattern show the same failure mode.

### Long-Horizon Revision

Triggered after a stage transition to verify that older patterns still transfer.

Revision is not repetition for its own sake. Each return should have a narrow purpose:

- recover the invariant
- shorten the explanation
- remove prompts
- improve implementation hygiene

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

1. due revision items
2. unlocked problems in the current module
3. unlocked problems in the current stage
4. the earliest unlocked dependency-safe problem in the curriculum

Selection rules:

- Stay within one active cognitive context when possible.
- Prefer breadth only after the current invariant family is stable.
- Hard variants should follow a stable solve of the easier base family.
- Revisited problems from the source should stay in the system because they measure transfer, not memory.

## Repository Discipline

- Keep `original_number` unchanged forever.
- Keep generated IDs stable once they are published.
- Change the dependency graph only with a deliberate curriculum reason.
- Run validation after any structural edit.
- Treat the repository as an operating system, not a notebook.
