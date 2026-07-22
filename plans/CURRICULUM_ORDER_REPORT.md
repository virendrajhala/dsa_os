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
- Task 3: `712b89c` — as planned. Deviation of scope, noted not acted on:
  the plan scoped the D4 reversal to `skill_dependencies` only. Because
  `problem_dependencies` is generated from the skill DAG, the derived edge
  `RNG-004 → RNG-001` still encodes the old direction, so LC307 is still
  served after LC315. Following the plan's stated file/field scope rather
  than widening it; recorded as a follow-up in the audit.
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
| Easy→Hard adjacencies | 3 | 3 | ✅ |
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
