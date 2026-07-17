# Error Taxonomy

Every mistake must be classified using exactly one category. Do not mix
algorithm-knowledge failures with implementation-translation failures.

## Category A — Pattern Selection Error

Wrong algorithm.

Use when the learner selected the wrong reasoning family or pattern for the
problem.

## Category B — State Design Error

Wrong DP state or invariant.

Use when the learner understood the broad pattern but defined the wrong state,
invariant, or meaning for tracked variables.

## Category C — Transition Error

Incorrect recurrence/update.

Use when the state is meaningful but the recurrence, greedy decision, or update
rule is wrong.

## Category D — Implementation Engineering Error

The learner understood the algorithm but translated it incorrectly.

Includes:

- Wrong initialization
- Wrong starting index
- Wrong ending boundary
- Wrong update ordering
- Forgetting previous state
- Incorrect return variable
- Incorrect answer update location
- Variable ownership mistakes
- Off-by-one mistakes
- Incorrect loop direction

## Category E — Language/Syntax Error

Missing semicolons, syntax mistakes, API misuse.

Use only when the issue is language mechanics rather than algorithm reasoning
or implementation engineering.
