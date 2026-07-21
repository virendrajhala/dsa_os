# Phase 5 Plan — Curriculum Data Quality (F15 → F18 → F17 → F16 → F19)

Read `PHASE_EXECUTION_GUIDE.md` first. Effort: 2-3 days of model time. **Execute in EXACTLY this order** — dedupe before reordering, reorder before adding problems, add problems before backfilling links, metadata sweep last. One commit per task.

These tasks all touch `curriculum/curriculum.json` (9k lines), `curriculum/dependency_graph.json`, `curriculum/stages.json`, `knowledge/skills.json`, `curriculum/dsa-skill-map.md`. The cross-file invariants are enforced by `make validate` — run it CONSTANTLY. The five files must stay mutually consistent: every problem's `primary_skill` exists in skills.json/stages.json; skills.json's primary/reinforcement/challenge problem-ID lists match curriculum.json membership + `problem_role`; dependency_graph has a node per problem and per skill; dsa-skill-map.md's counts match.

**Data-safety rule**: `progress/progress.json` references completed problems OBS-001..008, CPX-001, CPX-002 and (possibly, if a mock/solve happened since) other IDs — NEVER delete or re-ID a problem that appears anywhere in progress.json. Check first:
```
python3 - <<'EOF'
import json,re
p=open('progress/progress.json').read()
print(sorted(set(re.findall(r'"(?:[A-Z]{3}-\d{3})"',p))))
EOF
```

---

## Task F15 — Dedupe duplicate problems

### Decided policy (user-approved — do not re-litigate)
For each duplicate pair (same underlying problem in two slots):
- **KEEP BOTH** (later slot gains `"revisit_of": "<earlier-ID>"`) only if the later slot's `primary_skill` is a genuinely DIFFERENT skill that the problem legitimately exercises (e.g. Kth Smallest in Sorted Matrix as binary-search-on-answer vs as heap).
- **DELETE the later slot** if same skill, same stage, or the second mapping is bogus.
- **Contentious pairs**: if you cannot confidently decide, DO NOT delete — list the pair + both skills + your lean in your report under "Needs user decision" and move on.

