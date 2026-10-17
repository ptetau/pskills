# Port: tracker

The tracker port shows the state of pdlc on a board. The pdlc files are the truth. The
board only shows that state.

## Operations

- **show intent**: the input is the ID, name, status, and links of an intent. Create or
  update the card of the intent in the column for that status. Return the card key.
- **show change**: the input is the ID, name, status, intent, and links of a change.
  Create or update the sub-card of the change under the card of the intent.

The "Board columns" section of `pdlc/config.md` gives the column for each status.

## Success

If the port shows the same intent two times, the port updates one card, and does not make
a second card.

## Conformance check

1. Show a test intent with the status `new`. A card appears in the `new` column.
2. Show the test intent again with the status `ready`. The same card moves to the `ready`
   column.
3. Remove the card.

In v1, the port only writes to the board. A later version will also act on moves on the
board.
