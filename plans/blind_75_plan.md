# Blind 75 Track — Architecture & Implementation Plan

**Date:** 2026-08-06
**Goal:** a second, fully independent curriculum ("Blind 75") tracked and shown separately from the main 582-problem curriculum, with a track flip button on the dashboard. Same learning-path mechanics (stages → skills → scheduler → revision policy → mentor protocol); separate data files.

---

## 1. Current architecture (analysis summary)

Verified against the code on 2026-08-06.

### 1.1 Engine (Python)

- All data paths are **module-level constants** in `scripts/_shared.py:16-25`: `CURRICULUM_PATH`, `GRAPH_PATH`, `STAGES_PATH`, `SKILLS_PATH`, `PATTERNS_PATH`, `SCORING_PATH`, `PROGRESS_PATH`, `PROGRESS_TEMPLATE_PATH`, `PLAN_PATH`. Plus implicit `ROOT/solutions` at `_shared.py:2293, 2335, 2349`.
- **Single chokepoint:** `load_repository_state(explicit_progress_path=None)` (`_shared.py:207`) loads everything and returns frozen dataclass `RepositoryState` (`_shared.py:155`) with fields `curriculum, graph, stages, skills, patterns, scoring, progress, progress_path`. Only the progress path is injectable today.
- `build_dashboard_feed(state, on_date)` (`_shared.py:2256`) is pure except for 3 `ROOT/solutions` touches and `build_plan_feed → load_plan()` which falls through to the `PLAN_PATH` global (`_shared.py:2371, 2863, 2469`) — a track plan.json is unreachable without threading a path.
- **Import-time policy globals** (`_shared.py:90-96`): `REVISION_POLICY` etc. are read from `SCORING_PATH` at module import and consumed by `revision_due_entries`, `quarterly_maintenance_entries`, `apply_revision_result`, and the feed `policy` block — while `select_next_problem` reads `state.scoring`. Existing inconsistency; must become state-derived for a second track.
- All CLI scripts (`next_problem.py`, `update_progress.py`, `dashboard.py`, `weakness_lab.py`, `revision_report.py`) go through `load_repository_state(args.progress_file)` and already have `--progress-file`. `validate_curriculum.py` imports all path constants directly (`:15-31, 1720-1732`). `serve_dashboard.py:38` calls `load_repository_state()` with **no args**. `run_checks.py:22-23` owns `SOLUTIONS_DIR` (overridable `--solutions-dir`); `update_progress.py:40-45` imports it.
- **Writers:** only `update_progress.py` writes progress.json (`:594, :661, :1041`); `fetch_interview_frequency.py` writes interview_frequency.json. Nothing else writes anything.
- **Tests:** ~40 call sites in 5 test files access `_shared.CURRICULUM_PATH`-style attributes and hand-build `RepositoryState(...)`. Constants must stay as names; `RepositoryState` additions need defaults.

### 1.2 Dashboard (JS)

- **Two data paths:** `GET /api/feed` (`js/data.js:10`) **plus 10 hardcoded static-file fetches** in `js/legacy/app.js` — the 7-file `DATA` map at `app.js:9-15` (progress, scoring, curriculum, stages, skills, patterns, mistake_catalog), inline `../curriculum/interview_frequency.json` (`:421`), lazy `../curriculum/dependency_graph.json` (`:4523`), and lazy solution files via `feed.solution_files` paths (`:4346`).
- `state.datasets` + lookup Maps are built **once** in `loadData()` (`app.js:389-421`) and never rebuilt; `visibilitychange` refreshes only the feed. Stage filter options are populated once at init (`filterbar.js:81-86`).
- View state = hash router (`js/engine/router.js`), 6 workspaces in `WORKSPACE_META` (`app.js:195-224`). Track is orthogonal to workspace.
- Global controls live in the **rail footer** (`index.html:76-91`): `#rail-collapse` + `#theme-toggle` pills + `.source-card` that displays "progress.json".
- `legacy/app.js` must stay import-side-effect-free or `make test-web` breaks (`router.test.js → router.js:1 → app.js`).
- `serve_dashboard.py:27` strips the query string before matching `/api/feed`, so `?track=` is currently discarded — clean seam.

### 1.3 Workflow layer

