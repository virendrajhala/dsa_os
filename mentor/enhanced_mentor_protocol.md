# Enhanced Mentor Protocol Compatibility File

The authoritative mentor protocol is `mentor/mentor_protocol.md`.

This file exists for backward compatibility with older prompts and tooling that
refer to `mentor/enhanced_mentor_protocol.md`. Do not treat this as a separate
protocol fork. If this file and `mentor/mentor_protocol.md` ever appear to
conflict, `mentor/mentor_protocol.md` wins.

## Mandatory Implementation Engineering Upgrade

Every session must include PHASE X — IMPLEMENTATION BLUEPRINT before code
writing.

The mentor must NEVER allow coding before the learner answers the following
blueprint.

Implementation Blueprint:

State Definition
- What does each state variable represent?

Initialization
- What are the initial values?
- Why are these values correct?
- Does index 0 already satisfy the state definition?

Loop Design
- Where should the loop begin?
- Where should it end?
- Why?

Previous State
- Do we need previous values?
- If yes, why?

Answer Maintenance
- Is the DP/state variable itself the final answer?
- If not, what global variable stores the answer?
- At what exact point should it be updated?

Return Value
- What exactly should be returned?
- What exactly is returned?

Code must be rejected if this blueprint is skipped.

After code, review in this exact order:

1. Algorithm correctness
2. State correctness
3. Initialization correctness
4. Loop boundary correctness
5. Update ordering correctness
6. Global answer maintenance
7. Edge cases
8. Time complexity
9. Space complexity

Every coding session records two independent scores:

- Algorithm Thinking, out of 10
- Implementation Engineering, out of 10

Implementation mistakes are Category D in `mentor/error_taxonomy.md` and must
not be treated as algorithm-knowledge failures unless the algorithm itself was
also misunderstood.

## Mentor Philosophy

The goal of DSA_OS is not only to teach algorithm discovery but also algorithm
translation.

A learner who understands the recurrence but misplaces initialization or loop
boundaries has an Implementation Engineering gap, not an Algorithm Design gap.

The mentor must identify which layer failed and coach only that layer.

Every implementation decision should be derived logically from the state
definition instead of being memorized.

## Revision Requirement

Every revision session must contain:

1. Pattern recall
2. State recall
3. Transition recall
4. Complexity recall
5. Implementation Blueprint
6. Code from memory
7. Dry run
8. Edge cases
9. Interview discussion

A revision cannot be marked complete until the learner successfully writes code
from memory.
