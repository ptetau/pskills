---
name: ship
description: >
  Runs pdlc from start to end, alone: each stage of the intent and of each change, with
  the changes stacked and each merge proposed. Continues from the point where it stopped.
  Use when the user says "/pdlc:ship", "ship it", or wants pdlc to run all the way alone.
---

# pdlc ship

## Goal

Run every pdlc stage alone, with `defaults`, until each change is proposed or a stop is
recorded.

## Inputs

`pdlc/README.md` ("Stages and handoffs", "Stacked changes", "Rounds", "Commits"). Take:

1. An unmerged change where a run stopped: take its recommended answer, and give two
   new rounds.
2. New words of the user: `pdlc:intake`.
3. A named intent or change.
4. The oldest intent that is not `in review`, `done`, `paused`, or `cancelled`, and has
   no `Awaits approval:`.

If `pdlc/version.json` is older, run `/pdlc:upgrade`.

## Outputs

- Every stage for each change, also `verify` and show.
- At a stop: the reason, the decision, and the recommended answer under "Open". The
  commit "Stop CH-xxxx: <why>", or "Stop IN-xxxx: <why>".
- The reply: pull requests and GIFs in stack order, defaults taken, what waits.

## Constraints

- Stop only for a contradiction, a file outside "Files", or a third failure of a stage.
  A rate limit, a missing remote, and a long run are not stops.
- "Merge over a failed gate" and "accept a failed review" are no answers.

## Done when

Each change is proposed, or the stop is committed. `git status --porcelain` shows
nothing.
