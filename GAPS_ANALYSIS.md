# DSA_OS Gaps Analysis

> Full-repo audit (every file, all ~30k lines) answering: **is this system solid and curated enough to make you a better problem-solving engineer and prepare you for DSA interviews?**
> Date: 2026-07-21. Progress at audit time: 10/557 problems completed, 6 revisions (all PASS), 3 skills mastered.

---

## Verdict

**Goal (a) — better problem-solving engineer: STRONG.** The 13-stage reasoning taxonomy with per-stage entry/exit/mastery criteria (`curriculum/stages.json`), the Socratic 12-state mentor loop with a hint ladder and struggle-before-hints rules (`mentor/mentor_protocol.md`), blueprint-before-code, proof-before-code, code-from-memory spaced revision, and the algorithm-thinking vs implementation-engineering score split are genuinely rigorous pedagogy — better than most public prep systems.

**Goal (b) — DSA interview prep: GOOD FOUNDATION, REAL DEFECTS.** ~85–90% of Blind-75/NeetCode-150 is covered with deep DP/graph/binary-search-on-answer content, but: interview *simulation* is entirely missing, all measurement is self-reported/gameable, the dependency chain is pedagogically inverted, ~5% of the problem list is duplicates, and there is **one blocker bug that will crash the revision workflow in ~2 more revisions**.

---

## P0 — Blockers (will break or corrupt the core loop)

### 1. R4 PASS crashes; mastery is unreachable
`scripts/_shared.py:25-30` defines revision intervals only for stages 0–3, but `apply_revision_result` (`_shared.py:1015-1027`) only masters at `attempted_stage >= 5` and otherwise indexes `REVISION_INTERVAL_DAYS[attempted_stage]`. Passing the 4th revision (stage 3→4) raises `KeyError: 4` (verified by simulation). `progress/scoring.json:122` says `mastered_after_stage: 4` — code contradicts its own policy. OBS-001 is at stage 2, due 2026-08-06; this crashes the live workflow soon. **Fix:** master at `>= 4`; add a regression test walking stage 0 → MASTERED. Related: `revision_stage_label` (`_shared.py:370-373`) invents a nonexistent "R5".

### 2. IST timezone off-by-one corrupts "due today" everywhere in the dashboard
`web_dashboard/app.js:81` parses dates as local midnight, `app.js:86` serializes via `toISOString()` (UTC) — in IST the round-trip returns the *previous day*. A revision due today shows "1 day left" during morning sessions; chart axis dates shift back a day. This degrades the single most actionable signal the dashboard has. **Fix:** format dates from local components, never `toISOString()`.

### 3. Overdue revisions don't block new solves
OBS-005/OBS-006 R1s overdue since 07-17/07-18, yet new solves (CPX-001/002) were recorded 07-21. `update_progress.py` never enforces revision-first; only `next_problem.py`'s *suggestion* does. The protocol's "revision before new work" rule (`boot_instructions/instructions.txt:14-16`) has no teeth in tooling. **Fix:** hard-warn or require `--override` in `update_progress.py` when revisions are overdue.

---

## P1 — Interview-readiness gaps (biggest gap vs your stated goal)

### 4. No interview simulation layer at all
- `interview_playbook.md` is a 41-line stub, **referenced by nothing** (zero inbound references), and overfit to week-1 Kadane content (follow-ups/edge cases are all Maximum-Subarray artifacts).
- No mock-interview mode: no state where the mentor plays interviewer for a timed, unassisted, full loop. The 12-state machine is a teaching loop only.
- No time budgeting: `--time-taken-minutes` is recorded but never budgeted (no 45-min cap, no pacing checkpoints). Boot Rule 19 (`instructions.txt:337-339`) explicitly says "Do not optimize for speed" — in direct tension with the mission "handle unfamiliar interview questions under pressure" (`docs/DSA_OS_MASTER.md:5`).
- "Interview discussion" is a revision PASS gate (`mentor_protocol.md:237`) and a scored dimension, but **no rubric anywhere** defines what a passing discussion sounds like.
- Zero behavioral prep; no statement of system-design scope (SK-IN-07 "Advanced System Design", `knowledge/skills.json:1751-1754`, is actually a LeetCode data-structure design problem).

