# slice

A light harness that takes a specification to committed code, one vertical slice at a
time. A slice is a user story through every layer.

## Flow

1. `/slice:spec`: find the ambiguities in the specification and ask the user about each,
   one question at a time. The interview recommends a stack if none is fixed. The user
   ratifies the result in `slice/NNN-<name>/spec.md`, with numbered requirements (R1) and
   decisions (D1).
2. `/slice:plan`: break the spec into vertical slices in `slices.md`. Each slice names its
   requirements.
3. `/slice:domain`: model the entities, the state machines, and the boundary in
   `domain.md`. Each requirement must map to the model. It holds no code. A state machine is a
   `### Machine: <Object>` section (`- States:`, `- Start:`, `- End:`, `- T1: <from> -> <to> on
   <trigger> [<guard>] / <effect>`, `- X1: <from> on <trigger> refused: <error>`), or the line
   `- Machines: none`. A requirement cites transitions as `Order.T1`. `status` reports a cited
   transition that no machine defines, a transition that no requirement cites, a machine with no
   start state, and an unreachable state; `next` keeps printing `domain` until none is left.
4. `/slice:interface`: design one test surface for all the slices. The user approves it
   (`Status: approved`). Create it as stubs that fail with the not-implemented error of the
   stack. A `- Changed:` line per slice lists the requirements of existing entries that
   change: their tests can fail by assertion. Then `slice:test-writer` writes red acceptance tests
   from `interface.md` alone. A script checks that each test is red. The tests and
   stubs go in one "Interface: NNN-name" commit.
5. `/slice:build`: for the slice that `next` names, `slice:implementer` writes the code. A hook keeps it out
   of the tests. A script runs the tests, `slice:reviewer` checks the requirements, the
   architecture, and the security, and a script commits the slice.
6. `/slice:run`: loop on `slice.py next` (a stage, `build Sn`, `stop Sn: reason`, or `done`). Run and build recap.
   After the user answers a stop, `slice.py resume Sn` restarts the slice.

## Model

Every agent and skill sets `model: claude-opus-5-5` and `effort: medium` in its frontmatter, except the reviewer, which sets `effort: high`.
Claude Code supports both fields for agents and skills. The bindings have limits: `CLAUDE_CODE_EFFORT_LEVEL` overrides `effort`, and a skill's `model` lasts one turn and can be dropped by an `availableModels` allowlist or auto mode.

## Records

`slice/config.md` (stack, test command, tests folder, source folders, optional `source files`
such as `package.json, migrations/**`) is at the top of `slice/`. Each spec has a folder, `slice/NNN-<name>/`,
with `spec.md`, `slices.md`, `domain.md`, `interface.md`, and `review/Sn.md`. The scripts
use the highest number, or the folder that `--spec` names. The templates are in
`templates/`. `contracts.json` lists each hand-off between the prompts and the scripts.

## Script and hook

- `bin/slice.py`: `status`, `next`, `set`, `round`, `resume`, `test` (with `--red`), and `commit`. Run it with
  `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py`. It gives 5 test rounds and 3 review rounds
  for each slice. A slice commit has the subject "Slice Sn: <title>" and the trailer
  `Slice: Sn`. It holds the records, the source folders, and the source files, not the tests.
  `commit interface` holds the tests and the stubs of all slices, so a slice commit stays
  small. `commit Sn` refuses when a done slice's test, or a test that no slice owns, fails.
  `test Sn` lists these regressions. For each failing test it prints the acceptance lines of the
  requirement that the test name cites. An assertion failure keeps its message back until the slice
  has used 2 test rounds, so the implementer works from the spec and not from the expected
  value; an error (an exception, an import error) prints at once. `test Sn --full` prints every message
  (the guard blocks it, and `--red`, for the implementer).
- `slice.py scan` runs the optional config line `- security scan: <command>` (for example
  `bandit -q -r src`, `semgrep --error --config auto src`, `npm audit --audit-level=high`; default
  `none`). It exits 1 when the command fails or runs over 300 seconds. The reviewer runs it and
  reports a failure as a major security finding, and `commit Sn` refuses while it fails.
- `hooks/guard.py`: blocks the implementer from every read, search, edit, and command that
  reaches the tests folder, also through quotes, wildcards, and symlinks, from every test
  runner, and from `slice.py` except `test`. It limits its writes to the source folders and
  source files. It blocks the test writer from both, and limits its writes to the tests folder. The
  check is by name and by path, so it is a guard, not a sandbox.

## Test names

Each test name holds its spec number, slice ID, and requirement ID: `test_NNN_Sn_Rn_<what>`,
for example `test_002_S1_R2_counts_words`. A name with no number belongs to the only spec of
a project. It belongs to no slice when there are two specs.

## Tests

`(cd plugins/slice && python3 -m unittest discover -s tests)`
