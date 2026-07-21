# After Problem Completion Checklist

Use this checklist after every solved problem or completed revision session.
It is the single top-level reminder for what must be synchronized before the
session is considered finished.

## 1. Capture Session Facts

Collect only facts that cannot be recomputed by scripts. A problem should not
be marked solved until the required quantitative and qualitative fields below
are available.

### Required Quantitative Fields

- problem id
- session type: new problem or revision
- time taken
- hint level used
- confidence before and after
- Algorithm Thinking score
- Implementation Engineering score
- interview score dimensions
- mentor-graded scores, if this was a scored session (see below)
- revision recall dimensions, if this was a revision

For a new problem completion, `scripts/update_progress.py` requires:

- `--problem-id`
- `--time-taken-minutes`
- `--hint-level-used`
- `--confidence-before`
- `--confidence-after`
- every `--thinking-score` dimension
- every `--interview-score` dimension
- `--algorithm-thinking-score`
- `--implementation-engineering-score`

For a revision completion, also provide:

- `--revision-result`
- every `--revision-score` dimension

### Mentor-Graded Scores (optional)

Per `mentor/mentor_protocol.md`'s Scoring Rule, the mentor grades every
rubric dimension independently, with a one-line evidence quote, before the
learner states their self-report. The completion record may carry these
under an optional `mentor_scores` block, mirroring the shape of the existing
`thinking_score` / `interview_score` fields:

```json
"mentor_scores": {
  "thinking_score": { "<dimension>": <score>, ... },
  "interview_score": { "<dimension>": <score>, ... }
}
```

- Dimension names and score ranges must match `progress/scoring.json`
  exactly (same as `thinking_score` / `interview_score`).
- Absent is fine — `mentor_scores` is optional. If present, both sub-blocks
  must be complete and in-range.
- If any dimension diverges from the learner's self-report by more than 2
  points, that divergence must be discussed and the resolution recorded in
  the qualitative notes.

### Required Qualitative Fields

- thinking breakthrough
- main mistake or misconception
- whether the solution was independently derived or hint-dependent
- core mental model learned
- primary invariant or correctness reason
- implementation lesson, if any
- edge case learned, if any
- interview takeaway
- implementation engineering observations, if any
- deferred learning, if a solved problem still leaves a narrow topic unfinished
- pattern evidence, if the problem reinforces or introduces a transferable
  thinking model

Do not invent qualitative fields. If no mistake, implementation correction,
weakness, or deferred learning was observed, record that accurately or leave
the relevant optional section unchanged according to the existing schema.

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