**Fix:** build a mock-interview protocol (timed 45-min loop, mentor-as-interviewer, no hints, communication rubric, verdict + debrief), wire it in as a periodic gate (e.g., every N skills mastered), and grow `interview_playbook.md` per-topic as problems complete.

### 5. All measurement is self-reported and gameable
- Learner self-assesses hint level, all 13 rubric scores, and revision PASS/FAIL (`instructions.txt:26-32`, `HOW_TO_RUN.md:18`); nothing grades independently or audits against the transcript. Skill mastery and stage promotion sit on these numbers.
- `scoring.json:132` `pass_minimum: 7` is **never checked** — you can PASS a revision with all-zero scores (`update_progress.py:180-183`).
- `hint_level_used` never affects mastery — a hint-7 "solution revealed" solve counts the same as hint-0.
- `promotion_thresholds.*.minimum_completed_problems` (`scoring.json:59-112`) read nowhere.
- No code execution anywhere: no tests, no runners, no solution files. Completion is honor-system.
- Data shows the symptom: recent solves at hint level 2–3 still get uniform 4/4 thinking, 9–10/10 interview scores; OBS-001..004 are identical template-shaped score blocks. Confidence/interview "up-trends" are weak signals.

**Fix:** enforce `pass_minimum`; discount mastery by hint level; add a mentor-graded score pass distinct from self-report; consider a minimal test-runner per problem (even 3 asserts) so "solved" means executed.

### 6. Missing high-frequency interview classics
- **Matrix manipulation cluster absent**: no Rotate Image, Spiral Matrix, Set Matrix Zeroes, Game of Life, Valid Sudoku — top-frequency warmups.
- Absent classics (title-scan verified): Valid Palindrome, Merge Sorted Array, Majority Element (entire Boyer-Moore voting pattern missing), Rotate Array, Pow(x,n), Encode/Decode Strings, Construct Binary Tree from Preorder+Inorder (LC 105), BST Iterator, Subtree of Another Tree, Path Sum III, Longest Valid Parentheses, Meeting Rooms I, Surrounded Regions, Reconstruct Itinerary (Eulerian path pattern absent), Triangle, game-theory DP (only thin DP-060).
- Thin: 2-D prefix sums (none), BST hard tier (1 hard), tries (8, incl. 1 internal dup), rolling-hash/Rabin-Karp (named in notes, no dedicated problem), counting/bucket/radix sort (none).
- Importance tags undervalue must-dos: Sliding Window Maximum QUE-001, Word Search II TRI-002, N-Queens REC-019 all tagged SPECIALIZED.

---

## P2 — Curriculum data quality

### 7. ~25–30 duplicate problems inflate "557"
Beyond intentional revisits, the v2.1 supplemental batch re-added existing problems unflagged. Examples: TRI-004/TRI-008 (Replace Words), DES-021/RNG-019 (Stack with Increment — RNG-019 also mischaracterized as "snapshot design"), DES-012/DES-035, DES-006/DES-036, DES-001/DES-004 (LRU ×2), DES-002/DES-005 (LFU ×2), RNG-009/RNG-020, RNG-004/RNG-021, Kth Smallest in Sorted Matrix ×3 (BSR-010/HEP-008/HEP-023), GRF-001/GRF-007 (Rotten Oranges twice in same stage), OBS-021/OBS-025 (LC 28 under old+new names), MAT-001/MAT-005, LNK-003/LNK-027, REC-008/REC-032, LNK-013/ORD-015, DP-017/DP-100, DP-061/DP-094. True unique count ≈ 525–530. **Fix:** dedupe or mark as explicit revisits.