### Known pairs from the audit (verify each against current data before acting; normalized-title scan may find more):
Likely DELETE (later slot): GRF-007 (Rotting Oranges; GRF-001 same stage), OBS-025 (LC 28 dup of OBS-021), TRI-008 (Replace Words; dup of TRI-004), DES-004/DES-005 (LRU/LFU dups of DES-001/DES-002), DES-035 (dup of DES-012 Underground System), DES-036 (dup of DES-006 Design Twitter), RNG-019 (Stack with Increment; dup of DES-021, mislabeled "snapshot design"), RNG-020 (Rectangle Area II; dup of RNG-009), RNG-021 (Range Sum Mutable; dup of RNG-004), HEP-023 (Kth Smallest Matrix, 3rd copy), MAT-005 (Happy Number; dup of MAT-001), LNK-027 (Cycle II; dup of LNK-003), REC-032 (Combination Sum III; dup of REC-008), ORD-015 (Sort List; dup of LNK-013), DP-100 (House Robber III; dup of DP-017), DP-094 (Palindrome Partitioning II; dup of DP-061).
Likely KEEP+revisit_of: WIN-012 (Min Window revisit of WIN-004), STK-015 (Largest Rectangle revisit of STK-010), TWO-001 & HSH-005 (Two Sum re-seen through sorted-two-pointer and hashing lenses; CPX-001 is the first and is COMPLETED — keep all three, revisit_of chain to CPX-001), HEP-008 (Kth Smallest Matrix as heap, revisit_of BSR-010), DP-040/DP-041 (Regex/Wildcard revisits of DP-002/DP-001), DES-029 vs RNG-008 (My Calendar — see F16 note; keep DES-029 as revisit or delete after F16's unbundling decision — if unsure, mark contentious).

### Mechanics per deleted slot
Removing problem X requires, atomically: remove its object from curriculum.json; remove its ID from skills.json (whichever of primary/reinforcement/challenge lists holds it — if X was a skill's PRIMARY, promote the strongest same-skill reinforcement to PRIMARY and update `problem_role` fields accordingly, and say so in the report); remove its node from dependency_graph.json `problem_dependencies` AND any references to it in other problems' dependency lists (re-point them to X's kept twin); update dsa-skill-map.md counts; update any headline counts (curriculum.json header/metadata block, README.md if it states 557, dsa-skill-map.md totals).

### Schema + validator
- Add optional `"revisit_of": "<ID>"` to kept later slots. validate_curriculum.py: (a) accept the field, validate the target ID exists and is EARLIER in module ordering; (b) upgrade the existing duplicate-title WARNING to an ERROR unless the later slot carries `revisit_of`.
- Write a normalized-title duplicate scan (lowercase, strip punctuation/roman numerals/parentheticals) into the validator or a one-off check to catch pairs beyond the audit list; triage each by the policy above.

### Verify
`make test && make validate` (validator now errors on unmarked dups — proves the check works: temporarily duplicate a title to see it fire, then revert). Total problem count reported by validate drops by the number of deletions; report the new number.

### Commit
`fix/curriculum: dedupe duplicate problems, add revisit_of markers`
Body: N deleted (list IDs), M marked revisit_of, contentious pairs listed for user.

### Done when
- [ ] Every audit pair resolved or explicitly listed as contentious (report section)
- [ ] No problem referenced by progress.json was deleted
- [ ] skills.json/dependency_graph/dsa-skill-map/counts all consistent (validate passes)
- [ ] Duplicate-title check is now an ERROR unless revisit_of

---

## Task F18 — Real dependency DAG + stage reorder (user-approved: apply NOW)

### 18a. Stage reorder
New `stage_order` (apply IDENTICALLY in stages.json, dependency_graph.json, and anywhere else stage order is listed — grep the stage names):
1. Observation
2. State Construction
3. Constraint Maintenance
4. Ordered Reasoning
5. Query Processing            ← moved up (prefix sums/heaps/queues)
6. Decision Making
7. Recursive Thinking          ← moved up (trees/backtracking before DP)
8. State Transition            (DP)
9. Graph Thinking
10. Interval Reasoning         ← moved down (segment/Fenwick trees AFTER basic trees)
11. Pattern Discovery
12. Mathematical Thinking
13. Integration

Notes: stage NAMES and stage→skill membership do NOT change — only the order. All completed work is in Observation (position 1 before and after) so `progress.json` is unaffected. The F23 readiness config (`stage_scope_count: 9` = first 9 of stage_order) intentionally now spans through Graph Thinking — verify after reorder that position 9 IS Graph Thinking, and run the readiness section of `python3 scripts/revision_report.py` to confirm it still computes.

### 18b. Skill dependencies: linear chain → real DAG
`dependency_graph.json.skill_dependencies` currently gives every skill exactly one prereq (the previous skill in a global chain). Replace with 1-4 REAL prerequisites per skill. Authoring principles:
- A skill's prereqs are the skills whose TECHNIQUE it composes or extends — not whatever happened to precede it. (Tree DFS needs recursion basics, not segment trees. Prefix sums need array iteration, not union-find.)
- First skill of each stage: prereqs from EARLIER stages only. Within a stage, chain only where genuinely cumulative.
- Every skill except stage-1 entry skills must have ≥1 prereq; nothing depends on a LATER stage's skill (respect the new stage order).
- SK-IE-00 (Implementation Engineering meta-skill): resolve its dangling status — REGISTER it properly: add to stages.json under Integration as a problemless meta-skill (with a one-line description) so the 91-skill count is consistent everywhere, and give it no prereqs. Replace the malformed `global_skill_dependencies` block (which uses difficulty strings "Medium"/"Hard" as keys) with a well-formed `difficulty_gates` object: `{"difficulty_gates": {"Medium": ["SK-IE-00"], "Hard": ["SK-IE-00"]}}` plus a `_comment` explaining it, and make the validator accept the new shape.
- Sanity examples the new DAG must satisfy (spot-checks the reviewer will run): basic prefix-sum skill reachable without ANY DP/graph skill; queue basics without tree DP; tree traversal without segment trees; backtracking before/independent of DP families.

### 18c. Intra-skill problem dependencies
Currently every reinforcement AND challenge depends only on the skill's PRIMARY. Change: reinforcements depend on the primary (unchanged); CHALLENGE problems depend on ≥1 REINFORCEMENT of the same skill (pick the most related by technique/difficulty; if a skill has no reinforcements, primary is fine). This kills the "Trapping Rain Water unlocked right after Two Sum" jump.

### 18d. Cleanups bundled here
- stages.json Integration entry requirement text "each of the other 11 stages" → "12".
- Delete dead `module_order` from curriculum.json — FIRST verify nothing reads it: `grep -rn "module_order" scripts/ web_dashboard/`. If something reads it, fix the reader instead of keeping the field.
- validate_curriculum.py: REMOVE the one-prereq-per-skill rule; KEEP acyclicity (now over a real DAG); ADD sanity check "no Easy problem may transitively require more than 30 problems" (BFS over problem_dependencies; count unique transitive prereq problems).

### Verify
```
make test && make validate
python3 scripts/next_problem.py         # still selects sensibly
python3 scripts/revision_report.py      # readiness section intact, scope = through Graph Thinking
```
Also write (in the validator or as a test) the acyclicity + Easy-depth checks BEFORE rewiring, so violations surface as you author.

### Commit
`feat/curriculum: real skill DAG and interview-priority stage order`

### Done when
- [ ] stage_order identical in all files, position 9 = Graph Thinking
- [ ] Every skill 1-4 real prereqs, no forward-stage deps, acyclic
- [ ] SK-IE-00 registered; difficulty_gates well-formed; validator updated
- [ ] Challenges gated behind reinforcements
- [ ] "11"→"12" fixed; module_order gone (or reader fixed)
- [ ] Easy-depth sanity check active and passing

---

## Task F17 — Add missing interview classics

Add these problems (new IDs continuing each module's numbering; every new problem gets the full field set used by existing problems + `lc_id` + `url` since F16 follows — fill them here to save a pass). Assign `primary_skill` to the EXISTING skill that genuinely matches; the two flagged ones get a NEW skill:

**New skill 1: Matrix Simulation** (suggested ID following the SK-<stage-prefix>-NN convention used in skills.json — put it under the **State Construction** stage; in-place transforms are state manipulation, and that stage is early enough for warmups): Rotate Image (LC 48), Spiral Matrix (LC 54), Set Matrix Zeroes (LC 73), Game of Life (LC 289), Valid Sudoku (LC 36). One of these (Rotate Image) is PRIMARY, rest REINFORCEMENT; all get MAT-prefixed IDs continuing from the highest existing MAT number.
**New skill 2: Boyer-Moore Voting** — under **Observation** stage: Majority Element (LC 169) PRIMARY, Majority Element II (LC 229) CHALLENGE. OBS-prefixed IDs.

**Additions to existing skills** (pick nearest-technique skill; state your mapping per problem in the report): Valid Palindrome (LC 125), Merge Sorted Array (LC 88), Rotate Array (LC 189), Pow(x,n) (LC 50), Encode and Decode Strings (LC 271), Construct Binary Tree from Preorder+Inorder (LC 105), BST Iterator (LC 173), Subtree of Another Tree (LC 572), Path Sum III (LC 437), Longest Valid Parentheses (LC 32), Meeting Rooms (LC 252), Surrounded Regions (LC 130), Reconstruct Itinerary (LC 332), Triangle (LC 120), Predict the Winner (LC 486), Range Sum Query 2D — Immutable (LC 304), Longest Duplicate Substring (LC 1044, rolling hash).

Difficulty per LeetCode; `importance`: CORE for all of the above except Predict the Winner/Longest Duplicate Substring (COMMON). `original_number`: null, `supplemental`: true (match existing supplemental problems' field pattern), `status`/`revision_count` defaults matching peers.

**Wiring per new problem/skill**: skills.json lists; dependency_graph problem node + intra-skill deps per F18c rules; new skills added to stages.json stage skill lists + dependency_graph skill_order + skill_dependencies (real prereqs per F18b principles); dsa-skill-map.md rows; counts updated everywhere.

**Importance retags** (existing problems → CORE): QUE-001 Sliding Window Maximum, TRI-002 Word Search II, REC-019 N-Queens, HEP-014 Sliding Window Median.

### Verify
`make test && make validate`; report new total problem count; spot-check `python3 scripts/next_problem.py` unaffected.

### Commit
`feat/curriculum: add matrix simulation, voting, and missing interview classics`

---

## Task F16 — lc_id + url backfill (all problems)

1. Schema: every problem gets `lc_id` (positive int or null) and `url` (string or null). Non-LeetCode problems (SPOJ/GFG/custom): `lc_id: null`, `source`: "SPOJ"|"GFG"|"custom", url to the actual source when known.
2. Backfill ALL problems (~545 post-F15/F17). Work in batches by module; use a scratch script to apply a title→lc_id mapping table you author. **Accuracy rule: only set lc_id when confident of the exact LeetCode problem; otherwise leave null and add the title to an "unresolved" list in your report.** Known ambiguous/non-canonical titles from the audit — expect nulls or judgment calls: GRF-054 "Minimum Cost to Reach City with Tolls", DP-080 "Count Ways to Distribute Candies", GRF-050 "K-th Shortest Path (Yen's Algorithm concept)", DES-025 "Design a Log Aggregation System", GRD-026 "Earliest Deadline First Scheduling" (mark custom).
3. **RNG-008 "My Calendar I, II, III"** bundles three problems: replace with a single slot "My Calendar III" (LC 732), retitle, note in `notes` that I/II (LC 729/731) are lead-ins. Reconcile with its twin DES-029 per your F15 resolution.
4. validate_curriculum.py: validate lc_id (null or positive int, UNIQUE across problems except revisit_of pairs which must SHARE their twin's lc_id) and url shape. The uniqueness check is a free extra dedupe guard — if it fires on a pair F15 missed, triage per F15 policy.
5. `scripts/weakness_lab.py`: it prints "LC {original_number}" — original_number is the source-PDF index, NOT a LeetCode id (Word Break shows "LC 76", real 139). Fix: print real `lc_id` when set, else `#{original_number} (source index)`, never the string "LC" for original_number.
6. Dashboard (optional, small): if trivial, render `url` as a link in the problem modal; skip if it balloons scope.

### Verify
`make test && make validate`; `python3 scripts/weakness_lab.py` output shows correct LC numbers for Word Break (139)/Jump Game (55) if they appear; report: count with lc_id, count null, unresolved list.

### Commit
`feat/curriculum: backfill lc_id and source urls, fix weakness-lab labels`

---

## Task F19 — Metadata repair sweep

1. **Wrong `notes` in curriculum.json** (note must describe ITS problem's actual technique — cross-check against the now-present lc_id): OBS-009 Partition Labels + OBS-010 Min Arrows (say "Kadane's" → interval greedy); DP-083..DP-092 (say "Bitmask DP" → actually tree-DP/partition-DP/etc. — rewrite each individually); TRE-026 Serialize/Deserialize (says "BST Property"); DP-012/DP-013 Ugly Number II (say "Two Heaps/median"); QUE-003..QUE-006 design problems (say "Monotonic Deque"). Scan for other mismatches while there: any note naming a technique that contradicts the problem's primary_skill deserves a look.
2. **skills.json name/description mismatches** (rewrite description to match the NAME; these were copy-paste errors): SK-SC-03 "Cycle Detection or Value-Space Search" (desc says Sorting+Binary Search), SK-CM-05 "Monotonic Stack on Linked List" (desc says In-place Reversal), SK-ST-04 "LIS DP with Bisect" (desc says Parametric Search), SK-ST-11 "Pointer Dynamic Programming" (desc says Two-Heap median), SK-GT-01 "Queue / Deque / BFS" (desc says Monotonic Deque). Also purge remaining "PDF subsection: X" boilerplate descriptions — replace with 1-2 real sentences about the technique.
3. **SK-QP-06 "Two Heaps / Priority Queue" primary swap**: current PRIMARY HEP-016 (Connect Sticks — single-heap greedy, poor exemplar) → make HEP-013 (Find Median from Data Stream — the actual two-heaps pattern) PRIMARY. Update: skills.json primary/reinforcement lists, both problems' `problem_role` in curriculum.json, dependency_graph intra-skill deps (per F18c), dsa-skill-map.
4. **Remove `secondary_skill`** (null on every problem, carries zero information): delete the key from all problems + from validator's field expectations + from progress_template if present. FIRST grep readers: `grep -rn "secondary_skill" scripts/ web_dashboard/` — fix any reader.
5. **Rename `section` → `source_section`** on all problems (it reflects PDF page provenance, NOT topic — e.g. DP problems say "Strings"). Grep readers first (`grep -rn '"section"\|\.section' scripts/ web_dashboard/`) and update them. Add a `_comment` near the top-level metadata: "source_section = provenance in the source PDF; NOT a topic tag."
6. **Version/changelog**: curriculum.json says `"version": "3.0"` but its changelog's newest entry is v3.1 → set version to match the newest changelog entry you'll add for phases 5's changes (add a changelog entry summarizing F15-F19: dedupe, DAG, classics, lc_id, metadata — bump version to 3.2). Normalize the v2.1 changelog entry from bare string to the object shape of the others.
7. **progress.json history stage names** (EXPLICITLY AUTHORIZED progress.json edit — this task only): `history[]` entries with `stage_before`/`stage_after` = "Foundational" (a stage that no longer exists) → "Observation". Touch NOTHING else in the file. Then add a validator check: history stage names must be in stages.json's stage set (so this can't regress).

### Verify
`make test && make validate`; `git diff progress/progress.json` shows ONLY the Foundational→Observation strings; dashboard loads (`node --check web_dashboard/app.js` + serve once) since section/secondary_skill readers may have been touched.

### Commit
`fix/curriculum: metadata repair sweep (notes, skill descs, fields, changelog)`

### Done when (whole phase)
- [ ] All five tasks committed in order, validate passing after each
- [ ] Contentious F15 pairs + unresolved F16 titles listed in reports for the user
- [ ] progress.json diff across the whole phase = only F19's history stage-name fix
