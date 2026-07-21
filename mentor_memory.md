# Mentor Memory — student profile (state only; process lives in mentor/mentor_protocol.md)

This file holds *who the student currently is* — durable strengths, gaps,
preferred reasoning, and recurring failure modes — so a new session starts with
context. It holds no protocol, session flow, hint ladder, or review policy;
those live solely in `mentor/mentor_protocol.md`. Keep this synced with
`progress/progress.json.thinking_profile`, which is the authoritative source.

## Strengths

- Builds concrete examples and edge cases before optimizing.
- Challenges assumptions (including the mentor's) by constructing counterexamples.
- Reasons with explicit correctness proofs and derives algorithms from invariants
  and state transitions rather than memorizing solutions.
- Compresses state only after proving redundancy mathematically.
- Thinks in reachable frontiers / candidate-relative state; separates a local
  hypothesis from global feasibility (Gas Station, Jump Game).
- Reproduces mastered algorithms from memory with correct state, transition,
  previous-state preservation, dry run, and complexity (Maximum Product Subarray).
- Derives the minimal data structure from the repeated query in a problem
  (HashMap for index lookup in CPX-001; HashSet for membership in CPX-002).

## Gaps

- Sometimes optimizes implementation before the correctness proof is complete;
  should keep correctness proofs separate from efficiency arguments.
- Occasionally redesigns initialization before verifying loop invariants and edge
  cases (notably all-negative inputs) still hold.
- **Current focus — Implementation Engineering:** can derive the correct algorithm
  but must derive initialization, loop boundaries, update ordering, global answer
  ownership, and return value *from the state definition* before coding.

## Preferred reasoning patterns

- State-transition reasoning; running max/min state preservation.
- Greedy candidate elimination; candidate-relative state.
- Observation-vs-hypothesis separation; proof-driven implementation.
- Bidirectional constraint satisfaction.
- Repeated query → required state → minimal data structure.

## Recurring failure modes

- May change initialization before questioning loop boundaries.
- May assume every discovered valid state must be preserved before checking
  whether some states dominate others.
- May initialize tracked state to a convenient neutral value before verifying it
  represents a valid candidate under the invariant.
- May mix local DP state with the final answer variable when translating to code,
  or place the global-answer update after the loop instead of immediately after
  the state transition that creates a new candidate.

## Notes for next session

- The main open growth edge is Implementation Engineering, not algorithm
  discovery — coach the layer that fails, not both.
- OBS-002 R2 showed the earlier implementation gap did not recur (from-memory
  solve, no hints, no mistakes).
- OBS-008 (Candy): O(n)-space two-pass greedy is mastered; the O(1)-space
  optimization is an intentionally deferred open learning, not a weakness.