- Mentor flow: `validate_curriculum.py` → `next_problem.py --format json` (only authority) → teaching loop → `update_progress.py` → `make test` + `make validate` → commit. Paths `progress/progress.json`, `solutions/<ID>.py`, `mistake_catalog.json` are hardcoded across `.claude/skills/mentor-session/SKILL.md`, `boot_instructions/instructions.txt`, `mentor/mentor_protocol.md`, `AFTER_PROBLEM_COMPLETION.md`.
- Learner-global knowledge (written at session end, NOT curriculum-specific): `mistake_catalog.json`, `mentor_memory.md`, `thinking_patterns.md`, `interview_playbook.md`, `knowledge/patterns.json`.

### 1.4 Blind 75 ↔ curriculum overlap (verified)

**All 75 Blind 75 problems already exist in the 582 curriculum**, matched by `lc_id`: 75 distinct curriculum ids, 34 distinct primary skills, 11 of 13 stages covered (Decision Making and Integration have zero problems). 13 skills have exactly one Blind-75 problem. Full mapping table in §6.

---

## 2. Design decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **Tracks fully independent.** Solving a problem in one track never touches the other. | User-confirmed. Simplest; matches "tracked separately". |
| D2 | **Blind 75 track is generated, not hand-written**, from the main curriculum by `lc_id` — inheriting id, title, stage, primary_skill, difficulty, notes, url. | 75/75 match; guarantees stage/skill consistency; zero manual curation drift. |
| D3 | **One engine, per-track data.** No script duplication. A `TrackPaths` bundle threads through the existing chokepoint. | `_shared.py` is 3k lines; forking it is unmaintainable. |
| D4 | Track data lives in `tracks/blind75/` (curriculum, graph, stages, skills, patterns, scoring, progress, progress_template, solutions/). Main track keeps its current locations untouched. | Zero churn on the live track; `tracks/<name>/` scales to future tracks (e.g. NeetCode 150). |
| D5 | **Shared across tracks:** `curriculum/interview_frequency.json` (slug-keyed, curriculum-independent), `mistake_catalog.json`, `mentor_memory.md`, `thinking_patterns.md`, `interview_playbook.md`. | These are learner knowledge, not curriculum state. |
| D6 | **Per-track scoring.json** (full copy with regenerated `promotion_thresholds` + `readiness`), rest of rubric identical. | `promotion_thresholds` is stage-keyed and volume-calibrated to 582; validator demands one entry per stage. Copy > merge-override machinery. |
| D7 | Module path constants **stay** (bound to main). New `TrackPaths` dataclass + `track_paths(track)` factory; `RepositoryState` gains `paths` field **with a default**. | Keeps ~40 in-process test call sites passing. |
| D8 | Dashboard flip = **pill toggle in the rail footer** (sibling of theme toggle), persisted in `localStorage["track"]`, applied via **full page reload**. | Datasets/lookups/filter options are built once and never rebuilt; reload is the honest low-risk path for a localhost tool. In-place reload = large bug surface for zero real gain. |
| D9 | Server stays **one instance serving both tracks**: `/api/feed?track=blind75`. Static files resolve by convention (`../tracks/blind75/...`). | No second port, no flag juggling. |
| D10 | **Fresh ids minted per track: `B75-001..B75-075`** (emitted order). Each problem carries `derived_from_id` (the main curriculum id) for traceability. Validator id regex relaxed to allow a digit in the prefix under `track_derived`. Solutions are per-track dirs. | User-confirmed: everything different and independent for Blind 75. |
| D11 | Blind75 curriculum ordered by **(stage_order index, then main-curriculum order)** — same learning path, compressed. `source_section` carries the classic Blind-75 category for display. | File order is the scheduler tiebreaker; stage-major order keeps e.g. all Interval problems adjacent. |
| D12 | Engine rule addition: a skill with **zero reinforcement problems** reaches mastery from its primary alone. | 13 skills have one B75 problem; without this, stage promotion is unreachable. No effect on main (validator enforces ≥1 reinforcement there). |
| D13 | Blind75 `stages.json` drops empty stages (Decision Making, Integration) from `stage_order`. | Validator requires non-empty `skills` per stage; `determine_stage` walks `stage_order`. |
| D14 | **Generate `tracks/blind75/plan.json`** mirroring the main `progress/plan.json` schema: configurable start date + week count (default 8 weeks, ~9-10 solves/week, no deloads), so the Plan workspace and Today contract card work on the B75 track. | User-confirmed: weekly targets now. |

