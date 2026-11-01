# Handoff · <IN- or CH-ID> · <this stage> → <next stage>

Time: <the output of `date -Iseconds`; never typed by hand>

The title is one of these, and nothing else: `intake → ready`, `ready → change`,
`change → acceptance`, `acceptance → tests`, `tests → build`, `build → verify` or
`verify → show`. After a failed round, the title is `verify → tests`, `verify → build` or
`verify → acceptance`. After the acceptance stage corrects a check for a change, the title
is `acceptance → build`. When the recording shows that the app does not meet an acceptance
line, the title is `show → build`.

Once show proposes the change, the title is `show → user`. When a stage stops, the
title is `<this stage> → user`. Keep every section below, in this order. Write "- none"
under one with nothing in it.

## Done

Write what this stage did, in a few lines. Give each requirement, intent, or change a
short description next to its ID, as in `R5 (usage line)` or `CH-0001 (top option)`.
Keep each sentence at 25 words or fewer.

## Decided on defaults

List each `(assumed)` decision that this stage wrote. Write one line for each decision:
`- <requirement>: <question> → <answer> (assumed)`. `<requirement>` is the ID of the
requirement or spec that holds the mark. Copy the same line into the "Notes" of the intent.

Each `(assumed)` line that this stage adds to the Notes is also here. A pointer such as
"see Notes" is not a list. Write "- none" only if this stage wrote no `(assumed)` mark.

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
