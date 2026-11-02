---
name: board
description: >
  Shows the state of pdlc on a board, for example a GitHub project or Linear, through the
  tracker port. Each intent and each change has one card, in the column for its status.
  pdlc is the truth, and the board only shows the truth. Use when the user says
  "/pdlc:board", or wants to update the board. Pass "dry-run" to see the changes that the
  board needs. With "dry-run", the skill does not change the board.
---

# pdlc board

## Goal

The board agrees with pdlc. Each intent and change that is not `cancelled` has one
card, in the column of its status. pdlc is the truth.

## Inputs

- `pdlc/README.md`: "Bookkeeping on main", "Where pdlc commits".
- `pdlc/config.md`: the tracker adapter, "Tracker settings", "Board columns".
- The argument `dry-run`, or a request only to look.

## Outputs

- With `dry-run`: a table of card key (or `none`), current column, correct column
  for each item. Nothing changes.
- Else **show intent** for each intent, then **show change** for each of its changes.
  Each new card key goes into the item's `Ticket`: `pdlc.py set <ID> --ticket <key>`,
  then `pdlc.py commit board`.
- Counts of cards made, moved, unchanged.

## Constraints

- The adapter `none`, a missing setting, or a missing column stops the skill.
- With `dry-run` and no board access, skip the column check. Columns show "unknown".
- Only write to the board. Delete no card.
- The card of a cancelled item moves to a `cancelled` column if there is one.

## Done when

The board agrees, or the table is shown. Each stop names its gap. The reply states only
what the run saw.
