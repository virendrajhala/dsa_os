# Curriculum Ordering Fix Plan

> **For agentic workers:** implement task-by-task, in order. Steps use
> checkbox (`- [ ]`) syntax. Every task ends green (`make test && make
> validate`) and gets exactly one commit.
>
> Source audit: `plans/CURRICULUM_ORDER_AUDIT.md` findings, summarized in
> §"Audit basis" below. Every number in this plan was produced by
> simulating the real scheduler over all 581 problems — not estimated.

**Goal:** Fix the three ordering defects that make the curriculum serve
problems out of cognitive order for interview preparation, without deleting
a single problem or touching `progress/progress.json`.

**Architecture:** Three of the four fixes are pure data/config edits
(`stages.json`, `dependency_graph.json`, `skills.json`, `curriculum.json`,
`scoring.json`). One is a single scheduler rule in `_shared.py`. No problem
content changes; no stage renames (so `progress.json` history stays valid).

**Tech stack:** Python 3 stdlib only, unittest via `make test`.

## Audit basis (what's broken, and why these fixes)

| # | Defect | Evidence (simulated journey positions) |
|---|---|---|
| D1 | Backtracking sits outside the interview-readiness core | All backtracking classics (LC78/46/39/51/79/131) are in stage 11 "Pattern Discovery"; readiness scope is stages 1-9. Subsets served at **493**. |
| D2 | DP scheduled before Graph | **Zero** dependency edges either direction between the two stages; Graph's cross-stage prereqs all resolve to stages ≤7. DP contains LC847 (BFS+bitmask) served ~32 positions **before** the first graph BFS. |
| D3 | Hard problems unlock mid-skill | A CHALLENGE depends on only ONE reinforcement → *First Missing Positive* (Hard) at position **3**; triple-Hard KMP wall at 19-22; 11 straight Hards at 201-211. |
| D4 | Interval Reasoning teaches its tool last | `SK-IR-07` (Medium, teaches Fenwick/segment tree) **depends on** `SK-IR-04` (all-Hard, uses it). Edge is inverted. |
| D5 | Hard problems as skill entry points | 8 skills have a Hard `primary_validation_problem`. `SK-RT-03` is Hard-primary **and** Hard-only-reinforcement — no on-ramp at all. |

## Verified impact of this plan (simulation, all 581 problems)

| Metric | Before | After | Note |
|---|---|---|---|
| First Hard at journey position | 3 | **20** | end of Observation, as a challenge tail |
| Easy→Hard adjacencies | 7 | **3** | remaining 3 are dep-forced and pedagogically fine |
| Hard PRIMARY skills | 8 | **6** | two fixed here; four are post-readiness, deferred |
| Backtracking inside readiness core | no | **yes** | Subsets 493 → **274** |
| Problems served / unreachable | 581 / 0 | **581 / 0** | no regression |
| Easy problems over 30-dep cap | 0 | **0** | validator rule holds |
| Forward-stage deps (skill + problem) | 0 | **0** | invariant preserved |
| Graph cycles (skill + problem) | none | **none** | invariant preserved |
| Stage contiguity in served order | 13/13 | **13/13** | invariant preserved |

Difficulty curve per 50 problems, after:
`1.74 1.78 1.96 2.20 1.72 2.26 1.94 2.26 2.40 2.52 2.04 2.16` — rising, with
deliberate resets at each new paradigm (recursion, backtracking, graphs).

Canon ladders after the fix (all correct):
- LC105 Build Tree **262** → LC297 Serialize **263**
- Subsets **274** → Permutations **284** → Word Search **288** → N-Queens **299**
- Num Islands **315** → Course Schedule **326** → Dijkstra **344**
- Climbing Stairs **376** → Coin Change **383** → Burst Balloons **457**

## Global Constraints (repo owner's rules — non-negotiable)

- Commits directly on `main`, ONE commit per task, conventional format
  `type/scope: lowercase imperative subject ≤72 chars` + concise body via
  HEREDOC. NO Co-Authored-By / AI attribution anywhere. Do NOT push.
- **`progress/progress.json` must be byte-identical after every task**
  (`git diff --quiet -- progress/progress.json`). No stage is renamed by
  this plan precisely so recorded history stays valid.
