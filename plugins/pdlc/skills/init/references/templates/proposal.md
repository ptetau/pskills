# Proposal · CH-0000 · Short name

Intent: IN-0000 · Base: <the branch it merges into> · Tests-Locked: <hash, or acceptance>

Keep these sections, in this order. Write "none" under one with nothing in it.

## Visual review

The GIF, embedded as the delivery adapter says, and how many acceptance lines it shows
out of how many. Give each requirement a short description next to its ID, as in
`R5 (usage line)`. Keep each sentence at 25 words or fewer.

## Requirements and checks

| Requirement | Checks | Result |
|---|---|---|

## Acceptance checks of the intent

The acceptance file, its lock, and its review result. For the last change of the intent,
also the commit at which the acceptance checks passed. For an earlier change, write that
the checks pass at the last change.
With `Tests-Locked: acceptance`, these checks are also the checks of the change.

## Reviews

| Remit | Result |
|---|---|

Link each remit's `result.md`.

## Manual checks

Each line from the change spec's "Manual checks", for the user to confirm before the merge.

## Assumed

Every `(assumed)` detail in the change spec and its requirements, one line each, so the
user reviews them in one place.

## Merge together

The intent's other changes, in stack order, with their pull requests where they exist.
They merge together, bottom first.

## New behaviour for you to approve

Each intent verify filed for this change, by ID and name, one line each.
