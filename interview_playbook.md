
# Interview Playbook

## Purpose
This file captures interviewer expectations, follow-up questions, edge cases,
and communication patterns, organized per topic. It grows with every problem
completion — see "How This File Grows" below — instead of staying frozen at
whatever problem seeded it.

## Scope
System design and behavioral interviews are OUT of scope for this repo — DSA
only.

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

## Communication Rubric
The authoritative communication rules live in
`docs/DSA_OS_MASTER.md:202-213` ("Interview Communication Rules") and are
graded per the `communication` dimension in `docs/DSA_OS_MASTER.md`'s Scoring
Rubric (~:272). The mock interview protocol
(`mentor/mock_interview_protocol.md:133-146`, rubric dimension 29) applies
those same rules under a timed, unaided interview.

This section does not repeat those rubrics. It only adds the per-phase talk
track that turns the rules into what actually gets said out loud, phase by
phase:

- **Restate**: repeat the problem in your own words, including the return
  type and any implicit constraints (uniqueness, ordering, mutability).
- **Clarify**: ask about input ranges, duplicates, empty/null inputs, and
  whether multiple valid answers are acceptable — before proposing an
  approach.
- **Approach**: state the brute force first, say why it is slow, then state
  the optimized approach and the invariant it relies on, out loud, before
  writing code.
- **Complexity**: give time and space complexity for both the brute force and
  the chosen approach, and say which resource you are trading off.
- **Code narration**: speak in steps, not syntax — describe what a block does
  before or while typing it, not just what it says.
- **Walkthrough**: dry-run a normal case, an edge case, and an adversarial
  case you chose yourself; narrate the expectation-vs-state mismatch if a
  trace surfaces a bug.

## How This File Grows
Per `AFTER_PROBLEM_COMPLETION.md`, each completed problem's "interview
takeaway" qualitative field gets appended to the matching topic section below
(Follow-up variations seen / Edge-case checklists), keyed by the problem's
primary topic. This is the mechanism that keeps this file current — do not
let a section sit unedited just because no recent problem touched that topic.

---

## Arrays & Strings

### Interviewer expectations
- Discover the invariant before optimizing.
- State invariants explicitly.

### Communication patterns
- Separate local state (per-position/per-window) from global state
  (best-so-far) and say out loud which is which — a common confusion source
  in Kadane's/sliding-window-style problems.

### Follow-up variations seen
- (Kadane's / max-subarray family) Why is your greedy decision always safe?
- (Kadane's / max-subarray family) Can you prove your invariant?
- (Kadane's / max-subarray family) Can this be done in O(1) extra space?

### Edge-case checklists
- Empty input (if allowed)
- Single element
- All negative (Kadane's family: what happens on all-negative input?)
- All positive
- Duplicates
- Large constraints
- Overflow (if applicable)

---

## Trees & BSTs

### Interviewer expectations
<!-- grows per completion -->

### Communication patterns
<!-- grows per completion -->

### Follow-up variations seen
<!-- grows per completion -->

### Edge-case checklists
<!-- grows per completion -->

---

## Graphs

### Interviewer expectations
<!-- grows per completion -->

### Communication patterns
<!-- grows per completion -->

### Follow-up variations seen
<!-- grows per completion -->

### Edge-case checklists
<!-- grows per completion -->

---

## DP

### Interviewer expectations
<!-- grows per completion -->

### Communication patterns
<!-- grows per completion -->

### Follow-up variations seen
<!-- grows per completion -->

### Edge-case checklists
<!-- grows per completion -->

---

## Heaps & Design

### Interviewer expectations
- Min Stack (LC155): O(1) for every operation is the bar. Present the two-stack
  O(n)-space solution first, state the space cost aloud, then offer the O(1)
  auxiliary-space optimization.

### Communication patterns
- Derive the encode/decode formulas live rather than reciting them: a new
  minimum is stored as `2*newMin - prevMin`; a value below `getMin` is an
  encoded marker whose pop restores `prevMin = 2*currentMin - encoded`.

### Follow-up variations seen
- "Now do it in O(1) extra space." — the encoded single-stack Min Stack.

### Edge-case checklists
- Duplicate minima (the frequency-compression design must not desync).
- Integer overflow in the encoding arithmetic: every variable in `2*min-prev`
  must be widened (use `long`), not just the stack element type.

---

## General

### Interviewer expectations
- Never jump directly to the optimal algorithm; declare the brute-force
  baseline first.
- Explain correctness before efficiency.

### Communication patterns
<!-- grows per completion -->

### Follow-up variations seen
- What edge case breaks a naive implementation?
- How would you test this?

### Edge-case checklists
<!-- grows per completion -->