---

## 3. Data layout

```
dsa_os/
├── curriculum/…            # main track (untouched)
├── knowledge/…             # main track skills/patterns (untouched)
├── progress/…              # main track progress/scoring/plan (untouched)
├── solutions/…             # main track solutions (untouched)
├── mistake_catalog.json    # SHARED (learner-global)
├── tracks/
│   └── blind75/
│       ├── curriculum.json          # 75 problems, generated (§6)
│       ├── dependency_graph.json    # generated: filtered skill+problem deps
│       ├── stages.json              # generated: 11 stages, filtered skills lists
│       ├── skills.json              # generated: 34 skills, re-derived roles
│       ├── patterns.json            # generated: patterns with appears_in ∩ B75, dropped if empty
│       ├── scoring.json             # copy of main + regenerated promotion_thresholds/readiness
│       ├── progress.json            # fresh (schema_version 8, empty completed)
│       ├── progress_template.json   # fresh template
│       └── solutions/               # per-track solution files
└── scripts/generate_blind75_track.py   # committed generator (re-runnable)
```

---

## 4. Engine changes (Python)

### 4.1 `scripts/_shared.py`

1. **`TrackPaths` frozen dataclass** — fields: `track, curriculum, graph, stages, skills, patterns, scoring, progress, progress_template, plan, solutions_dir`. Factory:
   ```python
   DEFAULT_TRACK = "main"
   def track_paths(track: str = DEFAULT_TRACK) -> TrackPaths:
       # "main" → the existing 9 constants + ROOT/"solutions"
       # anything else → ROOT/"tracks"/track/<file> + .../solutions
   ```
   Unknown track dir → `RepositoryError` with the list of available tracks.