### 8. Dependency chain is a straight line, and it's inverted
`dependency_graph.json:112-381`: every skill's sole prerequisite is the previous skill — a fixed total order, not a real DAG. Consequences:
- PFX-002 Range Sum Query (Easy) is gated behind **all of MST/shortest-paths/union-find/topo-sort/103 DP problems/trees/tries** (`dependency_graph.json:1666-1668`).
- QUE-003 Implement Stack using Queues (Easy) gated behind hard tree DP (`:1453-1455`); heap basics behind the whole DP+graph stack.
- Backtracking (Pattern Discovery, stage 11) comes AFTER all DP, yet State Transition's own entry requirement is "can write a recursive brute force" (`stages.json:260`) — the ordering is self-contradictory.
- Segment trees (stage 6) taught before binary trees (stage 7); admitted as artificial in `skills.json:4`.
- Intra-skill deps are flat: hardest challenge unlocks right after the primary (e.g., Trapping Rain Water depends only on sorted Two Sum).
**Fix:** convert to a real DAG with 2–4 genuine prerequisites per skill; move prefix sums/queues/heaps/basic trees before DP/graphs.

### 9. Metadata rot in curriculum.json
- Wrong `notes` vs actual technique: OBS-009/010 labeled "Kadane" (interval greedy); DP-083..092 labeled "Bitmask DP" (tree/partition DP); TRE-026 Serialize/Deserialize labeled "BST property"; DP-012/013 Ugly Number labeled "Two Heaps/median"; QUE-003..006 design problems labeled "Monotonic Deque"; HEP-016 (single-heap greedy) is the PRIMARY exemplar for "Two Heaps" SK-QP-06.
- No LeetCode IDs/URLs anywhere — several titles ambiguous or non-canonical (GRF-054, DP-080, GRF-050 "Yen's Algorithm concept", DES-025 "Log Aggregation System" with no spec); RNG-008 bundles My Calendar I+II+III in one slot and duplicates as DES-029.
- `secondary_skill` null on all 557 (dead field); `section` reflects PDF page provenance not topic (DP-093..103 say "Strings", MAT-022 graph problem says "Linked Lists"); `module_order` (22 modules) used by nothing; version says 3.0 but changelog starts at 3.1; stale pre-3.0 stage names ("Foundational", "Optimizer") in changelog/notes and in `progress.json:760-801` history.
- `SK-IE-00`: 91st skill in `dependency_graph.json:110` but absent from stages.json's 90; `global_skill_dependencies` uses difficulty strings "Medium"/"Hard" as keys (`:2054-2061`) — schema smell. `stages.json:415` "each of the other 11 stages" — off-by-one (12).

### 10. skills.json entries are shallow labels with copy-paste errors
90 skills sequencing 557 problems is a real spine, but entries are name + 1–3 sentences: **no trigger cues, no template, no pitfalls** (those exist only in the 9 patterns). Name/description mismatches describing *different techniques*: SK-SC-03 (`skills.json:239`), SK-CM-05 (`:401`), SK-ST-04 (`:945`), SK-ST-11 (`:1043`), SK-GT-01 (`:1201`); many others are "PDF subsection: X" boilerplate.

---

## P3 — Knowledge/mentor layer hygiene

### 11. Pattern layer is high quality but 9/~30 built
All 9 `knowledge/patterns.json` entries carry full schema (mental model, recognition signals, invariant, proof, complexity, contrasts, mistakes) — but they only cover the first 10 solved problems. Zero classic families (sliding window, two pointers, monotonic stack, binary-search-on-answer, BFS/DFS, topo sort, union-find, backtracking, DP families, heaps, intervals, tries, bit tricks) exist as pattern entries yet; growth is learner-paced by design, but this means recognition training lags exactly when it matters. PAT-003/PAT-008 are problem-specific in disguise ("products of non-empty subarrays", "each child must receive").

