You are auditing whether the DSA curriculum in this repo serves problems in
proper order of increasing cognitive load for interview preparation. Work in
/home/virendra/DSA/dsa_os. STRICTLY READ-ONLY on repo files; write scratch
scripts only under /tmp. Do not commit anything. Follow the steps exactly;
where a step says SIMULATE or COMPUTE, write and run a small python3 script —
do not estimate by reading JSON manually.

## Facts you must take as given (already verified — do not re-derive)

- Data: curriculum/curriculum.json (581 problems: id, title, difficulty
  Easy/Medium/Hard, stage, primary_skill, problem_role
  PRIMARY/REINFORCEMENT/CHALLENGE, lc_id), knowledge/skills.json (93 skills:
  skill_order, per-skill primary_validation_problem / reinforcement_problems /
  challenge_problems, stage), curriculum/stages.json (stage_order, 13 stages),
  curriculum/dependency_graph.json (problem_dependencies = the journey gating).
- The journey order is DEPENDENCY-DRIVEN: scripts/_shared.py
  select_next_problem serves only problems whose problem_dependencies are all
  completed, preferring current skill, then current stage, then earliest by
  file order. File order matters only as tie-break among unlocked problems.
- STRUCTURAL FACT: a CHALLENGE depends on only ONE reinforcement, so
  challenges unlock MID-skill (right after that one dep), not at the end.
  "It's a challenge so it comes last" is FALSE — always simulate.
- Simulation recipe (validated): maintain completed=set(); loop: candidates =
  problems with all deps in completed, not completed; prefer same skill as the
  previously served problem, then same stage, then lowest file index; serve,
  add to completed. This reproduces the real scheduler for a fresh learner.
- Quantitative baseline (already computed, trust it): stage mean difficulty
  weights (E=1,M=2,H=3) in stage order: Observation 1.92, State Construction
  1.73, Constraint Maintenance 1.96, Ordered Reasoning 1.97, Query Processing
  2.08, Decision Making 2.11, Recursive Thinking 1.80, State Transition 2.42
  (51 Hards), Graph Thinking 2.21, Interval Reasoning 2.15, Pattern Discovery
  2.27, Mathematical 1.57, Integration 2.19.
- Interview-readiness scope = first 9 stages (through Graph Thinking);
  stages 10-13 are post-readiness polish — issues there are at most Minor
  unless they create an entry wall.

## Stages 1-4: ALREADY AUDITED — merge these findings verbatim into your final report

Verdicts: Observation MISORDERED; State Construction MINOR; Constraint
Maintenance WELL-ORDERED; Ordered Reasoning MINOR.
Important issues (keep IDs/fixes exactly):
I1. CPX-003 First Missing Positive (LC41, Hard) served at journey position 3
    (deps=[CPX-002] only). Fix: add a Medium reinforcement to SK-OB-01 (e.g.
    LC442) and gate CPX-003 behind it.
I2. SK-OB-06 triple-Hard wall at positions 19-22 (OBS-023 LC214, OBS-024
    LC1392, OBS-030 LC1044) all dep only on Easy OBS-022; OBS-030 needs
    binary-search-on-answer taught in stage 4. Fix: dep OBS-030 <- BSR-003;
    insert a Medium before the KMP pair.
I3. OBS-027 (LC1671 Hard) mis-roled REINFORCEMENT, dep directly on Easy
    OBS-026, in a "Patience Sorting" skill with no LIS teaching problem.
    Fix: re-role CHALLENGE, add LC300 as the real reinforcement.
I4. SK-SC-03/SK-SC-04 inverted: Find the Duplicate (LC287, Floyd's advanced
    application) is served BEFORE Linked List Cycle (LC141, the intro).
    Fix: swap that skill dependency.
Minor issues: LNK-011(E)->LNK-012(H) file-order adjacency (not dep-forced);
OBS-021/OBS-025 both lc 28 in one skill; TWO-001 lc_id should be 167 not 1;
TWO-011 wrong-concept PRIMARY for parametric search (swap with BSR-012);
skill_order reversed within Ordered Reasoning (display-only).

## YOUR WORK

### Part A — stages 5-9 (Query Processing, Decision Making, Recursive
Thinking, State Transition, Graph Thinking): the readiness core

