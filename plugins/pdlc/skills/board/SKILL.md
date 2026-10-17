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

This skill makes the board agree with pdlc. The other skills tell the tracker port about
each new status while they work. This skill makes all of the board agree with pdlc in one
pass. For example, use this skill when the board no longer agrees with pdlc, or after you
configure a new tracker.

Read `pdlc/README.md` first. Obey the instructions in that file, and start with its
"Before any work" step.

## 1. Examine the setup

- Read the tracker adapter in `pdlc/config.md`. If the adapter is `none`, tell the user
  that there is no tracker. Then stop.
- Read the adapter file, and the settings for the adapter under "Tracker settings". If a
  setting is missing, tell the user which setting is missing. Then stop.
- Make sure that each column in "Board columns" is on the board. If a column is not on the
  board, list each missing column. Then stop.
- With `dry-run`, it is possible that you cannot get to the board (no access yet). In that
  condition, do not do the column check. Show the current column of each card as
  "unknown".

## 2. Find what the board must show

For each intent that is not `cancelled`, and for each change that is not `cancelled`, find
these items:

- The ID, the name, and the status.
- The column for that status, from "Board columns".
- The `Ticket` (the card key), or `none` if the intent or change has no card yet.
- The links: the intent file, and the pull request of the change, if the change has one.

## 3. Make the board agree with pdlc

If the user passed `dry-run`, do not change the board or a file. Print a table with one
row for each item. Give the card key, the current column, and the correct column. Then
stop.

If the user did not pass `dry-run`, use the tracker port:

- Use **show intent** for each intent. Then use **show change** for each change of that
  intent.
- Write each new card key into the `Ticket` of the intent or the change.

## 4. Finish

- If you wrote a `Ticket`, commit on main with the message "Board: record card keys".
- Tell the user how many cards you made and how many cards you moved. Also tell the user
  how many cards did not need a change.

## Rules

- Only write to the board. Do not act on moves that persons make on the board. That
  function comes later.
- Do not delete a card.
- If an intent is cancelled, and there is a column for `cancelled`, move the card of the
  intent to that column. If there is no such column, do not move the card.
