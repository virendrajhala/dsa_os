# Mentor Memory — student profile (state only; process lives in mentor/mentor_protocol.md)

This file holds *who the student currently is* — durable strengths, gaps,
preferred reasoning, and recurring failure modes — so a new session starts with
context. It holds no protocol, session flow, hint ladder, or review policy;
those live solely in `mentor/mentor_protocol.md`. Keep this synced with
`progress/progress.json.thinking_profile`, which is the authoritative source.

**This is the main (582) track's profile.** Tracks share nothing: the Blind 75
track keeps its own at `tracks/blind75/mentor_memory.md`, and the two are never
merged. Everything below is evidenced by main-track sessions and cites
main-track problem ids.

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
- Distinguishes constraint-specific direct addressing from a general HashMap:
  for CPX-006, used the bounded key range to justify O(1) array indexing and
  the O(maxKey) space tradeoff.

## Gaps

- Sometimes optimizes implementation before the correctness proof is complete;
  should keep correctness proofs separate from efficiency arguments.
- Occasionally redesigns initialization before verifying loop invariants and edge
  cases (notably all-negative inputs) still hold.
- **Current focus — Implementation Engineering:** can derive the correct algorithm
  but must derive initialization, loop boundaries, update ordering, global answer
  ownership, and return value *from the state definition* before coding.
- Skips the Implementation Blueprint when eager to code. On the CPX-004 R1
  revision it was requested explicitly, deflected twice, and never delivered —
  and the code that followed carried three defects the blueprint would have
  caught (mutating accessor, default-zero initialization, unwidened arithmetic).
- Treats an operation's cost as the algorithm's work alone, ignoring the backing
  container. Conflated *amortized* with *average case* on CPX-004 and claimed all
  four operations were worst-case O(1) on an array-backed stack.
- States invariants informally ("the minimum found till now") where the precise
  set matters ("the minimum over elements currently in the stack"). The loose
  phrasing is literally false after a pop that removes the minimum.

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
- May write a read accessor using a destructive API (`pop()` where `peek()` was
  meant), desynchronizing structures that must move in lockstep. The failure
  surfaces far from its cause.
- May guess a sign or transpose a formula instead of dry-running it, and may dry
  -run the code intended rather than the code actually written. Both appeared on
  CPX-004 R1: a guessed sign flip on the encoding, and a trace that assumed a
  correct constructor the code did not have.

## Notes for next session

- The main open growth edge is Implementation Engineering, not algorithm
  discovery — coach the layer that fails, not both.
- OBS-002 R2 showed the earlier implementation gap did not recur (from-memory
  solve, no hints, no mistakes).
- OBS-008 (Candy): O(n)-space two-pass greedy is mastered; the O(1)-space
  optimization is an intentionally deferred open learning, not a weakness.
- CPX-004 R1 (2026-08-07) FAILED and retries 2026-08-08 at stage 0. Algorithm
  recall was strong — concept, invariant, proof, duplicate handling and both
  designs rebuilt from memory. It failed the complexity gate (amortized vs
  worst-case had to be taught) and the blueprint gate (never delivered). On the
  retry, hold the blueprint requirement hard and open with the amortized
  question; do not re-teach the encoding, which was re-derived as reflection and
  is now recorded as thinking pattern 006.
- M005 (widen every variable in an overflowing expression) recurred on the
  CPX-004 R1 rebuild fourteen days after it was catalogued. Watch for decay on
  catalogued implementation mistakes specifically, not just on algorithms.
- CPX-006 is complete only for LeetCode's bounded-key direct-addressing design.
  Do not treat separate chaining, collision handling, load factor, resizing,
  rehashing, amortized implementation, or Java HashMap internals as mastered;
  CPX-007 is the independent follow-up for that implementation layer.
- OBS-003 R2 (2026-08-13) PASSED with mentor-derived scores. Recall was solid
  after clarification, but invariant wording and global-answer proof needed
  tightening. Keep coaching exact state boundaries, and watch for implementation
  condition drift where a local comparison replaces the maintained invariant
  state (`prices[i] < prices[i-1]` instead of `prices[i] < minPrice`).
