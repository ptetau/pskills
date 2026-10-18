# Handoff · <IN- or CH-ID> · <this stage> → <next stage>

Time: <the output of `date -Iseconds`; never typed by hand>

The title is one of these, and nothing else: `intake → ready`, `ready → change`,
`change → tests`, `tests → build`, `build → show` or `show → verify`. After a failed
round, the title is `verify → tests` or `verify → build`. Once verify proposes the change,
the title is `verify → user`. When a stage stops, the title is `<this stage> → user`. Keep
every section below, in this order. Write "none" under one with nothing in it.

## Done

Write what this stage did, in a few lines. Give each requirement, intent, or change a
short description next to its ID, as in `R5 (usage line)` or `CH-0001 (top option)`.
Keep each sentence at 25 words or fewer.

## Decided on defaults

List each `(assumed)` decision that this stage wrote, so that the user can change the
decisions. Write one line for each decision, in the form of the "Notes" section of the
intent: `<requirement>: <question> → <answer> (assumed)`. Write "none" only if this stage
wrote no such decision.

- none

## Open

List each item that is unfinished, unclear, or failing.

- none

## Look here

List the files that are important for the next stage.

## Don't redo

List the work that is finished and checked. The next stage accepts this work as correct.

## Next: do this first

Write one or two sentences for the next stage.
