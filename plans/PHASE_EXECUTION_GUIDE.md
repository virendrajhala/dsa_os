# Phase Execution Guide (read FIRST, applies to all phase plans)

This guide + `PHASE_4_PLAN.md` / `PHASE_5_PLAN.md` / `PHASE_6_PLAN.md` / `FINAL_REVIEW_PLAN.md` are self-contained instructions for executing the remaining fixes from `../FIXES_PROPOSAL.md` (companion audit: `../GAPS_ANALYSIS.md`). They are written so a fresh model with NO prior session context can execute them.

## What this repo is

DSA_OS — a Claude-mentor-driven DSA interview-prep system. Layers:
- `curriculum/` — curriculum.json (557 problems), stages.json (13 stages, 90 skills), dependency_graph.json, dsa-skill-map.md (hand-maintained index)
- `knowledge/` — skills.json (90 skills + SK-IE-00 meta), patterns.json (9 patterns)
- `mentor/` — mentor_protocol.md (AUTHORITATIVE teaching protocol), mock_interview_protocol.md, enhanced_mentor_protocol.md (compat pointer), error_taxonomy.md
- `progress/` — progress.json (live learner data — treat as production data), progress_template.json, scoring.json (all scoring/threshold config)
- `scripts/` — stdlib-only Python: _shared.py (core lib), update_progress.py, next_problem.py, revision_report.py, dashboard.py, validate_curriculum.py, weakness_lab.py, run_checks.py, serve_dashboard.py + test_*.py suites
- `web_dashboard/` — vanilla JS/HTML/CSS static dashboard (no build, no libraries)
- `solutions/` — learner solution files (convention: `<PROBLEM-ID>.py` with embedded asserts)
- Root docs: README.md, docs/DSA_OS_MASTER.md, AFTER_PROBLEM_COMPLETION.md, interview_playbook.md, boot_instructions/instructions.txt, mentor_memory.md, session_notes.md, thinking_patterns.md, mistake_catalog.json

## State when these plans were written (2026-07-21)

Phases 1-3 of FIXES_PROPOSAL.md are DONE, committed on main (F1-F11, F23; F5+F8 bundled). Landed behavior you MUST NOT break:
- `make test` runs 4+ unittest suites in scripts/ (test_shared, test_update_progress, test_validate_curriculum, test_run_checks, + possibly test files added by F23). `make validate` runs validate_curriculum.py (cross-file integrity INCLUDING a recompute-vs-cached derived-state check on progress.json).
- update_progress.py new-solve mode has TWO sequential gates before its single write: (1) overdue-revision gate (`--override-revisions` bypass), (2) solution-file gate via scripts/run_checks.py (`--no-code` bypass). Revision mode (`--revision-result`) requires only revision scores/result/hint level/confidence-after; enforces scoring.json `pass_minimum` (7) with `--force-pass`/`--force-pass-reason` escape. `--mode mock` records into `mock_interviews[]`. Optional `--mentor-thinking-score`/`--mentor-interview-score DIM=VALUE` args record `mentor_scores`.
- scoring.json has `hint_mastery_discount` (hint 0-2→1.0, 3-4→0.5, 5+→0) applied as a MARGIN-SCALED BAR in _shared.py (weight 0 → never masters; else effective_bar = 2.6 + (4−2.6)×(1−weight)), and a `readiness` block (F23).
- next_problem.py priority: overdue revisions > weekend mock_due > current/new work. Date logic uses injectable `on_date` params — never monkeypatch datetime.
- web_dashboard/app.js: `isoDate` formats from LOCAL date components (IST fix) — never reintroduce `toISOString()` for day-strings.

Precondition check before starting any phase: `git log --oneline -20` should show commits for F1-F11 and F23 (subjects mention: R4 mastery crash, IST off-by-one, block new solves, dashboard guard, pass minimum, hint level discount, mentor-graded scoring, solution files gate, mock-interview, playbook, readiness estimator). Run `make test && make validate` — both must pass BEFORE you start. If F23's commit is missing, stop and tell the user.

## Hard rules (from the repo owner — non-negotiable)

1. **Commits**: directly on `main`, ONE commit per fix (F12, F13+F14 may share one commit per plan instruction). Conventional format `type/scope: lowercase imperative subject ≤72 chars` + concise body, committed via HEREDOC. **ABSOLUTELY NO Co-Authored-By lines, no "Generated with" lines, no AI/agent/bot attribution anywhere.** Do not push.
2. **Never stage/commit**: `GAPS_ANALYSIS.md`, `FIXES_PROPOSAL.md`, `.superpowers/`, `__pycache__/`, scratch files. Stage files explicitly by name — never `git add -A` / `git add .`.
3. **progress/progress.json is production data.** Default: byte-identical after every task (verify with `git status`/`git diff`). Exceptions are called out explicitly per-task in the plans (e.g. F19's history-stage-name migration). Test against TEMP COPIES of it, never the live file.
4. Python: **stdlib only**. Dashboard: **vanilla JS only**, must keep working via `python3 scripts/serve_dashboard.py`; check syntax with `node --check web_dashboard/app.js` after JS edits.
5. After EVERY task: `make test` AND `make validate` must pass before committing.
6. TDD for any behavior change in scripts/: write the failing test first, then implement. Extend the existing test files/patterns (unittest, temp-dir fixtures, subprocess CLI tests).

## Per-task workflow

For each task in a phase plan:
1. Read the task section fully. Read the target files/functions before editing (line numbers in plans are approximate — locate by content).
2. Implement exactly what's specified. If something is ambiguous or contradicts what you find in the code, STOP and ask the user rather than guessing.
3. Run the task's Verify block. All commands must pass.
4. Self-review the diff (`git diff`) for scope creep, then commit with the given message template.
5. Independent review (strongly recommended): have a second model/session read the task section + `git show <commit>` and verify every "Done when" item, citing file:line. Fix anything Critical/Important it finds, re-review, then move on.

Execute tasks IN THE ORDER LISTED — later tasks assume earlier ones landed (Phase 5's order matters especially).

## Known review-carryover (feed into FINAL_REVIEW_PLAN.md)

Minor findings accepted during Phases 1-3, to triage at final review:
- F3: new-solve overdue gate ignores quarterly-maintenance entries (product-scope question); no test asserting revision-mode stays ungated.
- F10: mock verdict is holistic (soft-guarded by protocol rule 42); `--mode revision` without `--revision-result` falls through to solve path (footgun); fractional mock scores accepted; weakness tagging via "Mock: " string prefix (accepted deviation); mock record-time doesn't re-validate problem eligibility.
- F23: mock recency uses append order, not date-sorted (consistent with is_mock_due); dashboard readiness card reads persisted `skill_progress` while Python recomputes — can drift if the cached field goes stale.
