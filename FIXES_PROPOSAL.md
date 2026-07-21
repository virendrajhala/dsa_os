# DSA_OS Fixes Proposal

> Companion to `GAPS_ANALYSIS.md` (2026-07-21). Each fix: what to change, where, how, and how to verify. Grouped into 6 phases in recommended execution order. Effort: T=trivial (<30min), S=small (<2h), M=medium (half day+).

---

## Phase 1 — Hotfixes (do before next session; nothing else is safe until these land)

### F1. Fix R4 mastery crash [T]
- `scripts/_shared.py:1018` (`apply_revision_result`): change mastery condition `attempted_stage >= 5` → `attempted_stage >= 4`, matching `scoring.json:122` (`mastered_after_stage: 4`).
- `scripts/_shared.py:370-373` (`revision_stage_label`): cap labels at R4 + MASTERED; remove phantom "R5".
- Add regression test `scripts/test_shared.py`: simulate one record PASS×4 from stage 0 → status MASTERED, no KeyError; FAIL path retries next day at same stage. Wire into `make validate` or new `make test`.
- Verify: run test; then dry-run `apply_revision_result` on a copy of OBS-001 advanced to stage 3.

### F2. Fix IST date off-by-one in dashboard [S]
- `web_dashboard/app.js:86` (`isoDate`): build from local components (`getFullYear/getMonth/getDate`, zero-padded), never `toISOString()`.
- Audit every other `toISOString()` call in app.js (incl. `addDays` at :3072, `referenceDate` at :276) — same local-format helper everywhere.
- Verify: with system TZ Asia/Kolkata before 05:30, a revision with `next_due` = today renders "due now"; chart x-axis dates match progress.json dates exactly.

