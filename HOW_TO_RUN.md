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
- run the mentor's question sequence (Restatement → Examples → Brute Force → Repeated Work → Invariant → Proof → Algorithm → Code → Review → Retrospective) — one question at a time, no early pattern/algorithm reveals
- at the end, ask you in one short batch for the few things only you can report honestly: time taken, hint level, confidence before/after, thinking-score self-assessment, and for revisions the PASS/FAIL recall dimensions
- run `update_progress.py` itself with those numbers and tell you the new stage
- remind you once to download the updated `progress.json` (chat sessions only — skip if the repo lives on a persistent disk)

## Your only two jobs

1. **Answer the mentor's questions honestly** — restate the problem in your own words, build real examples, propose a real brute force, etc. Don't let it skip ahead; if it names the pattern or algorithm early, tell it to stop and follow the protocol.
2. **Give honest self-assessment numbers** when it asks at the end, and **download `progress.json`** if reminded.

Everything else — which script runs when, filling the case file, computing your stage, advancing or retrying revision state — is the agent's job, not yours.

## If something looks wrong

- Validation fails → the agent should stop and tell you exactly what's inconsistent. Don't let it push through a broken repo.
- It asks *you* to run a command → that's a bug in this session; point it back to `boot_instructions/instructions.txt` PHASE 0.
- Unsure which mentor protocol file is authoritative → there's only one: `mentor/mentor_protocol.md`. It's self-documenting on this — it explicitly states it replaced and superseded the old `enhanced_mentor_protocol.md` and `mentor_protocol_updated.md` files, which no longer exist in this repo.
