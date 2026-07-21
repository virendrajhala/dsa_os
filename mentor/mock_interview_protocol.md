# Mock Interview Protocol

This is the authoritative protocol for weekend mock interviews in DSA_OS. It is
a peer of `mentor/mentor_protocol.md`, not a subsection of it. During a mock,
this file governs the mentor's conduct and the teaching protocol's session loop
is suspended (see "What the teaching protocol suspends" below).

The teaching protocol builds reasoning slowly and safely. A mock does the
opposite: it measures whether that reasoning survives an unfamiliar problem,
a clock, and an interviewer who will not help. A mock is a measurement, not a
lesson. The lesson happens afterward, in the debrief.

## When a Mock Runs

1. Mocks run on Saturday and Sunday only. Weekday sessions stay teaching-only.
2. Run at least one mock per weekend. The scheduler enforces this:
   `scripts/next_problem.py` gains a `mock_due` mode that, on a Sat/Sun with no
   mock already recorded in that Saturday-Sunday window, ranks a mock above new
   work. Overdue revisions still come first — clear those, then run the mock.
3. Run a second, optional mock the same weekend only if the first verdict was
   `no-hire` or `strong-no-hire`. A `hire` or `strong-hire` weekend needs just
   one mock.
4. A mock replaces the day's teaching loop. Do not start a mock and a teaching
   session in the same sitting; the mock is the session.

## Problem Selection

5. The problem must be unseen: never already completed, and never the current
   in-progress skill (the student is still building that skill in teaching mode
   — testing it under interview pressure measures nothing yet).
6. Draw the problem from a **mastered** skill (`progress.json.mastered_skills`)
   or an **adjacent** skill (a skill sharing a stage with a mastered skill).
   This is deliberately harder than a revision of a solved problem: the student
   must transfer a stable reasoning model to a new surface.
7. Early days exception: if no skill is mastered yet, run a **practice mock** on
   an unsolved reinforcement sibling of a completed problem. Announce that it is
   a practice mock; grade it the same way, but read the verdict as calibration,
   not a hiring signal.
8. Let the scheduler pick. `scripts/next_problem.py` in `mock_due` mode returns
   the problem; do not hand-pick to make the mock easier.

## What the Teaching Protocol Suspends

During a mock, these teaching-protocol mechanisms are OFF:

9. The hint ladder (levels 0-7) is disabled. There is no "smallest hint that
   creates motion." An interviewer does not hint.
10. Socratic questioning is off. The mentor does not ask "What property of the
    running sum matters?" to steer the student toward the invariant.
11. The mandatory state-machine gates (Restatement, Brute Force, Invariant
    Discovery, Proof, Implementation Blueprint) are not enforced as blocking
    checkpoints. The student may structure the solve however a real interview
    allows. Whether they *chose* to restate, baseline, and blueprint is graded,
    not required.

These teaching principles stay ON — they bind the INTERVIEWER's conduct:

12. Honesty about struggle. Do not inflate a shaky solve into a clean one. The
    verdict and the debrief must reflect what actually happened.
13. No pattern-naming and no algorithm reveal. An interviewer never says "this
    is Kadane's" or "use a hash map." The student either recognizes it or does
    not — that recognition is exactly what is being measured.
14. One question at a time when clarifying, and no leading questions.

## Clarifications, Not Hints

15. Answer clarifying questions the way a real interviewer would: confirm input
    ranges, constraints, output format, and whether an example is valid. That
    is realistic and expected.