- Never stage `GAPS_ANALYSIS.md`, `FIXES_PROPOSAL.md`, `__pycache__/`, or
  scratch files. Stage files explicitly by name.
- Python stdlib only. TDD: write the failing test first for every behavior
  change.
- After EVERY task: `make test && make validate` must pass before commit.
- `stage_order` exists in BOTH `curriculum/stages.json` and
  `curriculum/dependency_graph.json` and the validator requires them
  identical. `skill_order` exists in BOTH `knowledge/skills.json` and
  `curriculum/dependency_graph.json` and must also stay identical.
- Do not delete problems. Do not rename stages. Do not edit problem
  `title`, `lc_id`, or `url` fields except where a task says so explicitly.

---

### Task 0: Ordering-invariant harness (do this first — it proves the rest)

**Files:**
- Create: `scripts/test_curriculum_order.py`
- Modify: `Makefile` (add to the `test` target)

**Interfaces:**
- Produces: `simulate_journey(state) -> list[str]` test helper reproducing
  `select_next_problem`'s served order, plus invariant tests every later
  task re-runs. Later tasks rely on these tests failing/passing to prove
  their effect.

- [ ] **Step 1: Write the harness tests.** Create
  `scripts/test_curriculum_order.py`:

```python
#!/usr/bin/env python3
"""Curriculum ORDERING invariants (cognitive-load progression).

These pin the properties an interview-prep curriculum must have:
reachability, stage monotonicity, a gentle entry ramp, and canon ladders.
They read the repo's curriculum files; they never touch progress.json.
"""
from __future__ import annotations

import unittest

import _shared
from _shared import load_json_file

DW = {"Easy": 1, "Medium": 2, "Hard": 3}


def _load():
    curriculum = load_json_file(_shared.CURRICULUM_PATH)
    skills = load_json_file(_shared.SKILLS_PATH)
    stages = load_json_file(_shared.STAGES_PATH)
    graph = load_json_file(_shared.GRAPH_PATH)
    return curriculum, skills, stages, graph


def simulate_journey():
    """Reproduce select_next_problem's served order for a fresh learner:
    only dependency-complete problems are servable; prefer the current
    skill, then the current stage, then earliest curriculum order."""
    curriculum, skills, stages, graph = _load()
    problems = curriculum["problems"]
    by_id = {p["id"]: p for p in problems}
    file_index = {p["id"]: i for i, p in enumerate(problems)}
    stage_index = {s: i for i, s in enumerate(stages["stage_order"])}
    deps = graph["problem_dependencies"]
    role_gate = _shared.challenge_stage_gate(curriculum)

    completed: set[str] = set()
    served: list[str] = []
    skill = None
    stage = stages["stage_order"][0]
    ids = [p["id"] for p in problems]
    while len(served) < len(problems):
        ready = [
            i for i in ids
            if i not in completed
            and all(d in completed for d in (deps.get(i) or []))
            and role_gate(by_id[i], completed)
        ]
        if not ready:
            break
        def key(i):
            p = by_id[i]
            return (
                0 if p["primary_skill"] == skill else 1,
                0 if p["stage"] == stage else 1,
                stage_index[p["stage"]],
                file_index[i],
            )
        chosen = min(ready, key=key)
        served.append(chosen)
        completed.add(chosen)
        skill = by_id[chosen]["primary_skill"]
        stage = by_id[chosen]["stage"]
    return served, by_id, stage_index


class JourneyInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.served, cls.by_id, cls.stage_index = simulate_journey()
        cls.pos = {pid: n for n, pid in enumerate(cls.served, 1)}

    def test_every_problem_is_reachable(self):
        total = len(load_json_file(_shared.CURRICULUM_PATH)["problems"])
        self.assertEqual(len(self.served), total)

    def test_stages_are_contiguous_in_served_order(self):
        spans = {}
        for n, pid in enumerate(self.served, 1):
            spans.setdefault(self.by_id[pid]["stage"], []).append(n)
        for stage, positions in spans.items():
            expected = max(positions) - min(positions) + 1
            self.assertEqual(expected, len(positions), f"{stage} is interleaved")

    def test_entry_ramp_has_no_hard_in_first_fifteen(self):
        early = [p for p in self.served[:15] if self.by_id[p]["difficulty"] == "Hard"]
        self.assertEqual(early, [], f"Hard problems too early: {early}")

    def test_no_forward_stage_dependencies(self):
        graph = load_json_file(_shared.GRAPH_PATH)
        bad = [
            (pid, dep)
            for pid, dep_list in graph["problem_dependencies"].items()
            for dep in (dep_list or [])
            if self.stage_index[self.by_id[dep]["stage"]]
            > self.stage_index[self.by_id[pid]["stage"]]
        ]
        self.assertEqual(bad, [])

    def _pos_of_lc(self, lc_id):
        hits = [p for p in self.by_id.values() if p.get("lc_id") == lc_id]
        self.assertTrue(hits, f"LC{lc_id} missing from curriculum")
        return min(self.pos[p["id"]] for p in hits)

    def test_backtracking_ladder_order(self):
        subsets = self._pos_of_lc(78)
        permutations = self._pos_of_lc(46)
        n_queens = self._pos_of_lc(51)
        self.assertLess(subsets, permutations)
        self.assertLess(permutations, n_queens)

    def test_graph_ladder_order(self):
        islands = self._pos_of_lc(200)
        course_schedule = self._pos_of_lc(207)
        dijkstra = self._pos_of_lc(743)
        self.assertLess(islands, course_schedule)
        self.assertLess(course_schedule, dijkstra)

    def test_dp_ladder_order(self):
        stairs = self._pos_of_lc(70)
        coin_change = self._pos_of_lc(322)
        burst_balloons = self._pos_of_lc(312)
        self.assertLess(stairs, coin_change)
        self.assertLess(coin_change, burst_balloons)

    def test_tree_ladder_builds_before_serialize(self):
        self.assertLess(self._pos_of_lc(105), self._pos_of_lc(297))

    def test_backtracking_is_inside_the_readiness_scope(self):
        stages = load_json_file(_shared.STAGES_PATH)
        scoring = load_json_file(_shared.SCORING_PATH)
        scope_count = scoring["readiness"]["stage_scope_count"]
        scope = set(stages["stage_order"][:scope_count])
        subsets = [p for p in self.by_id.values() if p.get("lc_id") == 78][0]
        self.assertIn(subsets["stage"], scope)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Add the gate helper stub** so the harness imports. In
  `scripts/_shared.py`, add (Task 2 gives it real behavior):

```python
def challenge_stage_gate(curriculum: JsonDict):
    """Return `is_unlocked(problem, completed_ids)` for the challenge rule.

    Placeholder until the stage-fundamentals gate lands (see the curriculum
    ordering fix plan, Task 2); currently allows everything. The signature
    mirrors `is_problem_unlocked`: it takes the problem DICT, not its id.
    """

    def is_unlocked(problem: JsonDict, completed_ids: set[str]) -> bool:
        return True

    return is_unlocked
