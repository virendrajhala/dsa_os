# Curriculum Ordering Fix — Execution Report

Implements `plans/CURRICULUM_ORDER_FIX_PLAN.md` (Tasks 0–4).

## Baseline (measured on the pre-fix repo)

| Metric | Baseline |
|---|---|
| first Hard at journey position | 3 |
| Easy→Hard adjacencies | 7 |
| Hard PRIMARY skills | 8 |
| Subsets (LC78) journey position | 493 |
| served / unreachable | 581 / 0 |
| forward-stage deps (skill + problem) | 0 / 0 |
| cycles (skill + problem) | none |
| stages contiguous in served order | 13 / 13 |

Baseline gates before any edit: `make test` green, `make validate` green
(581 problems / 93 skills), tree clean apart from the owner's untracked
files, no other agent in `git log`.

## Task log

- Plan doc: `ec5d401` — as planned.
- Task 0: `a092524` — deviation: the plan predicted four expectedFailure
  markers; the harness run produced exactly **two**
  (`test_entry_ramp_has_no_hard_in_first_fifteen`,
  `test_backtracking_is_inside_the_readiness_scope`).
  `test_backtracking_ladder_order` and
  `test_tree_ladder_builds_before_serialize` already pass on the pre-fix
  repo (LC105 at 245 < LC297 at 248), so marking them would have produced
  "unexpected success" failures. Commit body reworded four→two to match.
  Consequence: Task 3 has no marker to remove; it must instead keep the
  tree-ladder test green. Verified: it does (LC105 262 < LC297 263).
- Task 1: `2fa5e82` — as planned.
- Task 2: `80f0048` — as planned. Zero expectedFailure markers remain from
  this commit onward (one task earlier than the plan predicted, since only
  two markers ever existed).
- Task 3: `712b89c` — as planned. Deviation of scope at the time: the plan
  scoped the D4 reversal to `skill_dependencies` only, so the derived edge
  `RNG-004 → RNG-001` still encoded the old direction and LC307 was still
  served after LC315. **Closed in the follow-up commit below.**
- Task 4: this commit — as planned, plus three stale facts in
  `curriculum/dsa-skill-map.md` corrected because Task 3 invalidated them
  (SK-RT-03 primary TRE-026 → TRE-028 with 2 reinforcements, SK-RT-02 16 →
  15 reinforcements, difficulty totals 336 Medium / 146 Hard → 337 / 145).
  README needed no change: it enumerates neither the stage sequence nor the
  readiness scope count.

## Stop conditions

None triggered. No fix step needed more than one attempt.

## Final acceptance table (actual vs required)

| Metric | Required | Actual | |
|---|---|---|---|
| first Hard at journey position | 20 | 20 | ✅ |
| Easy→Hard adjacencies | 3 | 2 | ✅ (improved by the D4 follow-up) |
| Hard PRIMARY skills | 6 | 6 | ✅ |
| Subsets (LC78) journey position | 274 | 274 | ✅ |
| served / unreachable | 581 / 0 | 581 / 0 | ✅ |
| forward-stage deps (skill + problem) | 0 | 0 / 0 | ✅ |
| cycles (skill + problem) | none | none | ✅ |
| stages contiguous in served order | 13 / 13 | 13 / 13 | ✅ |
| expectedFailure markers | 0 | 0 | ✅ |

Canon ladders (journey position): LC105 262 < LC297 263 ✅ · LC78 274 <
LC46 284 < LC79 288 < LC51 299 ✅ · LC200 315 < LC207 326 < LC743 344 ✅ ·
LC70 376 < LC322 383 < LC312 457 ✅

Difficulty curve per 50 reproduces the plan header exactly:
`1.74 1.78 1.96 2.20 1.72 2.26 1.94 2.26 2.40 2.52 2.04 2.16`

## Follow-up: D4 closed at the problem layer

