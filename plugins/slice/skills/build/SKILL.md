---
name: build
description: >
  Builds one slice. The implementer agent writes the code from the interface and the spec, and a hook keeps it out of the tests. A script runs the tests, a reviewer reviews, and a script commits the slice. Use when the user says "/slice:build", or when the slices are red.
model: claude-sonnet-5-5
effort: medium
---

# slice build

## Goal

One slice passes its tests, has no open major finding, and is one commit.

## Inputs

- `Sn` from the `build Sn` line of `slice.py next`, or from the user. Build that slice only.

## Outputs

- Code from `slice:implementer`, then `slice.py commit <Sn>`: the subject "Slice Sn: <title>" and the trailer `Slice: Sn`.
- Test fix: tests from `slice:test-writer`, then `slice.py commit tests <Sn>`: the subject "Tests Sn: <title>" and the trailer `Slice: Sn`.
- A line that says what starts, and a recap.

## Constraints

- `slice.py` is `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py`. Give the implementer results only.
- Test loop: `slice.py set <Sn> building`, then `slice.py test <Sn>`. If the tests already pass, go to review. Else, before each implementer run (at most 5), `slice.py round <Sn> test`; after it, `slice.py test <Sn>`.
- Review loop: `slice.py set <Sn> review`. Before each `slice:reviewer` run (at most 3), `slice.py round <Sn> review`. Give `review/<Sn>.md` to the implementer, then test. A test that fails after a review fix uses a test round.
- A line in `review/<Sn>.tests.md` goes to `slice:test-writer` and not to the implementer. Then run `slice.py commit tests <Sn>`. Failing tests make the slice `building`: run the test loop. A test fix uses no round of its own.
- Give the implementer `model: opus` when the slice says `- Tier: hard`, and from test round 3 of any slice.
- A refused round stops the slice: ask the user, then `slice.py resume <Sn>`.
- Run agents in the foreground.
- Outputs give each reader exactly what it reads: see `contracts.json`.

## Done when

- That slice is `done`, or `stopped` and the user is asked.