```

- [ ] **Step 3: Run — expect FAILURES.** `python3 scripts/test_curriculum_order.py`
  Expected failures (these are exactly D1-D3): `test_entry_ramp_has_no_hard_in_first_fifteen`
  (CPX-003 at position 3), `test_backtracking_ladder_order` (passes today
  — the ladder itself is fine), `test_tree_ladder_builds_before_serialize`
  (LC297 before LC105), `test_backtracking_is_inside_the_readiness_scope`
  (Pattern Discovery is stage 11, scope is 9).
  Record which failed — later tasks flip them one by one.

- [ ] **Step 4: Wire into `make test`.** Add
  `python3 scripts/test_curriculum_order.py` to the `test` target,
  matching existing lines. Run `make test` — the new suite fails; that is
  expected and is the point. **Do not commit a red `make test`:** mark the
  four known-failing tests with `@unittest.expectedFailure` and a comment
  naming the task that removes the marker.

- [ ] **Step 5: Commit**

```bash
git add scripts/test_curriculum_order.py scripts/_shared.py Makefile
git commit -m "$(cat <<'EOF'
test/curriculum: pin cognitive-order invariants for the learner journey

simulates select_next_problem over all 581 problems and asserts the
properties interview prep needs: reachability, stage contiguity, a hard-free
entry ramp, canon ladders (backtracking, graph, dp, tree) and backtracking
inside the readiness scope. four assertions are expectedFailure today and
are the specification for the ordering fixes that follow.
EOF
)"
```

---

### Task 1: Move Pattern Discovery into the readiness core; Graph before DP

Fixes **D1** and **D2**. Pattern Discovery's entire dependency footprint
(SK-PD-01..05) resolves to Recursive Thinking or earlier — verified — so the
stage moves wholesale with no problem re-stamping and no skill surgery.

**Files:**
- Modify: `curriculum/stages.json` (`stage_order`)
- Modify: `curriculum/dependency_graph.json` (`stage_order`, `skill_order`)
- Modify: `knowledge/skills.json` (`skill_order`)
- Modify: `progress/scoring.json` (`readiness.stage_scope_count`)
- Modify: `scripts/test_curriculum_order.py` (drop two expectedFailure markers)

- [ ] **Step 1: Reorder `stage_order`** in `curriculum/stages.json` to
  exactly this sequence (the only change is Pattern Discovery moving to
  slot 8 and State Transition moving after Graph Thinking):

```json
"stage_order": [
  "Observation",
  "State Construction",
  "Constraint Maintenance",
  "Ordered Reasoning",
  "Query Processing",
  "Decision Making",
  "Recursive Thinking",
  "Pattern Discovery",
  "Graph Thinking",
  "State Transition",
  "Interval Reasoning",
  "Mathematical Thinking",
  "Integration"
]
```

- [ ] **Step 2: Mirror it** into `curriculum/dependency_graph.json`'s
  `stage_order` — byte-identical list (the validator compares them).

- [ ] **Step 3: Resequence `skill_order`** in `knowledge/skills.json` so
  skills are grouped in the NEW stage order. `skill_order` is currently
  stale from the pre-F18 sequence (it lists Query Processing 10th and
  Interval Reasoning 6th). Rebuild it with this script, then paste the
  result in:

```bash
python3 - <<'EOF'
import json
skills = json.load(open('knowledge/skills.json'))
stages = json.load(open('curriculum/stages.json'))
by_stage = {s: [] for s in stages['stage_order']}
for skill_id in skills['skill_order']:
    by_stage[skills['skills'][skill_id]['stage']].append(skill_id)
