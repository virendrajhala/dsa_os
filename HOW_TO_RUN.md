# HOW_TO_RUN.md

You send **one message** to start a session. The agent handles orchestration
(validating, checking revisions, picking the problem, logging progress). Your
job is to think through the DSA problem when it asks — nothing else.

The one thing you must decide first is **which track** you are running.

---

## Pick your track

The repository carries two independent curricula. They share the same mentor
protocol, the same scoring, and the same learning path — they differ in how much
ground they cover.

| | **Main (582)** | **Blind 75** |
|---|---|---|
| Problems | 582 | 75 |
| Skills / stages | 93 skills, 13 stages | 35 skills, 12 stages |
| Pace plan | 13-week quarter, deload weeks | 8-week sprint, no deloads |
| Problem ids | `OBS-001`, `DP-015`, … | `B75-001` … `B75-075` |
| Track flag | `TRACK=main` (the default) | `TRACK=blind75` |
| Use it when | You have months, and want real depth and coverage | You have weeks, and want one fast pass over every major pattern |

**The two tracks share no files at all.** Not progress, not solutions, and not
your accumulated notes: each track keeps its own mistake catalog, mentor memory,
thinking-pattern log, interview playbook and interview-frequency snapshot. A
track directory is self-contained — everything the Blind 75 track reads or
writes is inside `tracks/blind75/`.

The practical consequences:

- Solving a problem on one track records nothing on the other, even where both
  cover the same LeetCode problem. You can run the sprint now and come back to
  the 582 track later with its history exactly as you left it.
- A mistake or insight logged during the sprint lands in the sprint's own files.
  It will not appear in the 582 track's catalog. If you want it in both, you
  write it in both — deliberately.
- Each track has its own revision queue and its own weekend mock schedule.

**Never mix tracks inside one session.** Pick one, say so at the start, finish
the session on it.

---

## Section A — Running the Main (582) track

This is the default. No flags anywhere.

### Start a session

In Claude Code, from the repo:

> /mentor-session

or, in plain words:

> Start a mentor session on the main track.

If you're pasting the repo into a chat instead of running it in-repo, attach the
zip and send:

> Here's my DSA_OS repository. Read `boot_instructions/instructions.txt` and follow it exactly, including PHASE 0a and PHASE 0. Run it on the **main** track. **Actually run** the scripts (validate, revision check, next problem) — don't just describe what they'd probably output. Then begin the mentor session for whatever problem/revision comes up.

### Commands, if you want to look yourself

```bash
make validate                  # integrity check (covers every track)
make next                      # what to work on now
make revise                    # what recall is due today
make stats                     # full revision + trend report
make dashboard                 # console summary
make weakness                  # weakness-targeted practice plan
make check-solution PROBLEM=OBS-001
```

Your solutions go in `solutions/<PROBLEM-ID>.py`. Your state lives in
`progress/progress.json`.

---

## Section B — Running the Blind 75 track

Same everything, with `TRACK=blind75`.

### Start a session

In Claude Code, from the repo:

> /mentor-session blind 75

or, in plain words:

> Start a mentor session on the Blind 75 track.

Saying "blind 75", "b75", or "the sprint" is enough — the agent picks the track
from that and confirms it in one line before starting. If you don't say, it will
ask once rather than guess.

For the zip-into-a-chat flow:

> Here's my DSA_OS repository. Read `boot_instructions/instructions.txt` and follow it exactly, including PHASE 0a and PHASE 0. Run it on the **blind75** track — pass `--track blind75` to every script. **Actually run** the scripts, don't describe them. Then begin the mentor session for whatever problem comes up.

### Commands, if you want to look yourself

```bash
make next TRACK=blind75
make revise TRACK=blind75
make stats TRACK=blind75
make dashboard TRACK=blind75
make weakness TRACK=blind75
make check-solution PROBLEM=B75-001 TRACK=blind75
```

Your solutions go in `tracks/blind75/solutions/<PROBLEM-ID>.py`. Your state lives
in `tracks/blind75/progress.json`. Everything else the track uses sits beside
them — its own curriculum, skills, stages, dependency graph, patterns, scoring,
plan, mistake catalog, mentor memory, thinking patterns, interview playbook and
interview-frequency snapshot. Nothing outside `tracks/blind75/` is read or
written while you are on this track.

### Rebuilding the track

The Blind 75 track is generated from the main curriculum, not hand-written:

```bash
python3 scripts/generate_blind75_track.py
```

Re-run it after a main-curriculum fix. It is safe to re-run — everything you own
is protected:

- `progress.json` is kept if it holds any completion or mock.
- `mistake_catalog.json` is kept if it holds any entry.
- `mentor_memory.md`, `thinking_patterns.md`, `interview_playbook.md` are seeded
  once on first generation and never rewritten after that.
- `solutions/` is never touched.

It says which files it kept. Everything else — curriculum, skills, stages,
graph, patterns, scoring, plan — is derived, so don't hand-edit those: a
regeneration would silently discard the edit. Fix the main curriculum and
regenerate instead.

To refresh this track's interview-frequency data:

```bash
make refresh-frequency TRACK=blind75
```

---

## What the agent does for you (either track)

- runs `validate_curriculum.py` first and stops if it fails
- checks for a due active-recall revision and works that instead of new material if one exists
- picks today's problem via `next_problem.py` — the only authority on what to work
- runs the mentor's question sequence (Restatement → Examples → Brute Force → Repeated Work → Invariant → Proof → Algorithm → Implementation Blueprint → Code → Review → Retrospective) — one question at a time, no early pattern/algorithm reveals, and no code before the blueprint
- at the end, asks you in one short batch for the few things only you can report honestly: time taken, hint level, confidence before/after, thinking-score self-assessment, independent Algorithm Thinking score, independent Implementation Engineering score, and for revisions the PASS/FAIL recall dimensions
- runs `update_progress.py` itself with those numbers and tells you the new stage
- reminds you once to download the updated `progress.json` (chat sessions only — skip if the repo lives on a persistent disk)

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

**One server shows both tracks.** The sidebar footer has a **582 / B75** switch;
clicking it reloads the page against that track's data. You can tell which track
you're looking at from two places: the Source card names the progress file in
use, and the heading above each workspace reads `B75 · Today` on the Blind 75
track. There is no separate command or port for the second track.

The briefing needs the server running — the numbers come from `/api/feed`,
computed by the same code as the CLI. Opening the file directly still shows
the tables and the curriculum map, with a banner where the live numbers go.

## If something looks wrong

- Validation fails → the agent should stop and tell you exactly what's inconsistent. Don't let it push through a broken repo.
- It asks *you* to run a command → that's a bug in this session; point it back to `boot_instructions/instructions.txt` PHASE 0.
- The agent works the wrong curriculum → it skipped track selection. Stop it, name the track, and have it re-run `next_problem.py` with the right `--track`.
- The dashboard shows a banner saying a track couldn't be loaded → that track's files are missing. Run `python3 scripts/generate_blind75_track.py`. The dashboard falls back to the 582 track meanwhile, so you're never stuck.
- Unsure which mentor protocol file is authoritative → use `mentor/mentor_protocol.md`. `mentor/enhanced_mentor_protocol.md` is only a backward-compatibility pointer for older prompts.