Independent review confirmed every number above and flagged that D4 was only
half-delivered: `skill_dependencies` had been reversed (SK-IR-04 now requires
SK-IR-07) but `problem_dependencies` still carried `RNG-004 ← RNG-001`, so the
learner still met the Hard application (LC315, Count of Smaller Numbers After
Self) before the Medium that teaches the tool (LC307, Range Sum Query —
Mutable). Confirmed in the simulation: RNG-001 at 499, RNG-004 at 503.

**Scope decision.** The audit recommended "regenerate `problem_dependencies`
from the skill DAG". Dry-running that against the file's own documented
generation rule produced 13 differing keys, but 11 of them are CHALLENGE and
REINFORCEMENT anchors where the file deliberately names a *later*
reinforcement than a naive "first reinforcement" reading (e.g. HEP-014..019 →
HEP-020 rather than HEP-016, BSR-007 → BSR-006 rather than BSR-004). Those are
choices, not defects. Wholesale regeneration would have rewritten 11
intentional edges to fix one real inversion, so the fix is surgical:

- `RNG-004` (PRIMARY of SK-IR-07) drops `RNG-001` and takes `PFX-002`, the
  primary of its own prerequisite skill.
- `RNG-001` (PRIMARY of SK-IR-04) gains `RNG-004`, matching the reversed skill
  edge.

**Pinned, not just fixed.** `test_problem_deps_never_contradict_the_skill_dag`
now asserts the general invariant: no problem edge may require a problem whose
skill sits downstream of it in the transitive skill DAG. It failed on exactly
this one edge before the fix and passes after, so the whole class of defect is
guarded rather than this instance patched.

Also in this follow-up:
- **Dead `stage_order` mirror removed** from `dependency_graph.json`. It was
  byte-identical to `stages.json`, had no validator check of its own (only
  `skill_order` is checked, `validate_curriculum.py:352-367`) and no reader
  anywhere in `scripts/` — a field that could silently drift with nothing
  depending on it. Deleted rather than guarded.
- **Dead `DW` constant removed** from `test_curriculum_order.py`. Unused, and
  its `Hard: 3` contradicted the repo convention pinned at
  `validate_curriculum.py:554` (`Hard: 4`).
- **`is_problem_unlocked` now has direct unit tests** (9 cases in
  `test_shared.py`). It previously appeared nowhere outside `_shared.py` in any
  arity, despite the new challenge gate routing through it and guarding the
  entire ordering guarantee. Cases cover deps met/unmet, absent key, malformed
  and non-string dependency entries, gate veto, gate omitted, and that the gate
  is a veto and never an override.

### Re-derived acceptance (after the follow-up)

| Metric | Required | Actual | |
|---|---|---|---|
| first Hard at journey position | 20 | 20 | ✅ |
| Easy→Hard adjacencies | 3 | 2 | ✅ improved |
| Hard PRIMARY skills | 6 | 6 | ✅ |
| Subsets (LC78) journey position | 274 | 274 | ✅ |
| served / unreachable | 581 / 0 | 581 / 0 | ✅ |
| LC307 before LC315 (D4) | required | 499 < 501 | ✅ newly true |

Ladders unchanged: LC105 262 < LC297 263 · LC78 274 < LC46 284 < LC79 288 <
LC51 299 < LC743 344 · LC70 376 < LC322 383 < LC312 457.
`make test` 182 tests green (was 172), `make validate` green.

### Still open
- **Resume path, `_shared.py:1280`.** The active problem is re-checked through
  `is_problem_unlocked` *with* the challenge gate, so a CHALLENGE in progress
  can be refused on resume. Analysis: the gate is monotonic — it tests
  `fundamentals(stage) ⊆ completed_ids` and `completed_ids` only grows — so a
  problem that once passed cannot later fail. The reachable case is therefore
  narrow: a `current_problem` pointing at a CHALLENGE that was recorded
  *before* the gate existed, or set outside `update_progress.py`. Not
  triggered by the live file (current problem is a REINFORCEMENT). Left for
  the owner to decide: exempt the active problem from the gate, or accept it.