ordered = [sid for stage in stages['stage_order'] for sid in by_stage[stage]]
assert sorted(ordered) == sorted(skills['skill_order']), "skill set changed"
print(json.dumps(ordered, indent=2))
EOF
```

  Within a stage, keep the existing relative order. Mirror the identical
  list into `curriculum/dependency_graph.json`'s `skill_order`.

- [ ] **Step 4: Widen the readiness scope** in `progress/scoring.json`:
  `"stage_scope_count": 9` → `"stage_scope_count": 10`. Rationale: the core
  now ends at State Transition, so readiness covers recursion, backtracking,
  graphs AND dynamic programming — the full interview-relevant set. The
  validator allows 1..13; `_shared.compute_readiness` reads it, no code
  change needed.

- [ ] **Step 5: Remove one expectedFailure marker** — from
  `test_backtracking_is_inside_the_readiness_scope` only. The entry-ramp
  marker is removed by Task 2 and the tree-ladder marker by Task 3; leave
  both in place here.

- [ ] **Step 6: Verify**

```bash
make validate            # must pass: stage_order mirrored, skill_order mirrored
python3 scripts/test_curriculum_order.py   # readiness-scope test now passes
make test
python3 scripts/next_problem.py            # exit 0, sane recommendation
git diff --quiet -- progress/progress.json && echo "progress untouched"
```

  Then confirm the reordering worked as designed:

```bash
python3 - <<'EOF'
import json
stages = json.load(open('curriculum/stages.json'))
scoring = json.load(open('progress/scoring.json'))
order = stages['stage_order']
print("stage 8 :", order[7])   # expect Pattern Discovery
print("stage 9 :", order[8])   # expect Graph Thinking
print("stage 10:", order[9])   # expect State Transition
print("scope   :", order[:scoring['readiness']['stage_scope_count']])
EOF
```

- [ ] **Step 7: Commit**

```bash
git add curriculum/stages.json curriculum/dependency_graph.json knowledge/skills.json progress/scoring.json scripts/test_curriculum_order.py
git commit -m "$(cat <<'EOF'
fix/curriculum: put backtracking in the core and graphs before dp

