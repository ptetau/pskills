---
name: board
description: >
  Shows pdlc's state on a board like Linear or Jira through the tracker port. One card per
  intent, one sub-card per change, each in the column that matches its stage. Use when the
  user says "/pdlc:board" or wants the board brought up to date.
---

# pdlc board

> Skeleton. Not built yet. See the plugin's `OUTLINE.md`, section 9.

## What it does

Makes the board match pdlc. pdlc is the truth; the board only shows it.

## Reads

- Every intent and change, and their status.
- `config.md`: the tracker adapter and the stage-to-column map.

## Writes

- Cards on the board, through the tracker port.
- The card key, back into each intent file.

## Steps

1. If no tracker adapter is set, say so and stop.
2. For each intent, find or create its card. Move it to its stage's column.
3. For each change, find or create its sub-card. Move it too.
4. Link each card to its intent file and PR.
5. Report anything that was out of step.

## Rules

- v1 only writes to the board. It never acts on moves made on the board.
