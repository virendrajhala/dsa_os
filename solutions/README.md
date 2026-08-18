# solutions/

This directory holds the **main (582-problem) track's** solutions. Every other
track keeps its own beside its data — the Blind 75 track's live in
`tracks/blind75/solutions/`. The contract below is identical in both; only the
directory and the problem-id shape differ.

Convention: one file per solved problem, `solutions/<PROBLEM-ID>.py` (e.g.
`solutions/OBS-001.py`). **Java is also supported** —
`solutions/<PROBLEM-ID>.java` (e.g. `solutions/CPX-004.java`); see the Java
notes below. When both exist for a problem, the `.py` is the gate file.

"Solved means it ran." Each file holds your solution; embedded `assert`
statements (ideally 3-5, including an edge case) are **recommended but
optional** — writing them doubles as edge-case practice, but the gate never
requires them. Running the file must exit 0 (any asserts you did include must
pass); that's the whole contract, not a full test harness.

For Java the gate compiles the file and runs it with assertions enabled
(`javac` then `java -ea <MainClass>`). Two rules make it work: the file must
have **no `public` top-level class** (the filename is the problem id, and a
hyphen is not a legal Java class name — use package-private classes), and
exactly one class must declare `public static void main(String[])`, where any
asserts you chose to write run. See `solutions/_example.java`. `javac`/`java` must be on PATH.

`scripts/update_progress.py` runs this check automatically before recording
a NEW solve (via `scripts/run_checks.py <PROBLEM-ID>`, 30s timeout). A
missing file, a failing assert, or any other exception aborts the record
before anything is written. It looks in the directory belonging to the track
you passed `--track` for, so you never point it at the solutions dir yourself.
For whiteboard-style sessions with no code, pass `--no-code` to bypass the
gate; it appends a note to the record instead of running anything.

Revisions (`--revision-result PASS|FAIL`) are recall exercises recorded via
the CLI and are not gated by this check.

See `solutions/_example.py` for the expected shape. It is not a real
problem id - do not treat it as one.

Check one file manually — `run_checks.py` has no track flag of its own, so on a
non-main track point it at that track's directory (the `make` target does this
for you):

    python3 scripts/run_checks.py OBS-001
    make check-solution PROBLEM=OBS-001

    python3 scripts/run_checks.py B75-001 --solutions-dir tracks/blind75/solutions
    make check-solution PROBLEM=B75-001 TRACK=blind75