### F3. Enforce revision-first in tooling [S]
- `scripts/update_progress.py`: on recording a NEW solve, if any revision overdue → abort with list of overdue IDs; `--override-revisions` flag to bypass (logged into the record's notes).
- Verify: with OBS-005/006 overdue, recording a new solve without flag exits non-zero.

### F4. Dashboard latent-crash + wiring fixes [S]
- `app.js:286,303`: filter out entries with unresolved `problem_id` before sort (and surface a warning banner) instead of `{}` placeholder → TypeError.
- `app.js:10,171,190`: drop `thinking_patterns.md` from the critical `Promise.all` (fetch lazily or delete — it's never rendered).
- `app.js:1119`: read mistake_catalog's real fields `{id, title, symptom, fix}`; drop nonexistent `source_problem` or add that field to catalog entries going forward (see F15).
- `app.js:400`: guard `total === 0`.
- Verify: temporarily rename thinking_patterns.md → dashboard still loads; add fake completion with bogus problem_id → warning, no blank views.

---

## Phase 2 — Measurement integrity (make scores mean something)

### F5. Enforce pass_minimum on revisions [S]
- `scripts/update_progress.py:180-183` / `_shared.py:961+`: when `--revision-result PASS`, require avg revision recall score ≥ `scoring.json.revision_evaluation.scale.pass_minimum` (7). Below → error: "scores say FAIL; pass explicitly with --force-pass and a reason".
- Verify: PASS with score 5 rejected; recorded FAIL reschedules next day.

### F6. Hint level discounts mastery [S]
- `_shared.py:642-644` (skill-mastery check): solve with `hint_level_used >= 5` (pattern revealed or more) does NOT count toward skill mastery — counts as attempt only; hint 3-4 counts at reduced weight (proposal: 0.5). Encode weights in `scoring.json` (new `hint_mastery_discount` map), read from there — no second hardcoded table.
- Also remove "provisionally passing" leniency: completion with no numeric thinking score counts as NOT passing the 2.6 bar.
- Verify: unit test — skill with primary solved at hint 6 stays unmastered.

### F7. Mentor-graded scoring pass, separate from self-report [S — protocol change, no code]
- `mentor/mentor_protocol.md` (single edit point, see F12): in Retrospective state, mentor independently assigns all rubric scores WITH one-line evidence quotes from the session before the learner sees/states theirs; both recorded — add `mentor_scores` block alongside existing scores in the completion record; `AFTER_PROBLEM_COMPLETION.md` gains the field. Divergence > 2 points on any dimension → must be discussed and noted.
- `scripts/validate_curriculum.py`: accept optional `mentor_scores` with same schema as thinking/interview scores.

### F8. Stop forcing junk input in revision mode [T]
- `scripts/update_progress.py:98-144,439-452`: make the 13 solve-rubric args and `--confidence-before`/`--time-taken-minutes` optional (ignored) in revision mode; require only revision scores, result, hint level, confidence-after.
- Verify: revision recordable without solve-rubric flags.

### F9. Minimal code execution [M — DECIDED: adopt]
- Add `solutions/<PROBLEM-ID>.py` convention + `scripts/run_checks.py`: each solution file has 3-5 embedded asserts (learner writes them at edge-case step — doubles as edge-case practice). `update_progress.py` new-solve mode refuses completion if solution file missing or asserts fail; `--no-code` escape hatch for whiteboard-style sessions.
- Deliberately NOT full test harness — just "solved means it ran".

---

## Phase 3 — Interview simulation layer (highest value for the stated goal)

### F10. Mock-interview protocol [M]
New file `mentor/mock_interview_protocol.md` (linked from mentor_protocol.md, not duplicated):
- **Trigger cadence (DECIDED): weekend mocks** — every Saturday/Sunday session opens with a mock (one per weekend minimum; second one optional if first verdict ≤ no-hire). Weekday sessions stay teaching-only. Scheduler: `next_problem.py` gains a `mock_due` mode — on Sat/Sun with no mock recorded that weekend, it outranks new work (overdue revisions still first).
- **Format**: 45-min hard cap, mentor plays interviewer. Problem = unseen problem from a mastered/adjacent skill (never current in-progress skill). NO hints beyond interviewer-realistic clarifications; hint ladder disabled. Pacing checkpoints announced at 15/30/40 min.
- **Loop**: intro → clarifying questions → approach + complexity verbally BEFORE code → code → walkthrough with own test cases → follow-up variation → verdict.
- **Rubric** (recorded in progress.json new `mock_interviews[]` array): problem-solving, communication, code quality, testing, time management — each 1-4 with anchored descriptors written INTO the protocol (what a 2 vs 4 sounds like). Overall verdict: strong-hire/hire/no-hire/strong-no-hire, interviewer-style.
- **Debrief**: gaps feed `weaknesses_detected` (tagged `source: mock`), playbook update.
- `scripts/update_progress.py`: new `--mode mock` recording the rubric; `validate_curriculum.py`: schema for `mock_interviews`.
- Resolve the speed contradiction: amend Boot Rule 19 (`instructions.txt:337-339`) to "no speed pressure in TEACHING sessions; mocks are timed".

### F11. Grow interview_playbook.md into a living file [S]
- Restructure to per-topic sections (arrays/strings, trees, graphs, DP, design); each problem completion appends its "interview takeaway" here (add to `AFTER_PROBLEM_COMPLETION.md` update-candidates list — this is why it fossilized).
- Add the missing communication rubric (merge `DSA_OS_MASTER.md:202-213` rules in, F10 rubric anchors reference it).
- Scope (DECIDED): add the line "System design and behavioral are OUT of scope for this repo — DSA only." Rename SK-IN-07 "Advanced System Design" → "Data-Structure Design" so the name stops implying system design.

### F23. Interview-readiness estimator (DECIDED: system-derived, no fixed target date) [S]
- New section in `scripts/revision_report.py` (+ dashboard Today card): compute and display
  - **Pace**: problems/week and skills-mastered/week over trailing 4 weeks.
  - **Readiness threshold** (proposal, tune in scoring.json): ≥80% of CORE-importance skills mastered across stages 1-9 (post-F18 order, i.e. through Graph Thinking), ≥90% revision PASS rate, last 3 weekend mocks ≥ "hire".
  - **Projection**: at current pace, estimated date threshold is met — "interview-ready around <date>".
- Readiness gates NOTHING (informational only); recomputed every run, so pace changes update the projection automatically.
- Config lives in `scoring.json` new `readiness` block so thresholds are editable without code.

---

## Phase 4 — Protocol consolidation (cheap, prevents drift)

### F12. Single source of truth, mechanically enforced [S]
- `mentor/mentor_protocol.md` = only copy of: blueprint, hint ladder, review order, revision gates, session flow.
- `enhanced_mentor_protocol.md` → 5-line pointer file (delete duplicated blueprint at :18-46).
- `DSA_OS_MASTER.md` → keep philosophy/scoring rationale; replace its session flow (:116-133), hint system (:96-113), blueprint (:143-151) with links. **Delete step 7 "Name the pattern"** (:126) — contradicts Golden Rule 1.
- `README.md:170-179` blueprint → link.
- `case_file_template.md`: :42 "Chosen pattern" → "Governing invariant (in your own words)"; fix stale `Original Number`/`Module` fields (:8-10) → `primary_skill`.
- ONE hint ladder: keep `mentor_protocol.md:252-265` semantics, rewrite `scoring.json.hint_levels` descriptions to match verbatim; delete the variants in DSA_OS_MASTER and mentor_memory.
- `validate_curriculum.py`: add check that hint-level descriptions appear in exactly one .md (grep-based guard) — optional but keeps it honest.

### F13. Kill/repair fossilized files [T]
- `session_notes.md` → move into `progress/legacy_apprenticeship_log_archive.md`, delete file.
- `mentor_memory.md` → rewrite as pure state (learner profile facts only, seeded from `progress.json.thinking_profile`); add to `AFTER_PROBLEM_COMPLETION.md:87-103` update-candidates list (its omission is why it fossilized). Delete its hint ladder + session flow.
- `boot_instructions/instructions.txt:366-370`: rewrite corrupted tail into a proper "files the agent must never hand-edit" list.

### F14. Route mistakes to the catalog [T — protocol]
- `AFTER_PROBLEM_COMPLETION.md`: make `mistake_catalog.json` a REQUIRED update when `main_mistake` is non-trivial; every entry gets `source_problem` + `taxonomy` (A-E from `error_taxonomy.md`) + `corrected_on`. Backfill M001/M002 provenance.
- This also unblocks the dashboard "Open problem" button (F4).

---

## Phase 5 — Curriculum data quality

### F15. Dedupe the ~28 duplicate problems [M]
- Policy (DECIDED): per-duplicate skill-value test. For each dup pair, check the skills the two slots are mapped to:
  - **Different skills AND the problem genuinely exercises the second skill** (e.g. Min Window WIN-004/WIN-012, Largest Rectangle STK-010/STK-015, Two Sum CPX-001/TWO-001/HSH-005, Kth Smallest in Sorted Matrix as binary-search-on-answer BSR-010 vs heap HEP-008) → KEEP both, mark later slot `"revisit_of": "<first-ID>"`.
  - **Same skill, or second mapping is bogus** (e.g. GRF-001/GRF-007 Rotten Oranges twice in same stage; RNG-019 "Stack with Increment" mislabeled as snapshot design; DES-004/005/035/036 straight re-adds; OBS-021/OBS-025 same LC 28; TRI-008; HEP-023; MAT-005; LNK-027; REC-032; DP-100; DP-094) → DELETE the later slot.
  - Audit each of the ~28 pairs against this test during implementation; GAPS §7 has the full list.
- `validate_curriculum.py`: normalized-title duplicate check → ERROR unless `revisit_of` present (upgrade current warning).
- Update headline counts everywhere (curriculum.json header, dsa-skill-map.md, README).

### F16. Add `lc_id` + `url` to problems [M, mechanizable]
- New optional fields per problem; backfill via script/agent pass over all ~530; non-LC problems get `source: "SPOJ/GFG/custom"` + url. Fixes title ambiguity (GRF-054, DP-080) and enables one-click open from dashboard.
- Unbundle RNG-008 "My Calendar I, II, III" into separate slots (or pick III).
- `weakness_lab.py:408,464`: print real `lc_id`; until backfilled, label `#{original_number} (source index)` — never "LC".

### F17. Add missing classics [S]
- New problems (with lc_id, correct skill mapping): Rotate Image, Spiral Matrix, Set Matrix Zeroes, Game of Life, Valid Sudoku (new MAT skill "Matrix Simulation"); Majority Element (Boyer-Moore — new skill or under OBS); Valid Palindrome, Merge Sorted Array, Rotate Array, Pow(x,n), Encode/Decode Strings, Construct Binary Tree from Pre+Inorder (LC 105), BST Iterator, Subtree of Another Tree, Path Sum III, Longest Valid Parentheses, Meeting Rooms I, Surrounded Regions, Reconstruct Itinerary, Triangle, Predict the Winner; Range Sum Query 2D (2-D prefix); Longest Duplicate Substring (rolling hash). ~25 adds ≈ replaces the deleted dups, net count stays ~530-555.
- Importance retags: QUE-001 Sliding Window Maximum, TRI-002 Word Search II, REC-019 N-Queens, HEP-014 → CORE.

### F18. Real dependency DAG + stage reorder [M — DECIDED: apply now]
- Safe to apply immediately: all completed work sits in Observation (stage 1), which doesn't move; nothing gets invalidated.
- `dependency_graph.json`: replace single-chain `skill_dependencies` with 1-4 REAL prerequisites per skill (hand-author at skill level, ~90 entries; agent-draft then human review).
- Stage reorder proposal: Observation → State Construction → Constraint Maintenance → Ordered Reasoning → **Query Processing (prefix/heaps/queues)** → Decision Making → **Recursive Thinking (trees/backtracking)** → State Transition (DP) → Graph Thinking → Interval Reasoning (segment/Fenwick) → Pattern Discovery → Mathematical → Integration. (Prefix sums/queues/heaps/trees before DP; segment trees after basic trees; backtracking before DP so brute-force entry requirement is coherent.)
- Intra-skill ladder: reinforcements depend on primary; challenges depend on ≥1 reinforcement (kills the "Trapping Rain Water right after Two Sum" jump).
- Fix `SK-IE-00` dangling node: either register it in stages.json (Integration, problemless meta-skill) or remove from `skill_order`; replace `global_skill_dependencies` "Medium"/"Hard" pseudo-keys with a proper `difficulty_gates` object.
- `stages.json:415`: "11" → "12". Delete dead `module_order` from curriculum.json (confirm nothing reads it — dashboard doesn't).
- `validate_curriculum.py`: keep acyclicity; drop the one-prereq-per-skill rule; add "no Easy problem may transitively require >30 problems" sanity check.

### F19. Metadata repair sweep [S, mechanizable]
- Fix wrong `notes` (OBS-009/010, DP-083..092, TRE-026, DP-012/013, QUE-003..006) — agent pass: note must name the technique of ITS problem; verify against lc_id.
- `skills.json` name/description mismatches: SK-SC-03:239, SK-CM-05:401, SK-ST-04:945, SK-ST-11:1043, SK-GT-01:1201 — rewrite descriptions to match names; purge "PDF subsection: X" boilerplate.
- SK-QP-06 primary: HEP-016 → HEP-013 (Find Median = actual two-heaps exemplar).
- Delete all-null `secondary_skill` or start using it; rename `section` → `source_section` with comment "PDF provenance, NOT topic"; fix version 3.0/3.1 mismatch + normalize v2.1 changelog entry to object form; migrate `progress.json` history "Foundational" → "Observation" (+ validator check history stage names ∈ stages.json).

---

## Phase 6 — Weakness loop + dashboard polish (lower priority)

### F20. Weakness lab correctness [S]
- `weakness_lab.py:280-292`: skip entries starting "Resolved:"; better — migrate `weaknesses_detected` to objects `{text, status: open|resolved, source}` (template + validator + dashboard `app.js:721` reader updated together).
- Feed revision outcomes into weakness scores: FAIL events add evidence; `_shared.py:1134` weakest-skills blends latest revision recall scores with day-one solve scores (proposal: 0.6 × latest-revision avg + 0.4 × solve score when revisions exist).
- Template + validate `weaknesses_detected`/`lessons_learned`/`personal_playbook` (add to `progress_template.json` + `REQUIRED_PROGRESS_FIELDS` as optional-but-schema'd).

### F21. Dashboard: surface the good data, cut the padding [M — optional]
- Render per-revision `misconception_corrected` + per-dimension recall scores in problem modal (`app.js:2476` currently discards them).
- Fetch `dependency_graph.json` → show "unlocks next" on problem modal.
- Derive pattern cues from patterns.json fields instead of hardcoded PAT-001..009 maps (`app.js:1926,2014,2029`).
- Cut: Analytics dials/funnel/stacked bars that restate Today counts; static edge-case/complexity cards out of every problem modal (`app.js:2401`) — link once from Practice tab.
- Rolling 30-day window for showing-up chart (`app.js:2914`); debounce search (`app.js:3121`); unify badge/modal mistake counts (`app.js:890` vs `:1121`).

### F22. Misc script hygiene [T]
- `update_progress.py:376-378`: `implementation_engineering.score` → running average (or label "last session" in `dashboard.py:97-102`).
- `_shared.py:438-445`: read weights from scoring.json, delete hardcoded copy.
- `dashboard.py:76-77`: "Weakest/Strongest Skill" → "…Thinking Dimension".
- `serve_dashboard.py:42`: serve repo root is fine locally; add comment.
- `_shared.py:882`: fix `"revision_due"` fallback string to a real kind name.
- Normalize `notes` format in progress.json (objects only); template the free-form fields (`session_summary`, `variable_semantics`, `revision_material`) or fold into `lessons_learned`.

---

## Execution order & effort summary

| Phase | Fixes | Effort | Why this order |
|---|---|---|---|
| 1 Hotfixes | F1-F4 | ~half day | crash + wrong due-dates block everything |
| 2 Measurement | F5-F9 | ~1 day | scores must be trustworthy before more data accrues |
| 3 Interview sim | F10, F11, F23 | 1 day | the actual goal; do before more weeks of untimed-only practice |
| 4 Consolidation | F12-F14 | ~half day | cheap, stops drift compounding |
| 5 Curriculum | F15-F19 | 2-3 days (agent-mechanizable) | F18 apply now; do rest before reaching affected stages |
| 6 Polish | F20-F22 | as time permits | quality-of-life |

Phases 1-2 + F10 = the minimum set that makes the system trustworthy AND interview-relevant.

---

## Decisions log (2026-07-21)
1. **Mock cadence**: weekend (Sat/Sun) — one mock per weekend minimum (F10).
2. **Behavioral + system design**: OUT of scope; DSA only (F11).
3. **Dedupe**: per-pair skill-value test — keep as `revisit_of` if the second slot genuinely tests a different skill, else delete (F15).
4. **Code execution**: ADOPTED — `solutions/` + self-written asserts gate completion (F9).
5. **Stage reorder**: apply NOW — safe, only Observation stage completed (F18).
6. **Interview target date**: no fixed date — system-derived readiness estimator from pace + mastery thresholds (F23).

7. **F23 thresholds**: defaults ACCEPTED (80% CORE skills through stage 9 / 90% revision pass rate / last 3 mocks ≥ hire); tunable in `scoring.json` later.

## Implementation note
- F15 dedupe: per-pair keep/delete verdicts get made during the cleanup pass itself; obviously-redundant pairs handled directly, genuinely debatable ones listed for user review before deletion.

---

> STATUS (added on recreation, 2026-07-21): Phases 1-3 (F1-F11, F23) are IMPLEMENTED and committed on main — see `git log 12d2169..` and `plans/PHASE_EXECUTION_GUIDE.md` for what landed. Phases 4-6 + final review are pending; execute them via the standalone plans in `plans/`. Line numbers in fix descriptions reference the PRE-fix repo state (commit 12d2169). This file was accidentally deleted from the working tree and has been recreated verbatim from the planning session.
