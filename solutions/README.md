# solutions/

Convention: one file per solved problem, `solutions/<PROBLEM-ID>.py` (e.g.
`solutions/OBS-001.py`).

"Solved means it ran." Each file holds your solution plus 3-5 embedded
`assert` statements you write yourself, including at least one edge case -
writing them doubles as edge-case practice. Running the file must execute
the asserts and exit 0; that's the whole contract, not a full test harness.

`scripts/update_progress.py` runs this check automatically before recording
a NEW solve (via `scripts/run_checks.py <PROBLEM-ID>`, 30s timeout). A
missing file, a failing assert, or any other exception aborts the record
before anything is written. For whiteboard-style sessions with no code,
pass `--no-code` to bypass the gate; it appends a note to the record
instead of running anything.

Revisions (`--revision-result PASS|FAIL`) are recall exercises recorded via
the CLI and are not gated by this check.

See `solutions/_example.py` for the expected shape. It is not a real
problem id - do not treat it as one.

Check one file manually:

    python3 scripts/run_checks.py OBS-001
    make check-solution PROBLEM=OBS-001
