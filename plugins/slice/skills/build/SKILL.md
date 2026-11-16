---
name: build
description: >
  Builds one slice. The implementer agent writes the code from the interface and the spec, and a hook keeps it out of the tests. A script runs the tests, a reviewer reviews, and a script commits the slice. Use when the user says "/slice:build", or when the slices are red.
model: claude-opus-5-5
effort: medium
---

# slice build

## Goal

One slice passes its tests, has no open major finding, and is one commit. The skill never picks the slice or the order: `slice.py next` does.

## Inputs

- The slice `Sn` from the `build Sn` line of `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py next`, or the slice that the user names. If `next` prints another line (`stop`, a stage) and the user names no slice, build nothing and report that line.

## Outputs

- Code from `slice:implementer`, then `slice.py commit <Sn>`: the subject "Slice Sn: <title>" and the trailer `Slice: Sn`. The slice is `done`.
- Before the slice, one line that says what starts. At the end, a short recap.

## Constraints

- `slice.py` is `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py`. Give the implementer test results only.
- Test loop: `slice.py set <Sn> building`, then `slice.py test <Sn>`. If the tests already pass, go to review. Else, before each implementer run (at most 5), `slice.py round <Sn> test`; after it, `slice.py test <Sn>`.
- Review loop, when the tests pass: `slice.py set <Sn> review`. Before each `slice:reviewer` run (at most 3), `slice.py round <Sn> review`. Send `review/<Sn>.md` to the implementer, then test again. If a test fails after a review fix, go back to the test loop: that fix uses a test round.
- A refused round stops the slice: ask the user.
- Run agents in the foreground.
- Outputs give each reader exactly what it reads: see `contracts.json`.

## Done when

- That slice is `done`, or `stopped` and the user is asked. No other slice is built.
