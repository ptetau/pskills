---
name: build
description: >
  Builds each planned slice in order. The implementer agent writes the code from the interface and the spec, and a hook keeps it out of the tests. A script runs the tests, a reviewer reviews, and a script commits the slice. Use when the user says "/slice:build", or when
  the slices are red.
---

# slice build

## Goal

Each slice is built, its tests pass, no major finding is open, and it is one commit.

## Inputs

- The slice that the user names, else the first slice that is not `done` or `stopped`.

## Outputs

- Code from `slice:implementer`, then `slice.py commit <Sn>`: the subject "Slice Sn: <title>" and the trailer `Slice: Sn`. The slice is `done`.
- At a limit, `stopped` with the reason, and a question for the user.

## Constraints

- `slice.py` means `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py`. Give the implementer only the results of `slice.py test <Sn>`, not test code.
- Test loop: `slice.py set <Sn> building`. Then, before each implementer run (at most 5), `slice.py round <Sn> test`, and after it `slice.py test <Sn>`.
- Review loop, when the tests pass: `slice.py set <Sn> review`. Then, before each `slice:reviewer` run (at most 3), `slice.py round <Sn> review`. Send `slice/review/<Sn>.md` to the implementer, then run the tests again.
- A refused round stops the slice. Show what fails, and ask the user.
- Start each agent in the foreground.

## Done when

- Each slice is `done`, or `stopped` and the user is asked.
