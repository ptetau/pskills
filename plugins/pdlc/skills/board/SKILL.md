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

Board makes all of the board agree with pdlc in one pass. The other skills tell the
tracker port about each new status while they work. Board is for a board that no longer
agrees with pdlc, or for a new tracker.

## Constraints

- The rules of `pdlc/README.md` hold, and "Bookkeeping on main" runs first.
- A tracker adapter `none` in `pdlc/config.md` stops the skill, and the user hears that
  there is no tracker.
- A missing setting of the adapter under "Tracker settings" stops the skill, and the user
  hears which setting is missing.
- Each column in "Board columns" is on the board. Else the skill stops, and lists each
  missing column.
- With `dry-run` and no access to the board yet, the skill does no column check, and the
  current column of each card is "unknown".
- Each intent and each change that is not `cancelled` gets a card with these items:
  - The ID, the name, the status, and the column of that status.
  - The `Ticket` (the card key), or `none`.
  - The links: the intent file, and the pull request of a change that has one.
- With `dry-run`, the skill changes no board and no file.
- Without `dry-run`, **show intent** of the tracker port runs for each intent, then
  **show change** for each change of that intent.
- The skill only writes to the board. It does not act on moves that persons make on the
  board, because that function comes later.
- The skill does not delete a card.
- The card of a cancelled intent moves to a `cancelled` column if there is one. Else the
  card does not move.

## Inputs

- `pdlc/README.md`, the tracker adapter, "Tracker settings", and "Board columns" in
  `pdlc/config.md`.
- Each intent and each change, with its status, `Ticket`, and links.
- The argument `dry-run`, if the user gives it.

## Outputs

- With `dry-run`: a table, with one row for each item, of the card key, the current
  column, and the correct column. The skill then stops.
- Without `dry-run`: the board agrees with pdlc, and each new card key is in the `Ticket`
  of its intent or change.
- If the skill wrote a `Ticket`, the commit "Board: record card keys" on main.
- For the user: how many cards the skill made, how many it moved, and how many needed no
  change.
