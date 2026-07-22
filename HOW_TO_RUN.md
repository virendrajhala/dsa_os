# HOW_TO_RUN.md

You send **one message** to start a session. The agent handles orchestration
(validating, checking revisions, picking the problem, logging progress). Your
job is to think through the DSA problem when it asks — nothing else.

## The one message

Attach the repo zip and send:

> Here's my DSA_OS repository. Read `boot_instructions/instructions.txt` and follow it exactly, including PHASE 0. **Actually run** the scripts (validate, revision check, next problem) — don't just describe what they'd probably output. Then begin the mentor session for whatever problem/revision comes up.

That's it. From here the agent should, on its own:
- run `validate_curriculum.py` first and stop if it fails
- check for a due active-recall revision and work that instead of new material if one exists
- pick today's problem via `next_problem.py`
- run the mentor's question sequence (Restatement → Examples → Brute Force → Repeated Work → Invariant → Proof → Algorithm → Implementation Blueprint → Code → Review → Retrospective) — one question at a time, no early pattern/algorithm reveals, and no code before the blueprint
- at the end, ask you in one short batch for the few things only you can report honestly: time taken, hint level, confidence before/after, thinking-score self-assessment, independent Algorithm Thinking score, independent Implementation Engineering score, and for revisions the PASS/FAIL recall dimensions
- run `update_progress.py` itself with those numbers and tell you the new stage
- remind you once to download the updated `progress.json` (chat sessions only — skip if the repo lives on a persistent disk)

## Your only two jobs

1. **Answer the mentor's questions honestly** — restate the problem in your own words, build real examples, propose a real brute force, etc. Don't let it skip ahead; if it names the pattern or algorithm early, tell it to stop and follow the protocol.
2. **Give honest self-assessment numbers** when it asks at the end, and **download `progress.json`** if reminded.

Everything else — which script runs when, filling the case file, computing your stage, advancing or retrying revision state — is the agent's job, not yours.

## Looking at where you stand

Between sessions, run `make web-dashboard` and open
`http://127.0.0.1:8765/web_dashboard/`. **Today** answers "what do I do now,
and am I on trajectory" — next action, readiness gates, what recall is due,
and how much review lands in the next 14 days. **Evidence** is where you
check whether the practice is working: hint independence trending down, mock
verdicts, and whether mature (R3+) recall is holding up. The page is
read-only; `update_progress.py` remains the only writer.

The briefing needs the server running — the numbers come from `/api/feed`,
computed by the same code as the CLI. Opening the file directly still shows
the tables and the curriculum map, with a banner where the live numbers go.

## If something looks wrong

- Validation fails → the agent should stop and tell you exactly what's inconsistent. Don't let it push through a broken repo.
- It asks *you* to run a command → that's a bug in this session; point it back to `boot_instructions/instructions.txt` PHASE 0.
- Unsure which mentor protocol file is authoritative → use `mentor/mentor_protocol.md`. `mentor/enhanced_mentor_protocol.md` is only a backward-compatibility pointer for older prompts.
