---
name: build
description: >
  Builds one slice, then runs the test-writer against the boundary and spec, then runs the reviewer on both code and tests. Use when the user says "/slice:build", or when the domain is mapped.
model: claude-sonnet-5-5
effort: medium
---

# slice build

## Goal

One slice is built, passes its acceptance tests, has no open major finding, and is one commit.

## Inputs

- `Sn` from `slice.py next` (`build Sn`) and `slices.md`, or the user. Build that slice only.

## Outputs

- Code and unit tests from `slice:implementer` in source folders, `source files`, and `unit tests folder`. Read by `slice.py` and `slice:reviewer`.
- Acceptance tests from `slice:test-writer` in the tests folder, and reviews from `slice:reviewer`. Read by `slice.py` and agents.
- `slice.py commit <Sn> [--summary TEXT]`: subject "Slice Sn: <title>", clear summary, trailer `Slice: Sn`.
- A line that says what starts, and a recap.

## Constraints

- `slice.py` is `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py`. Run `slice.py set <Sn> building`, then `slice:implementer` (`model: opus` on `- Tier: hard`, or from test round 3).
- Next, run `slice:test-writer` to write `Sn` tests (`test_NNN_Sn_Rn_<what>`), then `slice.py test <Sn>`.
- Run `slice.py set <Sn> review`, `slice.py round <Sn> review`, and `slice:reviewer` on code and tests right away.
- Open findings in `review/<Sn>.tests.md` go to `slice:test-writer` and not to the implementer. Then re-run `slice.py test <Sn>`.
- Failing tests or `review/<Sn>.md` findings go to `slice:implementer`: `slice.py round <Sn> test` (max 5), `slice.py test <Sn>`, then `slice:reviewer` (max 3).
- A refused round stops the slice: ask the user, then `slice.py resume <Sn>`.
- Run agents in the foreground.
- Outputs give each reader exactly what it reads: see `contracts.json`.

## Done when

- That slice is `done`, or `stopped` and the user is asked.
