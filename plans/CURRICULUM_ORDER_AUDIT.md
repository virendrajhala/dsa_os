# Curriculum Ordering Audit

Why the curriculum was resequenced. Implemented by
`plans/CURRICULUM_ORDER_FIX_PLAN.md` (Tasks 0–4); execution log in
`plans/CURRICULUM_ORDER_REPORT.md`.

Every number below was produced by simulating the real scheduler
(`_shared.select_next_problem`) over all 581 problems from a cold start —
none is estimated. The simulation is pinned as a test in
`scripts/test_curriculum_order.py`.

## Findings

| # | Defect | Evidence (simulated journey positions) |
|---|---|---|
| D1 | Backtracking sits outside the interview-readiness core | All backtracking classics (LC78/46/39/51/79/131) were in stage 11 "Pattern Discovery"; readiness scope was stages 1-9. Subsets served at **493**. The system could call a learner interview-ready having never written a backtracking template. |
| D2 | DP scheduled before Graph | **Zero** dependency edges either direction between the two stages; Graph's cross-stage prereqs all resolve to stages ≤7. DP contains LC847 (BFS+bitmask) served ~32 positions **before** the first graph BFS. |
| D3 | Hard problems unlock mid-skill | A CHALLENGE depends on only ONE reinforcement → *First Missing Positive* (Hard) at position **3**; triple-Hard KMP wall at 19-22; 11 straight Hards at 201-211. |
| D4 | Interval Reasoning teaches its tool last | `SK-IR-07` (Medium, teaches Fenwick/segment tree) **depended on** `SK-IR-04` (all-Hard, uses it). Edge was inverted. |
| D5 | Hard problems as skill entry points | 8 skills had a Hard `primary_validation_problem`. `SK-RT-03` was Hard-primary **and** Hard-only-reinforcement — no on-ramp at all. |

## Fixes applied

- **D1/D2** — `stage_order` resequenced in `curriculum/stages.json` and
  `curriculum/dependency_graph.json`: Pattern Discovery moves to slot 8
  (its whole dependency footprint, SK-PD-01..05, resolves to Recursive
  Thinking or earlier), and Graph Thinking now precedes State Transition.
  `readiness.stage_scope_count` widened 9 → 10 so DP stays in the core.
  `skill_order` in both files resequenced to match (it was stale from the
  pre-F18 sequence).
- **D3** — `_shared.challenge_stage_gate`: a CHALLENGE problem opens only
  once every PRIMARY/REINFORCEMENT problem of its own stage is complete.
  Expressed as one scheduler rule rather than ~4,700 materialized
  dependency entries; simulation confirms both forms produce an identical
  served order.
- **D4** — `SK-IR-04` ← `SK-IR-07` edge reversed in `skill_dependencies`.
- **D5** (two in-scope cases) — `SK-RT-03` takes LC105 (Construct Binary
  Tree from Preorder+Inorder, Medium — literal deserialization) as its
  primary, with LC297 demoted to a reinforcement that depends on it;
  `DP-083` (LC1522) relabelled Hard → Medium with `difficulty_weight`
  4 → 2, since LeetCode rates it Medium and the mislabel had made
  `SK-ST-17` an all-Hard skill.

## Measured impact (all 581 problems)

| Metric | Before | After |
|---|---|---|
| First Hard at journey position | 3 | **20** |
| Easy→Hard adjacencies | 7 | **3** |
| Hard PRIMARY skills | 8 | **6** |
| Backtracking inside readiness core | no | **yes** (Subsets 493 → **274**) |
| Problems served / unreachable | 581 / 0 | **581 / 0** |
| Forward-stage deps (skill + problem) | 0 | **0** |
| Graph cycles (skill + problem) | none | **none** |
| Stage contiguity in served order | 13/13 | **13/13** |

Difficulty curve per 50 problems, after:
`1.74 1.78 1.96 2.20 1.72 2.26 1.94 2.26 2.40 2.52 2.04 2.16` — rising, with
deliberate resets at each new paradigm (recursion, backtracking, graphs).

Canon ladders after the fix:

- LC105 Build Tree **262** → LC297 Serialize **263**
- Subsets **274** → Permutations **284** → Word Search **288** → N-Queens **299**
- Num Islands **315** → Course Schedule **326** → Dijkstra **344**
- Climbing Stairs **376** → Coin Change **383** → Burst Balloons **457**

## Deliberately deferred

Each is real but post-readiness or lower value; fixing them here would widen
the blast radius without changing interview outcomes.

- **Six remaining Hard-primary skills**: `SK-IR-04` (LC315), `SK-IR-05`
  (LC327), `SK-IR-10` (LC715), `SK-QP-06` (LC295 — genuinely the canonical
  two-heap problem, keep), `SK-ST-05` (LC354), `SK-IN-03` (LC1206). The
  Interval Reasoning three would need new problems (e.g. LC729 My Calendar I)
  to have a Medium entry; that is a curriculum addition, not a reorder.
- **Word Search II (LC212) served ~6 positions before Subsets.** Was 229
  positions early; the stage reorder reduces it to 6. Closing it fully needs
  either a forward-stage dependency (breaks a clean invariant) or re-skilling
  TRI-002 into `SK-PD-05`.
- **40 duplicate `lc_id` entries across 38 LeetCode problems**, some with
  inverted roles (LC327 is PRIMARY at one slot and CHALLENGE at another;
  LC307 is claimed as primary by two skills). Needs a per-pair decision from
  the owner, like the earlier F15 dedupe.
- **Bit manipulation buried.** LC136/191/338/190/268 have dependency depth
  ≤4 but are served at 538+ because Mathematical Thinking is stage 12. They
  are standard phone-screen material; moving `SK-MT-03` earlier is a
  reasonable follow-up.
- **`SK-GT-01` is deque/sliding-window material inside Graph Thinking**,
  giving that stage a non-graph opening. Moving it to Constraint Maintenance
  is a defensible follow-up.
- **`SK-IN-06`'s four Easy problems don't integrate two concepts** (LC703
  duplicates HEP-003). Relabel or relocate later.
- **[CLOSED] The D4 edge was reversed at skill level only.** `problem_dependencies` is
  generated from `skill_dependencies`, but the plan scoped the reversal to
  the skill edge; the derived problem edge `RNG-004 → RNG-001` still encodes
  the old direction, so LC307 continued to be served after LC315. Fixed
  surgically (the RNG-001/RNG-004 pair only — 11 of the 13 edges a wholesale
  regeneration would touch are deliberate CHALLENGE anchors) and pinned by
  `test_problem_deps_never_contradict_the_skill_dag`. LC307 now serves at 499,
  LC315 at 501.
