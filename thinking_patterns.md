
# Thinking Patterns

Each entry records a reusable invariant.

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
