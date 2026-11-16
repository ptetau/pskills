---
name: build
description: >
  Builds each planned slice in order. The implementer agent writes the code from the interface and the spec, and a hook keeps it out of the tests. A script runs the tests, a reviewer reviews, and a script commits the slice. Use when the user says "/slice:build", or when the slices are red.
---

# slice build

## Goal

Each slice is built, its tests pass, no major finding is open, and it is one commit.

## Inputs

- The slice that the user names, else the first one that is not `done` or `stopped`.

## Outputs

- Code from `slice:implementer`, then `slice.py commit <Sn>`: the subject "Slice Sn: <title>" and the trailer `Slice: Sn`. The slice is `done`.

## Constraints

- `slice.py` is `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py`. Give the implementer test results only, not test code.
- Test loop: `slice.py set <Sn> building`. Before each implementer run (at most 5), `slice.py round <Sn> test`. After it, `slice.py test <Sn>`.
- Review loop, when the tests pass: `slice.py set <Sn> review`. Before each reviewer run (at most 3), `slice.py round <Sn> review`. Send the findings (`review/<Sn>.md`) to the implementer, then run the tests again.
- A refused round stops the slice. Show what fails, and ask the user.
- Start each agent in the foreground.
- Outputs give each reader exactly what it reads: see `contracts.json`.

## Done when

- Each slice is `done`, or `stopped` and the user is asked.
