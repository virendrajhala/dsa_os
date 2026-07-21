# Final Whole-Branch Review Plan

Run AFTER Phases 4-6 are complete. Use the most capable model available for this — it is the last quality gate. The reviewer must be a FRESH context (not the model that implemented the phases).

## Scope

Everything from base commit `12d2169` (pre-fix state, message "enhancement/dashboard: improve dashboard scanability") to HEAD. Generate the review input:
```
git log --oneline 12d2169..HEAD
git diff --stat 12d2169..HEAD
git diff -U10 12d2169..HEAD > /tmp/full-branch.diff   # large; read in chunks
```

## Reviewer instructions (give these to the review model verbatim)

You are reviewing the complete implementation of `FIXES_PROPOSAL.md` (root of repo) against what actually landed. Read FIXES_PROPOSAL.md first — every F-item and every entry in its Decisions log is a requirement. Then review the diff.

### Part 1 — Requirements sweep
For each fix F1-F23 (F5+F8 bundled): does the landed code/docs match the spec AND the decisions log? Spot-check by reading the current files, not just the diff. Verdict per fix: ✅ / ❌ (what's missing) / ⚠️ (can't verify — say what to check manually).

### Part 2 — Cross-fix integration risks (the things per-task reviews can't see)
1. **Gate stack ordering** in update_progress.py: overdue-revision gate → code-execution gate → single write; `--mode mock` bypasses both correctly (mocks aren't solves); revision mode gated by neither. Trace main() end-to-end.
2. **Config coherence** in scoring.json: hint_mastery_discount, pass_minimum, readiness, hint_levels descriptions (must match mentor_protocol.md ladder verbatim post-F12), weights — one source each, no orphan or duplicated constants left in Python.
3. **Curriculum consistency post-Phase-5**: run `make validate`; additionally verify by script: every skills.json problem ID exists in curriculum.json and vice versa; dependency_graph nodes == curriculum problems; stage_order identical across files; readiness scope (first 9 stages) ends at Graph Thinking; no problem in progress.json was deleted/re-ID'd.
4. **Dashboard/data contract**: serve the dashboard, load every workspace with real data, check the browser console (or at minimum: node --check, then curl every fetched data file for 200 + JSON-parse each). Fields renamed in F19 (section→source_section, secondary_skill removed) and reshaped in F20 (weaknesses_detected objects) must have zero stale readers: grep app.js and scripts/ for the old names.
5. **Protocol non-contradiction post-F12**: grep for a second hint ladder, a second blueprint, "Name the pattern" — all must be gone. mock_interview_protocol and mentor_protocol must not contradict on what's suspended during mocks.
6. **Tests actually cover the risky paths**: R4→MASTERED transition, revision-first gate, code gate, pass_minimum + force-pass, hint-discount margin bar (3.3 boundary), mock weekend-window (prev-weekend doesn't suppress), readiness projection math. Run `make test` yourself and paste the summary.

### Part 3 — Accepted-minors triage
These were consciously deferred during earlier reviews. For each: fix-now (small + worth it), ticket-for-later, or fine-as-is — with one line of reasoning:
- F3: quarterly-maintenance entries don't block new solves (only regular overdue revisions do); no test pinning revision-mode-is-ungated.
- F10: `--mode revision` without `--revision-result` falls through to the solve path (footgun); fractional mock scores accepted though rubric is integer-anchored; mock record-time doesn't validate problem eligibility (scheduler is the enforcement point); holistic verdict soft-guarded only by protocol rule.
- Anything listed as "contentious pairs" (F15) or "unresolved lc_ids" (F16) in the phase reports → compile into one user-decision list.

### Part 4 — Output
Ranked findings (Critical / Important / Minor) with file:line, then an overall verdict: mergeable as-is / needs fixes (list). Keep prose tight; every claim cites evidence.

## After the review

- Fix all Critical/Important findings (one fix commit per logical group, same commit rules as PHASE_EXECUTION_GUIDE.md), re-run the affected checks, and have the reviewer confirm.
- Present the Part-3 user-decision list to the repo owner — do NOT silently decide contentious deletions.
- Suggested closing step (ASK THE OWNER FIRST — do not do it unprompted): commit GAPS_ANALYSIS.md, FIXES_PROPOSAL.md and plans/ as documentation (`docs/audit: record gaps analysis, fix plan and phase plans`), since they document why the system is shaped this way.
- Final state check: `make test && make validate && python3 scripts/next_problem.py && python3 scripts/revision_report.py && python3 scripts/dashboard.py` all clean.
