# slice: script, hook, and test names

This page holds the details of `bin/slice.py`, the guard hook, and the test names. For the overview, read `README.md`.

## Script and hook

- `bin/slice.py`: `status`, `next`, `set`, `round`, `resume`, `test`, `scan`, and `commit`. Run it with
  `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py`. It gives 5 test rounds and 3 review rounds
  for each slice. A slice commit has the subject "Slice Sn: <title>", a body from `--summary` or
  the slice's story and requirements, and the trailer `Slice: Sn`. It holds the records, the
  source folders, the unit tests folder, the source files, and the tests folder.
- `commit Sn` refuses when tests are missing or fail, or when a regression or security scan
  fails. It also refuses when a major finding is open in `review/Sn.md` or `review/Sn.tests.md`.
  `test Sn` lists the regressions.
- `test Sn` prints, for each failing test, the acceptance lines of the requirement that its name
  cites. An assertion failure withholds its message for 2 test rounds, so the implementer works
  from the spec. An error (an exception, an import error) prints at once. `test Sn --full` prints
  every message.
- `slice.py scan` runs the optional config line `- security scan: <command>` (for example
  `bandit -q -r src`, `semgrep --error --config auto src`, `npm audit --audit-level=high`; default
  `none`). It exits 1 when the command fails or runs over 300 seconds. The reviewer runs it and
  reports a failure as a major security finding.
- `hooks/guard.py`: blocks the implementer from reading, searching, or editing the acceptance
  `tests folder` (also through quotes, wildcards, and symlinks). It also blocks acceptance test
  runners, `test --full`, and `slice.py` except `test`. The implementer writes only in
  `source folders`, `unit tests folder`, and `source files`, and cannot read `review/Sn.tests.md`.
- `hooks/guard.py` blocks `slice:test-writer` from `source folders` (except read-only `boundary files`),
  `unit tests folder`, `source files`, and `review/Sn.md`. It limits its writes to `tests folder`.
  The check is by name and by path, so it is a guard, not a sandbox.

## Test names

Each test name holds its spec number, slice ID, and requirement ID: `test_NNN_Sn_Rn_<what>`,
for example `test_002_S1_R2_counts_words`. A name with no number belongs to the only spec of
a project. It belongs to no slice when there are two specs.
