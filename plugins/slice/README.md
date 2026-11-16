# slice

A light harness that takes a specification to committed code, one vertical slice at a
time. A slice is a user story that cuts through every layer of the app.

## Flow

1. `/slice:spec`: find the ambiguities in the specification and ask the user about each,
   one question at a time. The user ratifies the result in `slice/spec.md`.
2. `/slice:plan`: break the spec into vertical slices in `slice/slices.md`.
3. `/slice:interface`: design one test surface for all the slices, create it as stubs,
   and have `slice:test-writer` write red acceptance tests against it.
4. `/slice:build`: for each slice, `slice:implementer` writes the code. A hook keeps it out of
   the tests. A script runs the tests, `slice:reviewer` reviews, and a script commits the slice.
5. `/slice:run`: run the stages in order, from the state in `slice/`.

## Records

All records are in `slice/` at the project root: `config.md` (stack, test command, tests
folder, source folders), `spec.md`, `slices.md`, `interface.md`, and `review/Sn.md`. The
templates are in `templates/`.

## Script and hook

- `bin/slice.py`: `status`, `set`, `round`, `test` (with `--red`), and `commit`. Run it as
  `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py`. It gives 5 test rounds and 3 review rounds
  for each slice. It commits with the subject "Slice Sn: <title>" and the trailer `Slice: Sn`.
- `hooks/guard.py`: blocks the implementer from every read, search, edit, and command that
  reaches the tests folder. The check is by name, so it is a guard, not a sandbox.

## Test names

Each test name holds the ID of its slice, for example `test_S1_counts_words`. The script
uses the ID to pick the tests of a slice.

## Tests

`(cd plugins/slice && python3 -m unittest discover -s tests)`
