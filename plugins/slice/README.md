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
   `domain.md`. Each requirement must map to the model. It holds no code.
4. `/slice:interface`: design one test surface for all the slices. Create it as stubs that
   raise the not-implemented error. Then `slice:test-writer` writes red acceptance tests
   from `interface.md` alone. A script checks that each test is red. The tests and
   stubs go in one "Interface: NNN-name" commit.
5. `/slice:build`: for the slice that `next` names, `slice:implementer` writes the code. A hook keeps it out
   of the tests. A script runs the tests, `slice:reviewer` checks the requirements, the
   architecture, and the security, and a script commits the slice.
6. `/slice:run`: loop on `slice.py next` (a stage, `build Sn`, `stop Sn: reason`, or `done`). Run and build recap.

## Model

Every agent and skill sets `model: claude-opus-5-5` and `effort: medium` in its frontmatter.
Claude Code supports both fields for agents and skills. The bindings have limits: `CLAUDE_CODE_EFFORT_LEVEL` overrides `effort`, and a skill's `model` lasts one turn and can be dropped by an `availableModels` allowlist or auto mode.

## Records

`slice/config.md` (stack, test command, tests folder, source folders) is at the top of
`slice/`. Each spec has a folder, `slice/NNN-<name>/`,
with `spec.md`, `slices.md`, `domain.md`, `interface.md`, and `review/Sn.md`. The scripts
use the highest number, or the folder that `--spec` names. The templates are in
`templates/`. `contracts.json` lists each hand-off between the prompts and the scripts.

## Script and hook

- `bin/slice.py`: `status`, `next`, `set`, `round`, `test` (with `--red`), and `commit`. Run it with
  `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py`. It gives 5 test rounds and 3 review rounds
  for each slice. A slice commit has the subject "Slice Sn: <title>" and the trailer
  `Slice: Sn`. It holds the records and the source folders, not the tests. `commit
  interface` holds the tests and the stubs of all slices, so a slice commit stays small.
- `hooks/guard.py`: blocks the implementer from every read, search, edit, and command that
  reaches the tests folder, also through quotes, wildcards, and symlinks, from every test
  runner, and from `slice.py` except `test`. It limits its writes to the source folders. It blocks the
  test writer from the source folders, and limits its writes to the tests folder. The
  check is by name and by path, so it is a guard, not a sandbox.

## Test names

Each test name holds the ID of its slice and of its requirement, for example
`test_S1_R1_counts_words`.

## Tests

`(cd plugins/slice && python3 -m unittest discover -s tests)`