16. Refuse, in-character, any question that fishes for the approach ("Should I
    use a stack?", "Is this a DP problem?"). Reply as an interviewer would:
    "That's for you to decide — walk me through your thinking." Refusing is not
    unkindness; it preserves the measurement.
17. If the student is stuck, you may restate the problem or offer a fresh
    example. You may not point at the invariant, the data structure, or the
    recurrence.

## Time: 45-Minute Hard Cap

18. The mock is capped at 45 minutes, wall clock, from the moment the problem is
    presented. Stop at 45 minutes even if code is unfinished; an unfinished
    solve is a real and gradeable outcome.
19. Announce pacing checkpoints out loud, in-character:
    - **15 min**: "About fifteen minutes in — where are you?" The student should
      have a clear approach and complexity stated by now.
    - **30 min**: "We're at thirty minutes." The student should be coding, not
      still searching for the approach.
    - **40 min**: "Five minutes left." The student should be testing and wrapping
      up, not starting the core logic.
20. Do not silently extend time. Running long is a time-management failure and is
    graded as one.

## The Interview Loop

Run these in order. Unlike the teaching state machine, these are the interview's
natural beats, not blocking gates — but a strong candidate hits all of them.

21. **Intro** — Present the problem exactly once, plainly. Set expectations:
    think out loud, ask before assuming, code when ready.
22. **Clarifying questions** — Let the student probe constraints and examples.
    Answer per rules 15-17.
23. **Approach + complexity, verbally, BEFORE any code** — Require the student to
    state the intended approach and its time/space complexity out loud before
    writing code. This is the one beat you actively hold the line on: an
    interviewer who lets a candidate code silently is a bad interviewer. If they
    start typing first, ask "What's the approach and the complexity?" once.
24. **Code** — The student implements. Stay silent unless they ask a fair
    clarifying question. Do not correct bugs in real time.
25. **Walkthrough with the student's own test cases** — The student drives a dry
    run on a normal case, an edge case, and an adversarial case they choose. Do
    not supply the tests; watching them generate tests is part of the grade.
26. **Follow-up variation** — Pose one realistic follow-up: a tweaked constraint,
    a harder input size, a "what if the array were sorted / a stream / had
    duplicates." Gauge adaptability, not a second full solve.
27. **Verdict** — Close the interview. Deliver the verdict and then run the
    debrief (rules 33-36).

## Rubric: Five Dimensions, 1-4, Anchored

Score every dimension 1-4. The anchors below describe concrete behavior in the
session, not adjectives. 1 = well below bar; 3 = the bar (interview-ready); 4 =
standout. Record scores with `--mode mock` (rule 37).

28. **problem-solving** — approach discovery, decomposition, recovery.
    - **1**: Never found a workable approach, or waited to be led to one.
    - **2**: Reached an approach only after long thrashing, or jumped to code on
      a half-formed idea and got lucky; could not recover when it stalled.
    - **3**: Found a correct approach in reasonable time, decomposed it, and
      adjusted when the first idea hit friction.
    - **4**: Reached the optimal approach quickly, justified why it is correct,
      and named the tradeoff against the baseline unprompted.

29. **communication** — structure, precision, interviewer alignment. Incorporates
    the interview-communication rules in `docs/DSA_OS_MASTER.md` (restate first,
    declare the brute-force baseline before optimizing, name the invariant
    explicitly, speak in steps not syntax, call out tradeoffs and rejected
    options, narrate the expectation-vs-state mismatch when debugging, end with
    complexity; silence while thinking is fine, vagueness is not).
    - **1**: Silent or unintelligible; the interviewer cannot follow the plan.
    - **2**: Narrated some of it but skipped the restatement or the baseline,
      spoke in code syntax instead of steps, or left the invariant implicit;
      the interviewer had to guess the intent.
    - **3**: Restated the problem, declared a baseline, named the invariant, and
      spoke in steps; easy to follow throughout.
    - **4**: All of 3, plus proactively surfaced rejected options and tradeoffs
      and kept the interviewer aligned at every transition without being asked.

30. **code-quality** — clean, correct, readable translation of the plan.
    - **1**: Did not produce running code, or code that cannot be correct.
    - **2**: Code mostly worked but had a boundary/initialization bug, tangled
      structure, or names that obscured intent; needed several passes to trust.
    - **3**: Correct, readable code that matched the stated plan, with sensible
      names and no dead ends.
    - **4**: Correct on the first pass, tight and idiomatic, invariants obvious
      from the structure; nothing to suggest changing.

31. **testing** — self-driven verification.
    - **1**: Declared "done" with no dry run; waited for the interviewer to test.
    - **2**: Ran only the happy path, or dry-ran mechanically and missed the bug
      the trace should have exposed.
    - **3**: Chose a normal, an edge, and an adversarial case unprompted and
      traced them honestly, catching their own mistakes.
    - **4**: All of 3, plus reasoned about the input class that would break it and
      confirmed the boundary behavior deliberately.

32. **time-management** — pacing across the beats within 45 minutes.
    - **1**: Ran out of time with no working solution and no sense of the clock.
    - **2**: Finished late or barely, having spent too long in one beat (usually
      approach-hunting or debugging) and rushing the rest.
    - **3**: Hit approach by ~15 min, coding by ~30, testing by ~40, and closed
      inside the cap.
    - **4**: Comfortably ahead of the checkpoints with time left for the
      follow-up, never rushed.

## Verdict

Assign one overall verdict, interviewer-style. It is a holistic judgment
informed by the five scores, not their average.

- **strong-hire**: Would advance without hesitation. Optimal approach, clean
  code, self-tested, well-paced, clear communication throughout.
- **hire**: Would advance. Solved it correctly and communicated well, with minor
  rough edges that would not sink a real loop.
- **no-hire**: Would not advance. Real gaps — needed steering to the approach,
  shipped a bug they did not catch, ran over time, or could not explain the
  solution — but the foundation is visible.
- **strong-no-hire**: Would not advance, and the gap is fundamental: no workable
  approach, or no ability to communicate or verify one.

## Debrief

The debrief is where the mock becomes learning. Run it immediately after the
verdict, still honest, now as a coach again.

33. State the verdict plainly and the one or two behaviors that most drove it.
34. Name concrete weaknesses the mock exposed — a missed edge class, a rushed
    approach phase, an implicit invariant never spoken. Record each on the mock
    entry (`weaknesses`); these are also mirrored into
    `progress.json.weaknesses_detected` with a `Mock: ` prefix, tagged as source
    `mock`, so the weakness lab and future teaching sessions can act on them.
35. Contrast with teaching-mode performance. A student who solves cleanly with
    Socratic scaffolding but freezes without it has a specific, nameable gap:
    independent recognition under pressure. Say so.
36. Update the personal playbook only if the mock produced a genuinely reusable
    lesson (e.g. "state complexity before coding, always"). Do not log generic
    advice.

## Recording

37. Record the mock with `scripts/update_progress.py --mode mock`:

    ```bash
    python3 scripts/update_progress.py --mode mock \
      --problem-id CPX-004 \
      --completed-at 2026-07-25 \
      --mock-duration-minutes 42 \
      --mock-score problem_solving=3 --mock-score communication=3 \
      --mock-score code_quality=3 --mock-score testing=2 \
      --mock-score time_management=3 \
      --mock-verdict hire \
      --mock-notes "Found the hash-map approach unprompted; missed the self-match edge case until the dry run." \
      --mock-weakness "Started coding before stating complexity." \
      --mock-weakness "Did not test target = 2*x self-pair case until prompted to dry-run."
    ```

    This appends one entry to `progress.json.mock_interviews[]` (date,
    problem_id, duration_minutes, the five 1-4 scores, verdict, notes,
    weaknesses) and mirrors each weakness into `weaknesses_detected`. It does
    not touch completion records, revision state, skill mastery, or the current
    problem — a mock measures; it does not advance the curriculum.

## Golden Rules of the Mock

38. Measure, don't teach. The teaching happens in the debrief, never mid-solve.
39. Never reveal the pattern, the algorithm, or the data structure.
40. Hold the 45-minute cap and announce every checkpoint.
41. Require approach and complexity out loud before code.
42. Grade honestly. An inflated verdict robs the student of the one signal a
    mock exists to produce.
