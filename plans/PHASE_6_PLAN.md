# Phase 6 Plan — Weakness Loop + Dashboard Polish (F20, F21, F22)

Read `PHASE_EXECUTION_GUIDE.md` first. Lower priority — quality-of-life. One commit per task. Prereq: Phases 4-5 landed (F20's dashboard reader changes assume F19's field renames are done; if Phase 5 was skipped, grep before assuming field names).

---

## Task F20 — Weakness lab correctness

### 20a. Structured weaknesses (the real fix)
`progress/progress.json.weaknesses_detected` is currently a map problem_id → list of STRINGS, some prefixed "Resolved: ..." and (post-F10) "Mock: ...". `scripts/weakness_lab.py` ingests every string at full severity — resolved items inflate clusters.

Migrate to objects: `{"text": "...", "status": "open"|"resolved", "source": "session"|"mock"|"revision", "resolved_on": "YYYY-MM-DD"|null}`.
- **Migration** (EXPLICITLY AUTHORIZED progress.json edit, this field only): write a one-off migration in the normal load/normalize path style — strings starting "Resolved: " → status resolved, text without the prefix; "Mock: " prefix → source mock, text without prefix; everything else → open/session. Keep backward compat in ALL readers: a plain string is treated as `{"text": s, "status": "open", "source": "session"}` so old data/hand edits never crash anything.
- Readers to update simultaneously: `scripts/weakness_lab.py` (skip status=resolved in evidence; keep counting open), `scripts/_shared.py` (anywhere weaknesses_detected is read/written — update_progress writes "Mock: " prefixed strings since F10 → now write objects with source mock), `web_dashboard/app.js` weakness-clustering reader (search `weaknesses_detected`), `progress/progress_template.json`, and validator (validate object shape, tolerate legacy strings with a warning).

### 20b. Revision outcomes feed weakness scores
- Revision FAIL events: add as weakness evidence in weakness_lab (source revision, weight comparable to main_mistake evidence).
- `_shared.py` weakest-skills computation currently uses only the original solve's thinking_score forever. Change: when a problem has revision history with recall scores, blend `0.6 × latest-revision-recall-avg (normalized to the thinking scale) + 0.4 × solve score`. Normalization: recall scores are 0-10, thinking 0-4 → scale by 0.4. Keep it in one small function with a test.
- CAUTION — recompute-vs-cache: if weakest_skills/dimension averages are CACHED in progress.json and the validator recomputes them, regenerating derived state is authorized (derived fields only); report exactly which numbers changed. If they're computed on the fly (check first), nothing to regenerate.

### 20c. Template + validate hand-authored fields
`weaknesses_detected`, `lessons_learned`, `personal_playbook` exist only in live data. Add empty defaults to progress_template.json and optional-but-schema'd validation (shape checks; absent OK).

### Verify
`make test && make validate`; `python3 scripts/weakness_lab.py` on live data — resolved items no longer drive clusters (compare its top cluster before/after in the report); dashboard weakness lab still renders (serve once).

### Commit
`fix/weakness: structured weakness entries, revision-aware scoring`

---

## Task F21 — Dashboard: surface the good data, cut the padding

All in `web_dashboard/` (vanilla JS; `node --check` after every edit; keep `isoDate` local-format discipline). Read the relevant renderer before each change — line numbers shift.

1. **Problem modal — show the instructive revision data**: the modal's revision-history rows currently show only date/result/stage/confidence. Add per-event `misconception_corrected`, `hint_level`, `notes`, and per-dimension recall scores when present (they exist in progress.json revision history events).
2. **Dependency context**: fetch `curriculum/dependency_graph.json` (NOT in the critical Promise.all — lazy-load on first modal open, with a null-safe fallback) and show in the problem modal: "Unlocks: <problems/skills that list this problem/skill as prereq>" (compute reverse edges once, cache in state).
3. **Pattern cues from data, not hardcode**: `patternQuickCues`/`simplePatternLabel`/`simplePatternHint` hardcode PAT-001..009. Derive from the fetched patterns.json fields (`recognition_signals`, `core_invariant`, `common_mistakes` — truncate sensibly). Delete the hardcoded maps; PAT-010+ then works automatically.
4. **Cut padding**: remove Analytics sub-views that only restate Today-tab counts (dials/funnel/stacked bars) — KEEP the pass-rate KPIs and the showing-up chart; remove the static edge-case/complexity cards from EVERY problem modal (keep them once in the Practice tab). Remove now-dead code and the corresponding index.html/styles.css blocks.
5. **Showing-up chart**: rolling last-30-days window (today−29..today) instead of hardcoded first-30-days; keep y-max cap but base the x-axis on the rolling window.
6. **Search**: debounce input re-render (~150ms) — it currently re-renders 8 sections per keystroke.
7. **Mistake counts**: the "Frequent mistakes" badge and the modal list use different formulas (badge: gaps+completed-mistakes; modal: slice(-12) of gaps+mistakes+catalog). Make both count the same underlying list.
8. If F23 added a readiness card and F20 changed weakness shapes — re-verify both still render.

### Verify
`node --check web_dashboard/app.js`; serve and load with real data (`python3 scripts/serve_dashboard.py`, check browser console clean or curl-fetch all data files 200); every workspace renders; problem modal shows the new revision detail on OBS-001 (it has revision history).

### Commit
`enhancement/dashboard: surface revision insights and dependencies, cut vanity views`

---

## Task F22 — Misc script hygiene

1. `scripts/update_progress.py`: `implementation_engineering.score` is last-write-wins but displayed as a standing metric → make it a running average over completions (recompute in normalize path so validator recompute matches), OR relabel in `scripts/dashboard.py` as "last session" — pick ONE, prefer the running average, and keep validator recompute consistency (this may change a cached number in progress.json → derived-field regeneration authorized; report it).
2. `scripts/_shared.py` migrate_progress_payload: hardcoded 6-dim weight table duplicating scoring.json → read from scoring.json (same pattern as hint_mastery_discount/pass_minimum).
3. `scripts/dashboard.py`: "Weakest/Strongest Skill" labels actually show thinking DIMENSIONS → rename to "Weakest/Strongest Thinking Dimension".
4. `scripts/serve_dashboard.py`: serves repo root (fine for localhost) → add a one-line comment saying so and why (relative ../progress paths).
5. `scripts/_shared.py` select_next_problem: maintenance-mode fallback string "revision_due" never matches its own kind names → fix to the real kind name (read the function; add a test pinning the maintenance path).
6. progress.json `notes`: mixed object/string formats. Normalize READERS to handle both (grep readers); update_progress should append objects `{"date": ..., "text": ...}` going forward. Do NOT rewrite historical entries.
7. Template the free-form completion fields seen in live data (`session_summary`, `conceptual_discoveries`, `variable_semantics`, `revision_material`) as documented-optional in progress_template.json + validator tolerance (warn-not-error on unknown keys, or explicitly allow these four).

### Verify
`make test && make validate`; `python3 scripts/dashboard.py` and `python3 scripts/next_problem.py` run clean on live data.

### Commit
`chore/scripts: hygiene pass (config-driven weights, labels, notes normalization)`

### Done when (whole phase)
- [ ] Three commits, validate green after each
- [ ] Any derived-field regeneration in progress.json explicitly reported with before/after values
- [ ] Dashboard verified in a real serve, not just node --check
