# Port: tracker

Shows pdlc's state on a board. pdlc is the truth. The board only shows it.

## Operations

- **show intent**: given an intent's ID, name, status and links, create or update its card
  in the column for that status. Return the card key.
- **show change**: given a change's ID, name, status, intent and links, create or update its
  sub-card under the intent's card.

The column for each status comes from "Board columns" in `pdlc/config.md`.

## Success

Showing the same intent twice updates one card. It never makes two.

## Conformance check

1. Show a test intent with status `new`. A card appears in the `new` column.
2. Show it again with status `ready`. The same card moves to the `ready` column.
3. Remove the card.

v1 only writes to the board. Acting on moves made on the board comes later.
