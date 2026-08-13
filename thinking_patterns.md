
# Thinking Patterns

Each entry records a reusable invariant.

This is the main (582) track's log. Tracks share nothing: the Blind 75 track
keeps its own at `tracks/blind75/thinking_patterns.md`. `Related problems` here
name main-track ids only.

## Template
Pattern:
Trigger:
Invariant:
Proof:
Common mistakes:
Related problems:

---

## Pattern 001
Pattern: Local vs Global Optimum

Trigger:
Maintain best ending at current position while tracking overall best.

Invariant:
Local state may decrease; global optimum never decreases.

Problems:
- OBS-001 Maximum Subarray

---

## Pattern 002
Pattern: Negative Prefix Elimination

Trigger:
Accumulated prefix becomes negative.

Invariant:
For any future sum F:
F > F + negative_prefix

Therefore the negative prefix can never improve any future answer.

Proof:
If prefix = -k (k>0):
F > F-k for every F.

Problems:
- OBS-001 Maximum Subarray

---

## Pattern 003
Pattern: Invariant-Valid Initialization

Trigger:
Choosing initial values for a running state.

Invariant:
Initialization values must themselves satisfy the algorithm invariant.

Proof:
If the state is supposed to represent a real non-empty candidate, a neutral value like 0 is invalid unless 0 corresponds to an actual candidate. For Maximum Subarray, initializing runningSum and maxSum with 0 breaks the invariant on all-negative arrays because 0 is not the sum of any chosen non-empty subarray.

Common mistakes:
- Initializing with a convenient neutral value before checking whether it is a valid state.
- Testing only mixed positive/negative arrays and missing all-negative inputs.

Problems:
- OBS-001 Maximum Subarray

---

## Pattern 004
Pattern: Repeated Query -> Required State -> Minimal Data Structure

Trigger:
Brute force repeatedly searches for information that could be remembered.

Invariant:
Before processing the current item, the lookup structure contains exactly the
processed information needed to answer the repeated query.

Proof:
If each decision only needs an existence, index, count, or grouping question
over previously processed values, then storing the minimum state that answers
that question preserves correctness while removing the repeated scan.

Common mistakes:
- Choosing a HashMap or HashSet before naming the repeated query.
- Searching after insertion when the current item must not match itself.
- Explaining O(n) without separating the number of iterations from the lookup
  cost per iteration.

Problems:
- CPX-001 Two Sum
- CPX-002 Contains Duplicate

---

## Pattern 005
Pattern: Bounded Key Space -> Direct Addressing

Trigger:
The problem gives a small fixed key range and operations are keyed directly by
that value.

Invariant:
For every valid key, `table[key]` is the complete stored state for that key.

Proof:
If every key is an integer inside a known bounded range, array indexing maps
each possible key to exactly one storage slot. Lookup, update, and remove do
not need search or collision resolution; they directly read or write that slot.

Common mistakes:
- Calling direct addressing a general HashMap implementation.
- Forgetting that the approach spends O(maxKey) space even when few keys are
  used.
- Using 0 as a missing sentinel when 0 is a valid stored value.

Problems:
- CPX-006 Design a HashMap

---

## Pattern 006
Pattern: Impossible Value Region as Marker Space

Trigger:
Auxiliary state must be stored, but no extra container is allowed. The
structure already guarantees a range of values that real data can never take.

Invariant:
Every genuine element satisfies the structure's own guarantee (for a min-stack,
`element >= min`). Therefore any stored value violating that guarantee is a
marker the algorithm placed there itself, and can be decoded rather than read.

Proof:
Detection needs no flag because the guarantee is total: if no real element can
be below `min`, then `stored < min` is a complete and unambiguous test. To make
the marker also carry the displaced state, store the old value reflected across
the new one — `marker = 2*newMin - prevMin`, so that `newMin` is the midpoint of
`marker` and `prevMin`. Reflection lands the marker below `newMin` automatically
(because `prevMin > newMin`), so detectability is forced by the geometry rather
than arranged. Decoding is the same reflection read backwards:
`prevMin = 2*newMin - marker`.

Common mistakes:
- Memorizing `2x - m` as a formula instead of deriving it from "store the gap
  below the new minimum".
- Transposing encode and decode — they are one equation
  (`2*newMin = marker + prevMin`) solved for different unknowns.
- Trying to store the displaced value directly; it sits above the boundary and
  becomes indistinguishable from real data.
- Forgetting that reflection doubles distance from the origin, so the storage
  type must be wider than the input type.

Related problems:
- CPX-004 Min Stack

---

## Pattern 007
Pattern: Prefix Extremum

Trigger:
A current decision can only use values from earlier positions, and one
historical minimum or maximum dominates all worse historical candidates.

Invariant:
Before processing index `i`, the tracked extremum is the best eligible value
from the processed prefix `0..i-1`.

Proof:
For any fixed current value, a worse historical candidate can never produce a
better result than the best historical extremum. In Best Time to Buy and Sell
Stock, any earlier buy price larger than `minPrice` gives lower profit for the
same sell price, so it can be discarded.

Common mistakes:
- Saying "minimum so far" without naming whether the current index is included.
- Overwriting the prefix extremum on a local dip instead of only on a new global
  prefix extremum.
- Confusing the clearest invariant-preserving update order with the only
  mathematically correct update order.

Related problems:
- OBS-003 Best Time to Buy and Sell Stock
