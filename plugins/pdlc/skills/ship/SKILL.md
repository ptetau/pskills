---
name: ship
description: >
  Runs pdlc from start to end, alone: each stage of the intent and of each change, with
  the changes stacked and each merge proposed. Continues from the point where it stopped.
  Use when the user says "/pdlc:ship", "ship it", or wants pdlc to run all the way alone.
---

# pdlc ship

## Goal

Run `python3 pdlc/bin/pdlc.py next`, run that stage through its own skill with `defaults`, and repeat. Never choose the order.

## Inputs

`pdlc/README.md` ("Core rules", "Bookkeeping on main", "Stages and handoffs", "Stacked changes", "Where pdlc commits", "Rounds", "Questions", "Who does what", "New behaviour needs approval", "Commits", "Layout"). Take:

1. A stopped intent or change: take its recommended answer, run `pdlc.py next --resume`, and give two new rounds. A contradiction still waits for the user.
2. New user words: `pdlc:intake`.
3. A named intent or change: `pdlc.py next <ID>`.

If `pdlc/version.json` is older, run `/pdlc:upgrade`.

## Outputs

- At a stop: `python3 pdlc/bin/pdlc.py stop <ID> --stage <stage> --json -`, with `open` {reason, decide, recommend}. The reply repeats its "Open".
- One line per stage. The reply: a short recap, then pull requests and GIFs in stack order.

## Constraints

- Stop only for a contradiction from ready, a file outside "Files", or a third failure of a stage.
  A missing "Interface" entry, a rate limit, a missing remote, or a long run is no stop.
- "Merge over a failed gate" and "accept a failed review" are no answers.

## Done when

`pdlc.py next` prints `done` or `stopped <ID>: <reason>`, and `git status --porcelain` is empty.
