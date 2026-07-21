# Phase 4 Plan — Protocol Consolidation (F12, F13, F14)

Read `PHASE_EXECUTION_GUIDE.md` first. Effort: ~half day. Two commits: one for F12, one for F13+F14.

Goal: `mentor/mentor_protocol.md` becomes the ONLY copy of every protocol mechanism; fossilized files are repaired or retired; mistakes get routed to the catalog with provenance. This is documentation surgery — no script behavior changes, but `make validate` must keep passing.

---

## Task F12 — Single source of truth for protocol content

### Background (why)
The Implementation Blueprint is duplicated in 5 files, the revision gates and 9-item post-code review in 4, and there are THREE divergent hint ladders all claiming to match `progress/scoring.json.hint_levels`. Drift is already visible. Also `docs/DSA_OS_MASTER.md` has a session-flow step "Name the pattern" that directly contradicts mentor_protocol.md Golden Rule 1 ("Never reveal the algorithm before the student discovers the governing invariant") and boot rule 13.

### Steps (locate content by TEXT, not line numbers — files have been edited since the audit)

1. **`mentor/enhanced_mentor_protocol.md`** → reduce to a ~5-line pointer file: title, "This file exists only for backward compatibility; the authoritative protocol is `mentor/mentor_protocol.md`", nothing else. Delete its duplicated Implementation Blueprint / review-order / revision-gate content entirely.
2. **`docs/DSA_OS_MASTER.md`**:
   - Its "Session Flow" numbered list (a ~14-step flow containing a step like "Name the pattern"): replace the whole list with 2-3 sentences + a link: "The session flow is defined by the state machine in `mentor/mentor_protocol.md` — that file is authoritative." The "Name the pattern" step must be GONE.
   - Its "Hint System"/hint-ladder section (levels described as hint TYPES, e.g. "Example Hint", "Structure Hint"): replace with a link to the hint ladder in mentor_protocol.md.
   - Its Implementation Blueprint copy: replace with a link.
   - KEEP: philosophy, mission, scoring-rubric rationale, revision strategy narrative, Interview Communication Rules (the playbook links to those — do not remove or move them).
