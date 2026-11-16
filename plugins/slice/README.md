# slice

A light harness that takes a specification to committed code, one vertical slice at a
time. A slice is a user story that cuts through every layer of the app.

## Flow

1. `/slice:spec`: find the ambiguities in the specification and ask the user about each,
   one question at a time. If no stack is fixed, the interview recommends one. The user
   ratifies the result in `slice/NNN-<name>/spec.md`, with numbered requirements (R1) and
   decisions (D1).
2. `/slice:plan`: break the spec into vertical slices in `slices.md`. Each slice names its
   requirements.
3. `/slice:domain`: model the entities, the state machines, and the boundary in
   `domain.md`. Each requirement must map to the model. This is a design document only.
4. `/slice:interface`: design one test surface for all the slices. Create it as stubs that
   raise the not-implemented error. Then `slice:test-writer` writes red acceptance tests
   from `interface.md` alone. A script checks that each test is red. The tests and
   stubs go in one "Interface: NNN-name" commit.
5. `/slice:build`: for each slice, `slice:implementer` writes the code. A hook keeps it out
   of the tests. A script runs the tests, `slice:reviewer` checks the requirements, the
   architecture, and the security, and a script commits the slice.
6. `/slice:run`: loop on `slice.py next`, which prints the next stage and slice, `done`, or the stop with its reason. Run and build say what they start and recap at the end.

## Model

Every agent and skill sets `model: claude-opus-5-5` and `effort: medium` in its frontmatter.
Claude Code supports both fields for agents and skills.

## Records

`slice/config.md` (stack, test command, tests folder, source folders) is at the top of
`slice/`. Each spec has a folder, `slice/NNN-<name>/` (for example `slice/001-wordfreq/`),
with `spec.md`, `slices.md`, `domain.md`, `interface.md`, and `review/Sn.md`. The scripts
use the folder with the highest number, or the one that `--spec` names. The templates are in
`templates/`. `contracts.json` lists each hand-off between the prompts and the scripts.

## Script and hook

- `bin/slice.py`: `status`, `next`, `set`, `round`, `test` (with `--red`), and `commit`. Run it as
  `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py`. It gives 5 test rounds and 3 review rounds
  for each slice. A slice commit has the subject "Slice Sn: <title>" and the trailer
  `Slice: Sn`. It holds the records and the source folders, not the tests. `commit
  interface` holds the tests and the stubs of all slices, so each slice commit stays small.
- `hooks/guard.py`: blocks the implementer from every read, search, edit, and command that
  reaches the tests folder, also through quotes, wildcards, and symlinks. It also blocks
  the test writer from the source folders, and limits its writes to the tests folder. The
  check is by name and by resolved path, so it is a guard, not a sandbox.

## Test names

Each test name holds the ID of its slice and of its requirement, for example
`test_S1_R1_counts_words`. The script uses the slice ID to pick the tests of a slice.

## Tests

`(cd plugins/slice && python3 -m unittest discover -s tests)`
