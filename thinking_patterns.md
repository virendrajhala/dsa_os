
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
