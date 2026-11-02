---
name: ship
description: >
  Runs pdlc from start to end, alone: each stage of the intent and of each change, with
  the changes stacked and each merge proposed. Continues from the point where it stopped.
  Use when the user says "/pdlc:ship", "ship it", or wants pdlc to run all the way alone.
---

# pdlc ship

## Goal

Run each stage through its own skill, with `defaults`, until each change is proposed or stopped.

## Inputs

`pdlc/README.md` ("Core rules", "Bookkeeping on main", "Stages and handoffs", "Stacked changes", "Where pdlc commits", "Rounds", "Questions", "Who does what", "New behaviour needs approval", "Commits", "Layout"). Take:

1. An unmerged stopped change: take its recommended answer, and give two
   new rounds. A contradiction still waits for the user.
2. New user words: `pdlc:intake`.
3. A named intent or change.
4. The oldest intent that is not `in review`, `done`, `paused`, or `cancelled`, and has
   no `Awaits approval:`.

If `pdlc/version.json` is older, run `/pdlc:upgrade`.

## Outputs

- Each change gets `verify` and show.
- At a stop: under "Open", the reason in one sentence, what the user must decide, and the recommended answer. The reply says the same. Commit
  "Stop CH-xxxx: <why>" or "Stop IN-xxxx: <why>", with the trailers of "Commits" in one block.
- The reply: pull requests and GIFs in stack order.

## Constraints

- Stop only for a contradiction, a file outside "Files", or a third failure of a stage.
  A missing "Interface" entry, a rate limit, a missing remote, and a long run are not stops.
- "Merge over a failed gate" and "accept a failed review" are no answers.

## Done when

`git status --porcelain` is empty.
