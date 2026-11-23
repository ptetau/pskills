# slice: script, hook, and test names

This page holds the details of `bin/slice.py`, the guard hook, and the test names. For the overview, read `README.md`.

## Script and hook

- `bin/slice.py`: `status`, `next`, `set`, `round`, `resume`, `test`, `scan`, and `commit`. Run it with
  `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py`. It gives 5 test rounds and 3 review rounds
  for each slice. A slice commit has the subject "Slice Sn: <title>" and the trailer
  `Slice: Sn`. It holds the records, the source folders, and the source files, not the tests.
  `commit interface` holds the tests and the stubs of all slices, so a slice commit stays
  small. `commit Sn` refuses when a done slice's test, or a test that no slice owns, fails, when
  the security scan fails, and on an open `major` line in `review/Sn.md` or `review/Sn.tests.md`.
  `test Sn` lists the regressions.
- `test Sn` prints, for each failing test, the acceptance lines of the requirement that its name
  cites. An assertion failure keeps its message back until the slice has used 2 test rounds, so the
  implementer works from the spec and not from the expected value. An error (an exception, an
  import error) prints at once. `test Sn --full` prints every message.
- `commit tests Sn` commits a test fix (the tests folder and the records). It needs the slice in
  `review`, an open tests finding, and a change in the tests folder. Each test of the slice must
  run: a pass, a failing assertion, or the not-implemented error. A failing test sends the slice
  back to `building`. A test fix is part of the review round that found it.
- `slice.py scan` runs the optional config line `- security scan: <command>` (for example
  `bandit -q -r src`, `semgrep --error --config auto src`, `npm audit --audit-level=high`; default
  `none`). It exits 1 when the command fails or runs over 300 seconds. The reviewer runs it and
  reports a failure as a major security finding.
- `hooks/guard.py`: blocks the implementer from every read, search, edit, and command that
  reaches the tests folder, also through quotes, wildcards, and symlinks, from every test
  runner, from `test --full` and `test --red`, and from `slice.py` except `test`. It limits its writes
  to the source folders and source files, and hides `review/Sn.tests.md` from it. It blocks the
  test writer from the source folders, the source files, and `review/Sn.md`, and limits its writes
  to the tests folder. The check is by name and by path, so it is a guard, not a sandbox.

## Test names

Each test name holds its spec number, slice ID, and requirement ID: `test_NNN_Sn_Rn_<what>`,
for example `test_002_S1_R2_counts_words`. A name with no number belongs to the only spec of
a project. It belongs to no slice when there are two specs.
