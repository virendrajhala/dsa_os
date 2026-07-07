
# Interview Playbook

## Purpose
This file captures interviewer expectations, follow-up questions, edge cases, and communication patterns.

## Standard Interview Flow
1. Restate the problem.
2. Clarify constraints.
3. Give one example.
4. Explain brute force.
5. State why it is slow.
6. Discover the invariant.
7. Design the optimized algorithm.
8. Analyze complexity.
9. Implement.
10. Dry run.

## Mandatory Communication Rules
- Never jump directly to the optimal algorithm.
- Explain correctness before efficiency.
- Separate local state from global state.
- State invariants explicitly.

## Typical Follow-up Questions
- Why is your greedy decision always safe?
- Can you prove your invariant?
- What happens on all-negative input?
- What edge case breaks a naive implementation?
- Can this be done in O(1) extra space?
- How would you test this?

## Edge-case Checklist
- Empty input (if allowed)
- Single element
- All negative
- All positive
- Duplicates
- Large constraints
- Overflow (if applicable)
