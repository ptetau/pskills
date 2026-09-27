---
name: board
description: >
  Shows pdlc's state on a board, such as a GitHub project or Linear, through the tracker
  port. One card per intent and one per change, each in the column for its status. pdlc
  is the truth; the board only shows it. Use when the user says "/pdlc:board", or wants
  the board brought up to date. Pass "dry-run" to see what would change without touching
  the board.
---

# pdlc board

Makes the board match pdlc. Other skills tell the tracker port as they go; this skill
brings everything back in line in one pass, for example after the board drifted or a
tracker was just set up.

Read `pdlc/README.md` first and follow it. Start with its "Before any work" step.

## 1. Check the setup

- Read the tracker adapter in `pdlc/config.md`. If it is `none`, say so and stop.
- Read the adapter file and its settings under "Tracker settings". If a setting is missing,
  say which one and stop.
- Check that every column in "Board columns" exists on the board. List any that don't and
  stop.
- With `dry-run`, the board may be out of reach (no access yet). Then skip the column check
  and show each card's current column as "unknown".

## 2. Work out what should be shown

For each intent that isn't `cancelled`, and each change that isn't `cancelled`:

- its ID, name and status;
- the column for that status, from "Board columns";
- its `Ticket` (the card key), or `none` if it has no card yet;
- links: the intent file, and the change's pull request if it has one.

## 3. Bring the board in line

If the user passed `dry-run`, don't touch the board or any file. Print a table of each
item, its card key, its column now and the column it should be in, then stop.

Otherwise, through the tracker port:

- **show intent** for each intent, then **show change** for each of its changes.
- Write any new card key into the intent's or change's `Ticket`.

## 4. Finish

- If any `Ticket` was written, commit on main with the message "Board: record card keys".
- Tell the user how many cards were created, how many moved, and how many were already
  right.

## Rules

- Only write to the board. Never act on moves made on the board. That comes later.
- Never delete a card. If an intent is cancelled, move its card to the column for
  `cancelled` if there is one, and otherwise leave it.