### 12. Protocol duplication and three conflicting hint ladders
- Implementation Blueprint duplicated in **5 files** (mentor_protocol, enhanced_mentor_protocol, DSA_OS_MASTER, README, case_file_template); revision gates and 9-item review in 4. Every edit must land in 4–5 places; drift already visible (`enhanced_mentor_protocol.md:43-44` duplication artifact).
- **Three divergent hint ladders** all claiming to match `scoring.json.hint_levels`: `mentor_protocol.md:252-265` (amount of help), `DSA_OS_MASTER.md:96-113` (hint types), `mentor_memory.md:30-38` (third variant). Same session can honestly log different hint levels.
- Direct contradiction: `DSA_OS_MASTER.md:126` step 7 "Name the pattern" vs Golden Rule 1 + Boot Rule 13 (`instructions.txt:263-277`) forbidding naming; `case_file_template.md:42` demands "Chosen pattern:".
- Four different session flows (12-state protocol / 14-step MASTER / 10-step mentor_memory / stale 9-step session_notes with no Blueprint).
**Fix:** make mentor_protocol.md literally the only copy; reduce others to links.

### 13. Fossilized files — exactly the ones no protocol step forces the mentor to touch
`AFTER_PROBLEM_COMPLETION.md:87-103` lists update candidates but omits the three files that rotted:
- `mentor_memory.md`: written day 1, never updated, ~90% process duplication (violating `mentor_protocol.md:13-15` state-not-process rule), zero learner-specific facts, plus the third hint ladder. Real profile lives in `progress.json.thinking_profile`.
- `session_notes.md`: orphaned, stale flow, referenced by nothing — delete or archive.
- `interview_playbook.md`: see #4.
- `mistake_catalog.json`: 3 entries after 10 solves; M001/M002 have no provenance. Compare legacy archive where every session logged multiple mistakes — capture discipline exists but isn't routed here.
- `instructions.txt:366-370` ends in corrupted fragment text.
- `case_file_template.md:8-10` still has pre-v3.0 `Original Number`/`Module` fields.
- `thinking_patterns.md` Pattern 004 vs PAT-009: near-verbatim duplication (same invariant/proof/3-of-4 mistakes) — the two-file distinction isn't holding in practice.

---

## P4 — Tooling correctness (beyond the P0 crash)

### 14. Weakness lab distortions
- Resolved weaknesses still count as live evidence at full severity (`weakness_lab.py:280-292` ingests "Resolved: ..." strings from `progress.json:1870-1893`) — clusters inflated by already-fixed issues.
- "LC {n}" labels are wrong: `weakness_lab.py:408,464` prints `original_number` (position in 507-problem source PDF) as a LeetCode id — Word Break shown as "LC 76" (real 139), Jump Game "LC 35" (real 55).
- Keyword substring classification (`weakness_lab.py:104-113`) is brittle; differently-phrased mistakes silently dropped (dashboard has the same issue, `app.js:721`).
- Revision failures never feed weakness detection: `weakest_skills` and dimension averages use only day-one solve scores (`_shared.py:1134`), so a repeatedly-failed problem keeps its original score forever.
- Evidence fields `weaknesses_detected`/`lessons_learned`/`personal_playbook` are hand-authored, unvalidated (`validate_curriculum.py:83-99` omits them), and absent from the template — a fresh clone gets almost no weakness signal.