pattern discovery (all backtracking: subsets, permutations, n-queens, word
search) sat at stage 11, outside the 9-stage readiness scope — the system
could call a learner interview-ready having never written a backtracking
template. its whole dependency footprint resolves to recursive thinking or
earlier, so the stage moves to slot 8 wholesale.

graph thinking now precedes state transition: the two stages share zero
dependency edges in either direction, graph is the easier stage (2.21 vs
2.42 with 51 hards) and appears in more interview loops, and dp contains
lc847 shortest-path-visiting-all-nodes which needs bfs. readiness scope
widened to 10 stages so dp stays inside the core. skill_order in both files
resequenced to the new stage order (it was stale from the pre-f18 sequence).
EOF
)"
```

---

### Task 2: Gate challenges behind their stage's fundamentals

Fixes **D3**. A CHALLENGE currently depends on ONE reinforcement, so hard
challenges unlock mid-skill. Implemented as a scheduler rule rather than
materialized dependencies: gating 117 challenges against their stage
fundamentals would add roughly 4,700 dependency entries to
`dependency_graph.json`. The rule expresses the same semantics in one place.
Simulation confirms both forms produce an identical served order.

**Files:**
- Modify: `scripts/_shared.py` (`challenge_stage_gate`, `is_problem_unlocked`)
- Modify: `scripts/test_shared.py` (rule tests)
- Modify: `scripts/test_curriculum_order.py` (drop entry-ramp marker)

- [ ] **Step 1: Write failing tests** in `scripts/test_shared.py`:

```python
class ChallengeStageGateTests(unittest.TestCase):
    """A CHALLENGE problem must wait for its stage's fundamentals (every
    PRIMARY/REINFORCEMENT problem of that stage), not just the single
    reinforcement it names as a dependency."""

    CURRICULUM = {
        "problems": [
            {"id": "A-1", "stage": "S1", "problem_role": "PRIMARY"},
            {"id": "A-2", "stage": "S1", "problem_role": "REINFORCEMENT"},
            {"id": "A-3", "stage": "S1", "problem_role": "CHALLENGE"},
            {"id": "B-1", "stage": "S2", "problem_role": "PRIMARY"},
        ]
    }

    def _gate_and(self, problem_id):
        gate = _shared.challenge_stage_gate(self.CURRICULUM)
        problem = next(p for p in self.CURRICULUM["problems"] if p["id"] == problem_id)
        return gate, problem

    def test_challenge_locked_until_stage_fundamentals_complete(self):
        gate, challenge = self._gate_and("A-3")
        self.assertFalse(gate(challenge, {"A-1"}))
        self.assertTrue(gate(challenge, {"A-1", "A-2"}))

    def test_non_challenge_never_gated_by_the_rule(self):
        gate, reinforcement = self._gate_and("A-2")
        self.assertTrue(gate(reinforcement, set()))
        gate, other_stage = self._gate_and("B-1")
        self.assertTrue(gate(other_stage, set()))

    def test_other_stage_fundamentals_are_irrelevant(self):
        gate, challenge = self._gate_and("A-3")
        # B-1 (stage S2) is still incomplete and must not block an S1 challenge.
        self.assertTrue(gate(challenge, {"A-1", "A-2"}))
```

- [ ] **Step 2: Run — expect FAIL** (`gate` currently returns True always):
  `python3 scripts/test_shared.py -k ChallengeStageGate`

- [ ] **Step 3: Implement** — replace the Task-0 stub in `scripts/_shared.py`:

```python
def challenge_stage_gate(curriculum: JsonDict):
    """Return `is_unlocked(problem_id, completed)` enforcing the challenge
    rule: a CHALLENGE problem opens only once every PRIMARY/REINFORCEMENT
    problem of its own stage is complete.

    Rationale: challenges name a single reinforcement as their dependency,
    so without this rule a stage's hardest problems unlock immediately after
    one easy problem — putting Hard problems in the learner's first handful
    of solves. Skill-level dependencies stay as they are; this only defers
    the challenge tail to the end of its stage.
    """

    problems = ensure_list(curriculum.get("problems"), "curriculum.problems")
    fundamentals: dict[str, set[str]] = {}
    for problem in problems:
        if not isinstance(problem, dict) or not isinstance(problem.get("id"), str):
            continue
        stage = problem.get("stage")
        fundamentals.setdefault(stage, set())
        if problem.get("problem_role") != "CHALLENGE":
            fundamentals[stage].add(problem["id"])

    def is_unlocked(problem: JsonDict, completed_ids: set[str]) -> bool:
        if problem.get("problem_role") != "CHALLENGE":
            return True
        return fundamentals.get(problem.get("stage"), set()) <= completed_ids

    return is_unlocked