3. **`README.md`**: find its Implementation Blueprint copy (a bulleted State/Initialization/Loop/... block) → replace with one line linking mentor_protocol.md. Keep the rest of README's ops content.
4. **`templates/case_file_template.md`**:
   - Field "Chosen pattern:" → "Governing invariant (in your own words):" (pattern-naming contradicts the protocol).
   - Header fields `Original Number` / `Module` (stale pre-v3.0 schema) → replace with `Primary skill` (matching curriculum.json's `primary_skill`).
   - Its embedded blueprint short-form may stay (it is a fill-in TEMPLATE, not documentation) — but add a comment line: `<!-- blueprint structure defined in mentor/mentor_protocol.md; keep in sync -->`.
5. **ONE hint ladder**: `mentor/mentor_protocol.md`'s ladder (levels = amount of help consumed) is canonical. Rewrite the per-level `description` strings in `progress/scoring.json.hint_levels` to match mentor_protocol.md's level semantics VERBATIM (short phrases are fine; same meaning per level 0-7). Delete the hint-ladder variant in `mentor_memory.md` (that file is further handled in F13 — for THIS task just ensure no second ladder survives anywhere; `grep -rn "hint" --include="*.md" | grep -in "level"` to hunt).
6. Check `scripts/` for anything asserting on hint_levels description text (`grep -rn "hint_levels" scripts/`) — validate_curriculum.py validates the structure of scoring.json; make sure your description edits don't break its checks.

### Verify
```
make test && make validate
grep -rn "Name the pattern" docs/ mentor/ README.md   # → no hits
grep -rln "What does each state variable represent" --include="*.md" .   # → mentor_protocol.md and (allowed) templates/case_file_template.md ONLY
```

### Commit
`docs/protocol: consolidate blueprint, hint ladder and session flow into mentor_protocol`
Body: one line each — pointer-ized enhanced protocol, MASTER now links, removed pattern-naming step, single hint ladder synced to scoring.json.

### Done when
- [ ] enhanced_mentor_protocol.md ≤ ~8 lines, pure pointer
- [ ] DSA_OS_MASTER.md has no session-flow list, no hint ladder, no blueprint copy; still has philosophy + communication rules
- [ ] "Name the pattern" appears nowhere
- [ ] README has no blueprint copy
- [ ] case_file_template has Governing invariant + Primary skill fields
- [ ] scoring.json hint_levels descriptions match mentor_protocol.md ladder
- [ ] make test + make validate pass

---

## Task F13 — Kill/repair fossilized files

1. **`session_notes.md`** (root): stale session-1 retrospective with a pre-blueprint 9-step flow, referenced by nothing. Append its content under a dated "archived" heading at the END of `progress/legacy_apprenticeship_log_archive.md`, then `git rm session_notes.md`.
2. **`mentor_memory.md`**: currently ~90% process duplication (session flow, hint policy) violating mentor_protocol.md's own rule that this file holds STATE not process. Rewrite from scratch as a pure student-profile file:
   - Header: "# Mentor Memory — student profile (state only; process lives in mentor/mentor_protocol.md)"
   - Sections: Strengths / Gaps / Preferred reasoning patterns / Recurring failure modes / Notes for next session.
   - Seed the content from `progress/progress.json` → `thinking_profile` (read it; summarize strengths/gaps/failure_modes it contains as prose bullets). Do NOT invent facts not present in the data.
   - Delete its session flow, hint ladder, review policy entirely.
3. **`AFTER_PROBLEM_COMPLETION.md`**: in its update-candidates section (the list naming progress.json / mistake_catalog / thinking_patterns / patterns.json / interview_playbook.md), ADD `mentor_memory.md` with one line: "update when the session revealed a new strength/gap/failure mode — keep it state-only." (This omission is why the file fossilized.)
4. **`boot_instructions/instructions.txt`**: the file tail (last ~5 lines) is corrupted fragment text (mentions "❌ mastered_skills … dont touch manually only let the agent touch andmodify them"). Replace the corrupted tail with a proper final rule, numbered to follow the previous rule, e.g.:
   ```
   RULE N — FILES THE AGENT MUST NEVER HAND-EDIT
   The following are derived/production state. They change ONLY through scripts/update_progress.py:
   - progress/progress.json: scores, mastered_skills, skill_progress, stage_mastery, revision state
   Hand-editing them desynchronizes the recompute-vs-cache validator and corrupts scheduling.
   ```
   Keep the file's existing numbering/format conventions (read the surrounding rules first).

## Task F14 — Route mistakes to the catalog

1. **`AFTER_PROBLEM_COMPLETION.md`**: where it describes updating `mistake_catalog.json`, upgrade it from optional to REQUIRED whenever the session's `main_mistake` is non-trivial (define: anything beyond a pure typo). Specify the entry shape:
   ```json
   {"id": "M00N", "title": "...", "symptom": "...", "fix": "...",
    "source_problem": "OBS-00X", "taxonomy": "B", "corrected_on": "YYYY-MM-DD"}
   ```
   `taxonomy` = one letter A-E per `mentor/error_taxonomy.md` (A pattern / B state / C transition / D implementation / E syntax).
2. **Backfill `mistake_catalog.json`**: M001 and M002 lack provenance. Read `progress/legacy_apprenticeship_log_archive.md` and `progress/progress.json` completion records (main_mistake fields) to attribute them to a source problem + date + taxonomy letter. If genuinely unattributable, set `"source_problem": null, "note": "pre-migration, provenance unknown"` — do NOT invent. M003 already has provenance; add its missing `taxonomy` letter (infer from its text).
3. The dashboard already renders an "Open problem" button when `source_problem` is present (landed in F4) — no JS work needed. Verify by serving the dashboard once and opening the mistakes modal if convenient (optional).

### Verify (F13+F14)
```
make test && make validate
test ! -f session_notes.md && echo gone
python3 - <<'EOF'
import json; d=json.load(open('mistake_catalog.json'))
for m in d if isinstance(d,list) else d.get('mistakes',d):
    print(m)
EOF
grep -n "mentor_memory" AFTER_PROBLEM_COMPLETION.md   # → present in update list
```
(Adapt the JSON snippet to the file's real top-level shape — read it first.)

### Commit (one commit for F13+F14)
`chore/docs: retire fossil files, route mistakes to catalog with provenance`

### Done when
- [ ] session_notes.md deleted, content archived in legacy log
- [ ] mentor_memory.md is state-only, seeded from thinking_profile, listed in AFTER_PROBLEM_COMPLETION update candidates
- [ ] instructions.txt tail is a clean never-hand-edit rule
- [ ] AFTER_PROBLEM_COMPLETION mandates catalog entries with source_problem/taxonomy/corrected_on
- [ ] M001/M002 backfilled (or explicitly marked unattributable), M003 has taxonomy
- [ ] make test + make validate pass