### 15. Misc script issues
- Revision mode forces all 13 solve-rubric scores then discards them (`update_progress.py:98-144,439-452` vs `:482-489`) — invites fabricated numbers.
- `implementation_engineering.score` is last-write-wins, shown as a standing metric (`update_progress.py:376-378`, `dashboard.py:97-102`).
- Weights table duplicated in code vs scoring.json (`_shared.py:438-445`).
- progress.json anomalies: OBS-001 has 2 revision-completion dates but 1 history event; history uses nonexistent stage "Foundational"; `notes` mixes object and string formats; free-form fields (`session_summary`, `variable_semantics`…) exist only in live data, never templated/validated.
- Spaced repetition is fixed-interval Leitner (3/7/21/60), not SM-2 — no ease factor, no modulation by recall quality or hint level. Acceptable, but the full ladder has never run end-to-end (blocked by #1).

### 16. Dashboard issues (least important layer)
- `thinking_patterns.md` fetched inside `Promise.all` but never rendered (`app.js:10,171,190`) — deleting the file kills the entire dashboard.
- `dependency_graph.json` never fetched — dependency layer invisible.
- `mistake_catalog` entries checked for nonexistent `source_problem` field (`app.js:1119`) — "Open problem" button never renders.
- Latent crash: unresolvable `problem_id` → `a.problem.id.localeCompare` TypeError blanks all revision views (`app.js:286,303`).
- Richest data discarded: per-revision `misconception_corrected`, per-dimension recall scores, `personal_playbook` unread, while ~40% of screen restates static coaching text; Analytics tab mostly vanity (dials/funnels restating Today-tab counts). Hardcoded PAT-001..009 cues (`app.js:1926,2014,2029`) stop scaling at PAT-010. "Showing-up" chart clamps after day 30 (`app.js:2914`). Badge/modal mistake counts disagree (`app.js:890` vs `:1121`).

---

## What's genuinely good (keep, don't churn)

- 13-stage reasoning taxonomy with concrete exit criteria and failure modes (`stages.json`) — unusually good.
- Socratic state machine, hint-metering, proof-before-code, blueprint-before-code, code-from-memory revision gates, deferred learnings, algorithm-vs-implementation score split.
- `validate_curriculum.py` — strong cross-file checker incl. acyclicity and recompute-vs-cache derived-state verification (passes on current data).
- Pattern entry schema (PAT-001..009) — the capture discipline demonstrably works.
- Dashboard Today tab `nextAction()` priority policy + Weakness Lab concept.
- Zero phantom file references; scripts all run clean; stdlib-only; no hardcoded paths.

---

## Priority fix order

| # | Fix | Effort |
|---|-----|--------|
| 1 | R4 mastery crash (`_shared.py:1018` → `>= 4` + test) | trivial |
| 2 | Dashboard IST date bug (`app.js:81/86`) | small |
| 3 | Enforce `pass_minimum` + hint-level discount on mastery | small |
| 4 | Build mock-interview mode (timed, unassisted, rubric, cadence) | medium — **highest value for goal** |
| 5 | Dedupe ~28 duplicate problems; add LC IDs/links | medium |
| 6 | Add matrix cluster + ~15 missing classics; fix importance tags | small |
| 7 | Re-wire dependency graph into a real DAG; reorder prefix-sums/queues/heaps/trees before DP/graphs | medium |
| 8 | Consolidate protocol to one copy; single hint ladder; delete/archive session_notes, refresh or delete mentor_memory | small |
| 9 | Weakness lab: skip resolved, fix "LC n", feed revision failures into scores | small |
| 10 | Fix skills.json name/description mismatches; correct wrong curriculum notes | small |

## Unresolved questions
- Mock-interview cadence: every N skills, weekly, or stage-exit gate?
- Dedupe policy: delete dup slots or mark as formal "revisit" entries?
- Add code-execution (test asserts per problem) or keep honor-system?
- Target date for interviews? (determines whether linear chain reorder is worth it vs just overriding order manually)

> NOTE (added on recreation, 2026-07-21): line numbers in this document reference the repo state at audit time (commit 12d2169), BEFORE the fixes landed. The "Unresolved questions" above were subsequently answered — see the Decisions log in FIXES_PROPOSAL.md. This file was accidentally deleted from the working tree and has been recreated verbatim from the audit session.