```

  `_shared.py` imports nothing from `collections` today — keep it that way
  (hence `setdefault` rather than `defaultdict`).

  Then wire it into the scheduler. `is_problem_unlocked` currently reads:

```python
def is_problem_unlocked(problem: JsonDict, completed_ids: set[str], problem_deps: dict[str, list[str]]) -> bool:
```

  Add an optional fourth parameter so existing callers keep working:

```python
def is_problem_unlocked(
    problem: JsonDict,
    completed_ids: set[str],
    problem_deps: dict[str, list[str]],
    challenge_gate=None,
) -> bool:
    """Return whether a curriculum problem is unlocked for first-pass solving."""

    dependencies = problem_deps.get(problem["id"], [])
    if not isinstance(dependencies, list):
        return False
    if challenge_gate is not None and not challenge_gate(problem, completed_ids):
        return False
    return all(isinstance(dep, str) and dep in completed_ids for dep in dependencies)
```

  In `select_next_problem`, build the gate next to the existing
  `problem_deps = problem_dependencies_map(state.graph)` line and pass it to
  **both** `is_problem_unlocked` call sites (there are exactly two — locate
  them by content; at the time of writing they are the `incomplete_unlocked`
  comprehension and the `active_problem` check):

```python
    problem_deps = problem_dependencies_map(state.graph)
    challenge_gate = challenge_stage_gate(state.curriculum)
```

- [ ] **Step 4: Run tests** — `python3 scripts/test_shared.py` all pass.

- [ ] **Step 5: Remove the expectedFailure marker** from
  `test_entry_ramp_has_no_hard_in_first_fifteen`, and update the harness's
  `simulate_journey` if the gate signature changed.

- [ ] **Step 6: Verify the measured effect**

```bash
python3 scripts/test_curriculum_order.py   # entry-ramp test now passes
make test && make validate
python3 scripts/next_problem.py
git diff --quiet -- progress/progress.json && echo "progress untouched"
```

  Expected, from simulation: first Hard moves from position 3 to **20**;
  Easy→Hard adjacencies fall from 7 to **3**; all 581 still reachable.

- [ ] **Step 7: Commit**

```bash
git add scripts/_shared.py scripts/test_shared.py scripts/test_curriculum_order.py
git commit -m "$(cat <<'EOF'
fix/scheduler: hold challenge problems until their stage is learned

