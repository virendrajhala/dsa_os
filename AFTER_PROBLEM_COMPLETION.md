# After Problem Completion Checklist

Use this checklist after every solved problem or completed revision session.
It is the single top-level reminder for what must be synchronized before the
session is considered finished.

## 1. Capture Session Facts

Collect only facts that cannot be recomputed by scripts:

- problem id
- session type: new problem or revision
- time taken
- hint level used
- confidence before and after
- thinking breakthrough
- main mistake or misconception
- Algorithm Thinking score
- Implementation Engineering score
- interview score dimensions
- revision recall dimensions, if this was a revision

## 2. Update Learner State

Use `scripts/update_progress.py` or `make progress ARGS="..."`.

This is the source-of-truth writer for:

- `progress/progress.json`
- completed problem records
- revision state
- revision history
- current problem
- current stage
- stage mastery
- skill progress
- competency completion
- score summaries
- implementation engineering observations
- history events
- deferred learnings

Do not manually edit derived fields that the scripts recompute.

## 3. Record Genuine Learning Only

Add notes only when the session produced a real reusable discovery.

Consider whether anything should be updated in:

- `progress/progress.json`
  - learner state
  - weaknesses
  - lessons learned
  - thinking profile
  - implementation engineering
  - personal playbook
  - deferred learnings
- `mistake_catalog.json`
  - repeated mistake patterns with a clear correction
- `thinking_patterns.md`
  - reusable learner thinking patterns
- `knowledge/patterns.json`
  - stable transferable pattern models

Do not add memorized facts, generic advice, or duplicate notes.

## 4. Deferred Learnings

If the learner solved the problem but a narrow learning still needs future
evidence, create a deferred learning.

Use deferred learnings for gaps such as:

- initialization reasoning
- loop boundaries
- invariant proof
- implementation engineering
- optimization intuition
- complexity explanation
- interview communication

Deferred learnings must not change the scheduler. They are mentor context only
and should be resolved naturally by future problems, revisions, or mentor
verification.

## 5. Pattern Knowledge

Update `knowledge/patterns.json` only when a genuinely new transferable mental
model appears.

Prefer linking the problem to an existing pattern. Create a new pattern only
when the idea is reusable across multiple future problems and cannot be
represented by an existing pattern.

Patterns are curriculum knowledge, not learner progress.

## 6. Validate

After updates, run:

```bash
python3 scripts/validate_curriculum.py
python3 scripts/revision_report.py --today-only
python3 scripts/next_problem.py
```

For script or dashboard changes, also run:

```bash
python3 -m py_compile scripts/*.py
git diff --check
```

## 7. Final Sanity Check

Before ending the session, confirm:

- current problem points to the correct next problem or due revision
- revision schedule is internally consistent
- no generated or derived fields were manually edited unnecessarily
- no unrelated curriculum ordering or dependency changes were made
- validation passes