A1. SIMULATE the journey for these stages (assume all stage 1-4 problems
    completed at start). Print the first 12 served per stage with
    difficulty. Flag any Hard inside a stage's first 8 served.
A2. For every skill in these stages, list served order within the skill and
    flag adjacent Easy->Hard pairs; for each, check whether it is dep-forced
    (direct dependency) or file-order-only, and whether a Medium problem of
    the same skill would interleave.
A3. Role sanity: list every PRIMARY with difficulty Hard and every CHALLENGE
    with difficulty Easy in these stages. For each Hard PRIMARY, look at the
    skill's reinforcement list and name a specific easier problem to promote
    (use lc_id + your knowledge of the actual LeetCode problems). Known
    suspect: SK-RT-03 primary TRE-026 Serialize and Deserialize Binary Tree
    (LC297, Hard).
A4. Canon ladders — verify each ordering below holds in the SIMULATED order;
    report holds/broken with positions:
    - subsets/permutations/combination-sum BEFORE N-Queens (LC51) and
      Word Search II (LC212)
    - climbing stairs / house robber BEFORE coin change / knapsack BEFORE
      LCS/edit distance BEFORE interval DP (burst balloons LC312)
    - number of islands / flood fill BEFORE course schedule (topo) BEFORE
      Dijkstra/shortest paths BEFORE critical connections (LC1192)
    - binary tree traversals BEFORE BST operations BEFORE serialize (LC297)
      BEFORE hard tree DP (binary tree max path sum LC124, house robber III)
A5. Cross-stage direction: COMPUTE that no skill in an earlier stage depends
    on a skill in a later stage (skill_dependencies + stage indexes) — state
    the count of violations (expected 0).

### Part B — stages 10-13 (Interval Reasoning, Pattern Discovery,
Mathematical, Integration)

B1. Hard PRIMARY triage: RNG-001 (LC315), RNG-002 (LC327), RNG-013 (LC715)
    are Hard primaries. For each: name an easier canonical entry (e.g. LC307
    Range Sum Query Mutable for segment tree/BIT) from the skill's own lists
    if present, else recommend "add problem X as primary, demote current to
    challenge".
B2. Mathematical stage sits 12th with mean weight 1.57 (easiest of all).
    COMPUTE the transitive dependency count for its 5 easiest problems — are
    trivially-easy classics locked behind hundreds of problems? Verdict:
    acceptable dessert-course or should easy math move earlier?
B3. Integration capstone check: sample 8 problems by lc_id; does each truly
    combine >=2 earlier-stage concepts? Verdict: capstone or dumping ground.

### Part C — repo-wide mechanical sweeps (COMPUTE all of these)

C1. All PRIMARY problems with difficulty Hard (id, title, skill, stage).
C2. All CHALLENGE problems with difficulty Easy (same columns).
C3. Transitive-dep count distribution for all Easy problems; top 10 heaviest
    (id, title, stage, count). Are interview-classic Easies (LC125, LC88,
    LC169, LC252, LC120) reachable in a reasonable position?
C4. All adjacent Easy->Hard served pairs within skills, whole repo (merge
    with the stage 1-4 list above; dedupe).

### Output format (exactly this structure)

1. One-line overall verdict: WELL-ORDERED / MOSTLY-ORDERED WITH N FIXES /
   MISORDERED, plus one sentence of justification.
2. Table: stage | verdict | worst issue (all 13 stages; stages 1-4 from the
   merged findings above).
3. IMPORTANT issues, ranked, numbered continuing from I4 (I5, I6, ...): each
   with problem/skill IDs, evidence (journey positions, dep chains — from
   YOUR simulation output, cite the numbers), and a one-line concrete fix
   (re-role X / add dependency X<-Y / swap primary to X / move stage /
   fine-as-is).
4. MINOR issues, bulleted, same evidence discipline.
5. Appendix: raw outputs of C1-C4.

Rules: never propose deleting problems; never propose changing progress.json;
every claim about "position N" must come from your simulation printout, not
intuition; if simulation and intuition disagree, the simulation wins and say
so. If a step fails technically after 3 attempts, report the step as SKIPPED
with the error rather than guessing.