a challenge names one reinforcement as its dependency, so the hardest
problems of a stage unlocked immediately after a single easy solve: first
missing positive (hard) was the third problem served, and three kmp/rolling
hash hards landed at positions 19-22. challenges now open only once every
primary and reinforcement problem of their own stage is complete. first hard
moves to position 20 and easy->hard jumps drop from 7 to 3, with all 581
problems still reachable. expressed as a scheduler rule rather than ~4700
materialized dependency entries; semantics are identical.
EOF
)"
```

---

### Task 3: Fix inverted prerequisite and the two worst Hard entry points

Fixes **D4** and the two in-scope cases of **D5**.

**Files:**
- Modify: `curriculum/dependency_graph.json` (`skill_dependencies`,
  `problem_dependencies`)
- Modify: `knowledge/skills.json` (SK-RT-02, SK-RT-03 problem lists)
- Modify: `curriculum/curriculum.json` (TRE-026, TRE-028, DP-083)
- Modify: `scripts/test_curriculum_order.py` (drop tree-ladder marker)

- [ ] **Step 1: Reverse the Interval Reasoning edge.** In
  `dependency_graph.json.skill_dependencies`, `SK-IR-07` ("Fenwick Tree /
  Segment Tree", Medium primary LC307) currently depends on `SK-IR-04`
  (all-Hard, *uses* a Fenwick tree). Swap the direction:

```json
"SK-IR-04": ["SK-IR-07", "SK-QP-01", "SK-OR-04"],
"SK-IR-07": ["SK-QP-01", "SK-RT-02"]
```

  Leave `SK-IR-05` (`["SK-IR-04", "SK-QP-01"]`) and `SK-IR-10`
  (`["SK-IR-07", "SK-IR-08"]`) untouched — they inherit the correct order.
  Verify no cycle is introduced (Step 6 checks this).

- [ ] **Step 2: Give SK-RT-03 a Medium entry problem.** The skill
  ("Tree Serialization") is Hard-primary (TRE-026, LC297) with a Hard-only
  reinforcement (TRE-027, LC428) — no on-ramp. TRE-028 (LC105, Construct
  Binary Tree from Preorder+Inorder, Medium) is literal deserialization and
  currently sits as one of SK-RT-02's sixteen reinforcements.

  In `knowledge/skills.json`:
  - `SK-RT-02.reinforcement_problems`: remove `"TRE-028"` (15 remain — the
    validator's ≥1 rule still holds).
  - `SK-RT-03.primary_validation_problem`: `"TRE-026"` → `"TRE-028"`.
  - `SK-RT-03.reinforcement_problems`: `["TRE-027"]` → `["TRE-026", "TRE-027"]`.

  In `curriculum/curriculum.json`:
  - `TRE-028`: `primary_skill` → `"SK-RT-03"`, `problem_role` → `"PRIMARY"`.
    (Its `stage` stays `"Recursive Thinking"` — both skills are in that
    stage, so the stage/skill-stage invariant holds.)
  - `TRE-026`: `problem_role` → `"REINFORCEMENT"`.

  In `dependency_graph.json.problem_dependencies`, add `"TRE-028"` to
  `TRE-026`'s dependency list so serialization follows construction.

- [ ] **Step 3: Correct the DP-083 difficulty label.** `DP-083` is LC1522
  (Diameter of N-Ary Tree), which is **Medium** on LeetCode, not Hard. The
  mislabel makes `SK-ST-17` a 10-problem all-Hard skill with a Hard primary.
  In `curriculum/curriculum.json` set `DP-083.difficulty` to `"Medium"` **and**
  `DP-083.difficulty_weight` from `4` to `2` — the two fields are stored
  separately and the repo's convention is Easy=1, Medium=2, Hard=4 (verified
  across all 581 problems; leaving the weight at 4 would silently keep the
  problem scored as Hard).
  (`SK-ST-17` already depends on `SK-ST-09`, whose primary DP-100 is
  LC337 House Robber III (Medium), so the on-ramp already exists.)

- [ ] **Step 4: Remove the expectedFailure marker** from
  `test_tree_ladder_builds_before_serialize`.

- [ ] **Step 5: Verify**

```bash
make validate     # primary role/backref, ≥1 reinforcement, acyclicity, stage match
python3 scripts/test_curriculum_order.py
make test
git diff --quiet -- progress/progress.json && echo "progress untouched"
```

- [ ] **Step 6: Confirm the invariants explicitly**

```bash
python3 - <<'EOF'
import json
cur = json.load(open('curriculum/curriculum.json'))
skills = json.load(open('knowledge/skills.json'))
graph = json.load(open('curriculum/dependency_graph.json'))
by_id = {p['id']: p for p in cur['problems']}
S, SD = skills['skills'], graph['skill_dependencies']

hard_primaries = [
    k for k, v in S.items()
    if v.get('scope') != 'meta'
    and by_id[v['primary_validation_problem']]['difficulty'] == 'Hard'
]
print("hard primaries:", len(hard_primaries), sorted(hard_primaries))   # expect 6

def cyclic(graph_map, nodes):
    WHITE, GRAY, BLACK = 0, 1, 2
    colour = {n: WHITE for n in nodes}
    def visit(n):
        colour[n] = GRAY
        for m in (graph_map.get(n) or []):
            if colour.get(m) == GRAY:
                return True
            if colour.get(m, BLACK) == WHITE and visit(m):
                return True
        colour[n] = BLACK
        return False
    return any(colour[n] == WHITE and visit(n) for n in nodes)