2. **`RepositoryState`**: add `paths: TrackPaths | None = None` (default → tests' hand-built constructors keep working). Helper `state_paths(state)` returns `state.paths or track_paths("main")`.
3. **`load_repository_state(explicit_progress_path=None, track=DEFAULT_TRACK)`**: resolve `paths = track_paths(track)`, load every file from it, keep `explicit_progress_path` override winning over `paths.progress`, store `paths` on the state.
4. **Policy stays global — constraint documented instead.** The import-time `REVISION_POLICY` globals feed ~15 call sites across helper signatures; threading state policy through them buys nothing today because the B75 `scoring.json` copies `revision_policy` verbatim from main (only `promotion_thresholds` + `readiness` differ, and those already flow through `state.scoring`). The generator asserts the B75 `revision_policy` block equals main's. Per-track revision intervals become a follow-up refactor if ever wanted.
5. **`build_dashboard_feed`**: replace the 3 `ROOT/solutions` uses with `state_paths(state).solutions_dir`; emit `solution_files[].path` repo-relative (so `app.js:4346`'s `../${path}` keeps working for both tracks). Add `"track": paths.track` to the feed payload.
6. **`build_plan_feed(state, on_date)` / `load_plan(path=None)`**: pass `state_paths(state).plan` down so a future `tracks/blind75/plan.json` is reachable.
7. **Mastery relaxation (D12)** in `compute_skill_progress` (`:771`): if `reinforcement_problems` is empty, mastery = primary weighted score alone (no reinforcement-attempt requirement).

### 4.2 CLI scripts

- Add `--track {main,blind75}` (default `main`) to: `next_problem.py`, `update_progress.py`, `dashboard.py`, `weakness_lab.py`, `revision_report.py`, `validate_curriculum.py`. Each just forwards to `load_repository_state(args.progress_file, track=args.track)`.
- `update_progress.py`: default `--solutions-dir` becomes the track's solutions dir (explicit flag still wins).
- `validate_curriculum.py`: load all files via `track_paths(args.track)`; `--progress-file` default derived from it. Track-aware relaxations in §5.
- `run_checks.py`: no change needed (`--solutions-dir` exists); mentor flow passes the track dir.
- `serve_dashboard.py`: parse the query string on `/api/feed`; `?track=X` → `load_repository_state(track=X)`; invalid track → 400 JSON error. No server-level track flag — the server is track-agnostic per request.
- `fetch_interview_frequency.py`: unchanged (output is shared).

### 4.3 Makefile

- `TRACK ?= main`; targets `next`, `revise`, `stats`, `weakness`, `progress`, `dashboard`, `check-solution` pass `--track $(TRACK)` (usage: `make next TRACK=blind75`).
- `validate` runs **both** tracks: `validate_curriculum.py && validate_curriculum.py --track blind75`.
- Fix cosmetic: add `test-web` to `.PHONY`.

---

## 5. Generator: `scripts/generate_blind75_track.py`

One committed, re-runnable script (stdlib only, like the rest of the repo). Steps:

1. **Select** the 75 problems from `curriculum/curriculum.json` by the canonical `lc_id` list (embedded in the script, §6 table). Where an `lc_id` maps to multiple entries (revisit twins), prefer the non-`revisit_of` entry earliest in file order.
2. **curriculum.json**: order per D11; mint `id: B75-001..B75-075` in emitted order, keep `derived_from_id` = main id; keep `title, difficulty, stage, primary_skill, difficulty_weight, importance, lc_id, url, notes`; set `status: not_started`, `revision_count: 0`, `supplemental: false`, `original_number: null`, drop `revisit_of`; `source_section` = Blind-75 category. `source` block: `{origin: "Blind 75", derived_from: "curriculum/curriculum.json", track_derived: true, total_problem_count: 75}`. All skill problem refs, graph problem_dependencies keys/values, and patterns `appears_in` are remapped main-id → B75 id.
3. **Roles re-derived per skill**: within each skill's B75 problems (in emitted order) the first becomes `PRIMARY`, the rest `REINFORCEMENT`. No `CHALLENGE` roles (challenge_stage_gate then never blocks).
4. **skills.json**: the 34 referenced skills, main relative order preserved; `prerequisites` filtered to included skills; `primary_validation_problem`/`reinforcement_problems` from step 3; `challenge_problems: []`. Include meta-skill `SK-IE-00` unchanged (difficulty gates require it) — it has `subskills`, not problem refs, so it ports cleanly.
5. **stages.json**: main `stage_order` minus empty stages (→ 11), each stage's `skills` filtered to included skills; prose fields copied verbatim.
6. **dependency_graph.json**: `skill_order` = skills.json order; `skill_dependencies` filtered to included skills; `difficulty_gates` copied (`Medium/Hard: ["SK-IE-00"]`); `problem_dependencies` = main deps ∩ the 75 ids (dropping a dep = unlocks earlier — right for a fast track).
7. **scoring.json**: copy of main; regenerate `promotion_thresholds` (one entry per remaining stage; `minimum_completed_problems` = cumulative B75 problem counts through that stage, quality bars copied); `readiness.stage_scope_count` = min(current value, 11).
8. **patterns.json**: `appears_in` ∩ B75 ids per pattern; drop patterns left with empty `appears_in`; `pattern_order` updated; `skills`/`related_patterns`/`contrast_with` refs filtered to surviving entries.
9. **progress.json + progress_template.json**: fresh schema-v8 payloads — `current_stage: "Observation"`, empty `completed`, `current_problem` = first unlocked problem (computed by running the real `select_next_problem` on the generated state).
10. **Self-check**: the script ends by running the full validator (`--track blind75`) in-process and failing loudly if anything trips.

### Validator relaxations (gated on `source.track_derived: true`)

- Skip: original-number contiguity, supplemental-count reconciliation, `total >= original_problem_count` (source block shape differs).
- Id regex allows a digit in the prefix (`B75-001`); main keeps the strict `^[A-Z]{2,3}-\d{3}$`.
- Allow skills with **empty** `reinforcement_problems` (pairs with D12) and empty `challenge_problems`.
- Everything else applies unchanged — including scheduler-servability of `current_problem` and the full `normalize_progress` recompute.

---

## 6. Blind 75 → curriculum mapping (verified 75/75 by lc_id)

Ordering below is main-curriculum order; the generator re-sorts per D11 (stage-major).

| # | ID | LC | Title | B75 category | Stage | Primary skill | Diff |
|---|---|---|---|---|---|---|---|
| 1 | CPX-001 | 1 | Two Sum | Array | Observation | SK-OB-01 | Easy |
| 2 | CPX-002 | 217 | Contains Duplicate | Array | Observation | SK-OB-01 | Easy |
| 3 | OBS-001 | 53 | Maximum Subarray (Kadane's) | Array | Observation | SK-OB-03 | Medium |
| 4 | OBS-002 | 152 | Maximum Product Subarray | Array | Observation | SK-OB-03 | Medium |
| 5 | OBS-003 | 121 | Best Time to Buy and Sell Stock | Array | Observation | SK-OB-04 | Easy |
| 6 | OBS-005 | 55 | Jump Game | Dynamic Programming | Observation | SK-OB-04 | Medium |
| 7 | OBS-019 | 5 | Longest Palindromic Substring | String | Observation | SK-OB-05 | Medium |
| 8 | OBS-020 | 647 | Palindromic Substrings (count all) | String | Observation | SK-OB-05 | Medium |
| 9 | TWO-002 | 15 | Three Sum | Array | Constraint Maintenance | SK-CM-01 | Medium |
| 10 | TWO-004 | 11 | Container With Most Water | Array | Constraint Maintenance | SK-CM-01 | Medium |
| 11 | WIN-001 | 3 | Longest Substring Without Repeating Characters | String | Constraint Maintenance | SK-CM-02 | Medium |
| 12 | WIN-004 | 76 | Minimum Window Substring | String | Constraint Maintenance | SK-CM-02 | Hard |
| 13 | WIN-011 | 424 | Longest Repeating Character Replacement | String | Constraint Maintenance | SK-CM-03 | Medium |
| 14 | HSH-001 | 242 | Valid Anagram | String | State Construction | SK-SC-01 | Easy |
| 15 | HSH-002 | 49 | Group Anagrams | String | State Construction | SK-SC-01 | Medium |
| 16 | HSH-006 | 128 | Longest Consecutive Sequence | Graph | State Construction | SK-SC-02 | Medium |
| 17 | ORD-001 | 56 | Merge Intervals | Interval | Interval Reasoning | SK-IR-02 | Medium |
| 18 | ORD-002 | 57 | Insert Interval | Interval | Interval Reasoning | SK-IR-02 | Medium |
| 19 | ORD-003 | 253 | Meeting Rooms II (min conference rooms) | Interval | Interval Reasoning | SK-IR-02 | Medium |
| 20 | ORD-004 | 435 | Non-overlapping Intervals | Interval | Interval Reasoning | SK-IR-02 | Medium |
| 21 | BSR-001 | 153 | Find Minimum in Rotated Sorted Array | Array | Ordered Reasoning | SK-OR-03 | Medium |
| 22 | BSR-002 | 33 | Search in Rotated Sorted Array | Array | Ordered Reasoning | SK-OR-03 | Medium |
| 23 | PFX-004 | 238 | Product of Array Except Self | Array | Query Processing | SK-QP-01 | Medium |
| 24 | LNK-002 | 141 | Linked List Cycle Detection | Linked List | State Construction | SK-SC-04 | Easy |
| 25 | LNK-006 | 143 | Reorder List (L0→Ln→L1→Ln-1) | Linked List | State Construction | SK-SC-04 | Medium |
| 26 | LNK-007 | 206 | Reverse a Linked List | Linked List | State Construction | SK-SC-05 | Easy |
| 27 | LNK-011 | 21 | Merge Two Sorted Lists | Linked List | State Construction | SK-SC-05 | Easy |
| 28 | LNK-012 | 23 | Merge K Sorted Lists | Linked List | State Construction | SK-SC-05 | Hard |
| 29 | LNK-015 | 19 | Remove Nth Node from End | Linked List | State Construction | SK-SC-05 | Medium |
| 30 | STK-001 | 20 | Valid Parentheses | String | Constraint Maintenance | SK-CM-04 | Easy |
| 31 | HEP-004 | 347 | Top K Frequent Elements | Heap | Query Processing | SK-QP-05 | Medium |
| 32 | HEP-013 | 295 | Find Median from Data Stream | Heap | Query Processing | SK-QP-06 | Hard |
| 33 | TRE-004 | 102 | Binary Tree Level Order Traversal | Tree | Recursive Thinking | SK-RT-01 | Medium |
| 34 | TRE-011 | 104 | Maximum Depth of Binary Tree | Tree | Recursive Thinking | SK-RT-02 | Easy |
| 35 | TRE-015 | 100 | Same Tree | Tree | Recursive Thinking | SK-RT-02 | Easy |
| 36 | TRE-017 | 226 | Invert Binary Tree | Tree | Recursive Thinking | SK-RT-02 | Easy |
| 37 | TRE-022 | 124 | Binary Tree Maximum Path Sum | Tree | Recursive Thinking | SK-RT-02 | Hard |
| 38 | TRE-026 | 297 | Serialize and Deserialize Binary Tree | Tree | Recursive Thinking | SK-RT-03 | Hard |
| 39 | BST-001 | 98 | Validate Binary Search Tree | Tree | Recursive Thinking | SK-RT-04 | Medium |
| 40 | BST-002 | 230 | Kth Smallest Element in a BST | Tree | Recursive Thinking | SK-RT-04 | Medium |
| 41 | BST-003 | 235 | Lowest Common Ancestor of BST | Tree | Recursive Thinking | SK-RT-04 | Easy |
| 42 | TRI-001 | 208 | Implement Trie (Prefix Tree) | Tree | Recursive Thinking | SK-RT-05 | Medium |
| 43 | TRI-002 | 212 | Word Search II (Trie + DFS) | Tree | Recursive Thinking | SK-RT-05 | Hard |
| 44 | TRI-003 | 211 | Design Add and Search Words Data Structure | Tree | Recursive Thinking | SK-RT-05 | Medium |
| 45 | GRF-002 | 200 | Number of Islands | Graph | Graph Thinking | SK-GT-03 | Medium |
| 46 | GRF-005 | 417 | Pacific Atlantic Water Flow | Graph | Graph Thinking | SK-GT-03 | Medium |
| 47 | GRF-017 | 133 | Clone Graph | Graph | Graph Thinking | SK-GT-04 | Medium |
| 48 | GRF-018 | 207 | Course Schedule (cycle detection) | Graph | Graph Thinking | SK-GT-04 | Medium |
| 49 | GRF-020 | 323 | Number of Connected Components in Undirected Graph | Graph | Graph Thinking | SK-GT-04 | Medium |
| 50 | GRF-021 | 261 | Graph Valid Tree | Graph | Graph Thinking | SK-GT-04 | Medium |
| 51 | GRF-027 | 269 | Alien Dictionary | Graph | Graph Thinking | SK-GT-05 | Hard |
| 52 | DP-003 | 139 | Word Break | Dynamic Programming | State Transition | SK-ST-02 | Medium |
| 53 | DP-004 | 91 | Decode Ways | Dynamic Programming | State Transition | SK-ST-03 | Medium |
| 54 | DP-005 | 300 | Longest Increasing Subsequence (O(n log n)) | Dynamic Programming | State Transition | SK-ST-04 | Medium |
| 55 | DP-014 | 70 | Climbing Stairs | Dynamic Programming | State Transition | SK-ST-12 | Easy |
| 56 | DP-015 | 198 | House Robber | Dynamic Programming | State Transition | SK-ST-12 | Medium |
| 57 | DP-016 | 213 | House Robber II (circular) | Dynamic Programming | State Transition | SK-ST-12 | Medium |
| 58 | DP-021 | 322 | Coin Change (minimum coins) | Dynamic Programming | State Transition | SK-ST-12 | Medium |
| 59 | DP-029 | 62 | Unique Paths | Dynamic Programming | State Transition | SK-ST-01 | Medium |
| 60 | DP-035 | 1143 | Longest Common Subsequence | Dynamic Programming | State Transition | SK-ST-01 | Medium |
| 61 | DP-052 | 377 | Combination Sum IV | Dynamic Programming | State Transition | SK-ST-13 | Medium |
| 62 | REC-018 | 79 | Word Search | Matrix | Pattern Discovery | SK-PD-04 | Medium |
| 63 | MAT-015 | 191 | Number of 1 Bits (Hamming Weight) | Binary | Mathematical Thinking | SK-MT-03 | Easy |
| 64 | MAT-016 | 338 | Counting Bits (0 to n) | Binary | Mathematical Thinking | SK-MT-03 | Easy |
| 65 | MAT-017 | 190 | Reverse Bits | Binary | Mathematical Thinking | SK-MT-03 | Easy |
| 66 | MAT-018 | 268 | Missing Number | Binary | Mathematical Thinking | SK-MT-03 | Easy |
| 67 | MAT-019 | 371 | Sum of Two Integers (without + operator) | Binary | Mathematical Thinking | SK-MT-03 | Medium |
| 68 | MAT-023 | 48 | Rotate Image | Matrix | State Construction | SK-SC-07 | Medium |
| 69 | MAT-024 | 54 | Spiral Matrix | Matrix | State Construction | SK-SC-07 | Medium |
| 70 | MAT-025 | 73 | Set Matrix Zeroes | Matrix | State Construction | SK-SC-07 | Medium |
| 71 | TWO-012 | 125 | Valid Palindrome | String | Constraint Maintenance | SK-CM-01 | Easy |
| 72 | HSH-012 | 271 | Encode and Decode Strings | String | State Construction | SK-SC-01 | Medium |
| 73 | TRE-028 | 105 | Construct Binary Tree from Preorder and Inorder Traversal | Tree | Recursive Thinking | SK-RT-03 | Medium |
| 74 | TRE-029 | 572 | Subtree of Another Tree | Tree | Recursive Thinking | SK-RT-02 | Easy |
| 75 | ORD-016 | 252 | Meeting Rooms | Interval | Interval Reasoning | SK-IR-02 | Easy |

Stage coverage: Observation 8, Constraint Maintenance 7, State Construction 13, Ordered Reasoning 2, Query Processing 3, Recursive Thinking 14, Pattern Discovery 1, Graph Thinking 7, State Transition 10, Interval Reasoning 5, Mathematical Thinking 5. (Decision Making, Integration: dropped.)

---

## 7. Server + dashboard changes

### 7.1 `serve_dashboard.py`

- Parse `?track=` on `/api/feed` (`urllib.parse.parse_qs` on the already-split query). `track=blind75` → `load_repository_state(track="blind75")`; unknown → 400 with JSON `{error}`. Default `main`. Static serving unchanged (repo root already covers `tracks/`).

### 7.2 JS track resolution (all inside functions — no import-side-effects)

- New tiny module `js/engine/track.js`:
  ```js
  export const TRACKS = { main: {label: "582 Curriculum", short: "582"},
                          blind75: {label: "Blind 75", short: "B75"} };
  export function activeTrack() { /* localStorage["track"], validated, default "main" */ }
  export function setTrack(t) { localStorage.setItem("track", t); location.reload(); }
  export function trackFile(name) { /* "curriculum.json" → "../curriculum/curriculum.json" (main)
                                       or "../tracks/blind75/curriculum.json";
                                       skills/patterns/scoring/progress map to their main homes */ }
  ```
- `js/data.js`: fetch `/api/feed?track=${activeTrack()}`.
- `js/legacy/app.js`: `DATA` map (`:9-15`) built via `trackFile(...)` for the 6 per-track files; `mistake_catalog.json` stays fixed. Inline `dependency_graph.json` (`:4523`) → `trackFile`. `interview_frequency.json` (`:421`) stays fixed (shared).
- Solution files (`:4346`) need no change — server-provided repo-relative paths (§4.1.5).

### 7.3 Flip UI

- **Rail footer** (`index.html:76-91`): new pill button `#track-toggle` between `#rail-collapse` and `#theme-toggle`, showing the *other* track's short label ("B75" / "582"), `title` = "Switch to <label>". Click → `setTrack(other)` → reload. Styled like `.rail-collapse` (`css/components/sidebar.css:106-123`); visible in collapsed rail too (icon-only, like theme toggle).
- **Active-track echo:** `.source-card` label shows the active track name + its progress file; `#workspace-eyebrow` prefixed with the track short label on non-main track only (main stays visually identical to today).
- Keyboard: palette action "Switch track" registered alongside the theme action in `main.js:32-36`.

---

## 8. Workflow layer (mentor)

- `.claude/skills/mentor-session/SKILL.md`: PHASE 0 addition — determine track: explicit user mention ("blind 75", "b75") wins; else ask once at session start (default main). No marker file — flow stays identical to today, just with `--track <t>` appended to every script call; solutions path becomes `tracks/blind75/solutions/<ID>.py` on the B75 track; commit scope adds `tracks/blind75/`. Commit style: `progress/b75: record B75-001 completion`.
- `boot_instructions/instructions.txt` + `AFTER_PROBLEM_COMPLETION.md`: same path/flag substitutions, stated once as a "track resolution" preamble instead of editing every mention (docs describe the main paths; a short section defines the B75 substitutions).
- Shared learner artifacts (`mistake_catalog.json`, `mentor_memory.md`, `thinking_patterns.md`, `interview_playbook.md`) written exactly as today from both tracks.

---

## 9. Testing

- **New `scripts/test_track_paths.py`**: `track_paths()` resolution (main vs blind75 vs unknown), `load_repository_state(track="blind75")` loads the generated files, feed carries `"track"`, solutions paths point into `tracks/blind75/solutions`.
- **`test_dashboard_feed.py`**: extend the live-server test (`:160-195`) with `GET /api/feed?track=blind75` (200 + `track: "blind75"`) and `?track=nope` (400).
- **Generator test**: run generator into a temp dir, assert 75 problems / 34 skills / 11 stages, then run the full validator on the output.
- **Validator**: `make validate` covers both tracks (§4.3).
- **JS**: existing suite must stay green (track.js is import-side-effect-free); add `js/tests/track.test.js` for `trackFile()` mapping + `activeTrack()` validation (localStorage guarded inside functions).
- **Manual walk**: `make web-dashboard`, flip both directions, all 6 workspaces render, no console errors, both themes.

---

## 10. Implementation phases

Each phase ends green on `make validate && make test` before the next starts.

**Phase 1 — engine plumbing** (no behavior change on main)
1. `TrackPaths` + `track_paths()` + `RepositoryState.paths` (default None) + `load_repository_state(track=)`.
2. Thread paths through feed solutions + plan (`build_dashboard_feed`, `build_plan_feed`, `load_plan`).
3. Policy state-derived (§4.1.4).
4. `--track` flags on the 6 CLI scripts; Makefile `TRACK`.
5. `test_track_paths.py` (main-track cases only at this point).

**Phase 2 — generator + blind75 data**
6. Validator `track_derived` relaxations + mastery relaxation (D12).
7. `generate_blind75_track.py`; commit generated `tracks/blind75/*`.
8. `make validate` validates both tracks; generator test.
9. Smoke: `python3 scripts/next_problem.py --track blind75` serves CPX-001 (or first unlocked).

**Phase 3 — server + dashboard flip**
10. `?track=` on `/api/feed` + feed `track` field + test_dashboard_feed cases.
11. `js/engine/track.js`, `data.js`, `app.js` DATA-map parameterization.
12. `#track-toggle` pill + source-card/eyebrow echo + palette action + CSS.
13. `track.test.js`; full manual walk both tracks × both themes.

**Phase 4 — mentor workflow**
14. SKILL.md / instructions.txt / AFTER_PROBLEM_COMPLETION.md track resolution sections.
15. End-to-end dry run: one full B75 mentor session (validate → next → solve → update → tests → commit).

---

## Unresolved questions

1. B75 order: stage-major compressed path (D11) ok, or strict Blind-75 category order (Array→Binary→DP…)?
2. Toggle flip = full page reload — acceptable?
3. Reuse main problem ids (`OBS-001`) in B75 (D10), or mint `B75-001..075`?
4. `tracks/blind75/plan.json` weekly targets now or skip (D14)?
5. Mentor track pick: `.active_track` marker + ask-once ok, or always explicit per session?
6. Commit generated `tracks/blind75/*` files to git (yes assumed)?

## Decisions confirmed (2026-08-06)

1. Order: stage-major compressed path (D11).
2. Flip: full page reload — approved.
3. Ids: mint `B75-001..B75-075`, fully independent (D10 updated above).
4. `tracks/blind75/plan.json`: generate now (D14 updated above).
5. Mentor: same flow as today, `--track` appended; explicit mention wins, else ask once at session start.
6. Generated `tracks/blind75/*`: committed to git.