print("skill cycle:", cyclic(SD, list(S)))                    # expect False
print("problem cycle:", cyclic(graph['problem_dependencies'], list(by_id)))  # expect False
print("stage mismatches:",
      sum(1 for p in cur['problems'] if p['stage'] != S[p['primary_skill']]['stage']))  # expect 0
EOF
```

- [ ] **Step 7: Commit**

```bash
git add curriculum/dependency_graph.json knowledge/skills.json curriculum/curriculum.json scripts/test_curriculum_order.py
git commit -m "$(cat <<'EOF'
fix/curriculum: teach the tool before the problems that need it

SK-IR-07 (segment tree / fenwick, medium primary lc307) depended on
SK-IR-04, the all-hard skill that USES a fenwick tree — the teaching skill
was gated behind its own application. edge reversed.

SK-RT-03 was hard-primary (lc297 serialize) with a hard-only reinforcement,
so the skill had no entry point: lc105 construct-tree-from-traversals moves
in as primary (it is literal deserialization) and lc297 becomes a
reinforcement that depends on it. dp-083 was labelled hard but lc1522 is
medium on leetcode, which had made SK-ST-17 an all-hard skill.
EOF
)"
```

---

### Task 4: Documentation and final verification

**Files:**
- Modify: `curriculum/dsa-skill-map.md` (stage section order)
- Modify: `README.md` (stage list if it enumerates the sequence)
- Create: `plans/CURRICULUM_ORDER_AUDIT.md` (the audit this plan implements)

- [ ] **Step 1: Reorder the stage sections** in
  `curriculum/dsa-skill-map.md` so its `## ` headers follow the new
  `stage_order` (Pattern Discovery after Recursive Thinking; Graph Thinking
  before State Transition). Move whole sections; do not edit their content.

- [ ] **Step 2: Update README** if it lists the stage sequence or claims
  readiness covers "nine stages" — it is ten now. Grep first:
  `grep -n "Graph Thinking\|nine stages\|stage" README.md | head -20`.

- [ ] **Step 3: Write the audit record** to
  `plans/CURRICULUM_ORDER_AUDIT.md`: the D1-D5 findings table, the
  before/after metrics table from this plan's header, and the deferred list
  below. This is the "why" for future readers.

- [ ] **Step 4: Full final state check**

```bash
make test && make validate \
  && python3 scripts/next_problem.py \
  && python3 scripts/revision_report.py \
  && python3 scripts/dashboard.py
git diff --quiet -- progress/progress.json && echo "progress.json untouched"
git log --oneline -5
```

- [ ] **Step 5: Independent review.** Dispatch a fresh-context reviewer with
  this plan and `git log` for the four commits. It must verify: all
  expectedFailure markers removed (no silently-skipped ordering tests), the
  before/after metrics in this header reproduce when it runs its own
  simulation, `stage_order`/`skill_order` identical across both files,
  and zero problems deleted (`git diff --stat` shows no problem-count
  change; `make validate` still reports 581). Fix Critical/Important
  findings, then re-verify.

- [ ] **Step 6: Commit**

```bash
git add curriculum/dsa-skill-map.md README.md plans/CURRICULUM_ORDER_AUDIT.md
git commit -m "$(cat <<'EOF'
docs/curriculum: record the ordering audit and resequence the skill map
EOF
)"
```

---

## Deliberately deferred (do NOT fix in this plan)

Each is real but post-readiness or lower value; fixing them here would widen
the blast radius without changing interview outcomes.

- **Six remaining Hard-primary skills**: `SK-IR-04` (LC315), `SK-IR-05`
  (LC327), `SK-IR-10` (LC715), `SK-QP-06` (LC295 — genuinely the canonical
  two-heap problem, keep), `SK-ST-05` (LC354), `SK-IN-03` (LC1206). The
  Interval Reasoning three would need new problems (e.g. LC729 My Calendar I)
  to have a Medium entry; that is a curriculum addition, not a reorder.
- **Word Search II (LC212) served ~6 positions before Subsets.** Was 229
  positions early; Task 1 reduces it to 6. Closing it fully needs either a
  forward-stage dependency (breaks a clean invariant) or re-skilling TRI-002
  into `SK-PD-05`. Accept for now.
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
