# CH-0000 · Short name

Intent: IN-0000 · Scope: CAP-name · Status: planned · Ticket: none · Branch: none · Base: main
Tests-Locked: none

Keep these sections, in this order, and add no others.

## Delivers

One or two sentences. What is true when this change merges.

## Requirements

Copy from the specs each heading and its acceptance lines, in number order, and nothing
else (no `Status:` line). Add ` (retire)` to the heading of a requirement this change
removes.

### CAP-name.R1 · Short title

- Given ..., when ..., then ...

## Relies on

- CAP-... (used, not changed)
- DES-... (conventions to follow)

## Interface

What the checks may call, so the test writer never needs to see the code. For each entry,
give the file it lives in, and what goes in and what comes out. Give types where the
language has them. List every error the entry can give, by its code from `DES-errors`
(the project's error codes).

- `send(template: TemplateName, to: Email) -> SentId` in `src/email.js`
  - errors: `TEMPLATE_NOT_FOUND`, `INVALID_ADDRESS`

### Test seams

How a check controls what it can't wait for or reach: the clock, randomness, and outside
vendors or stores. A seam can also stand in for a surface the runner can't drive, such as
a page with no browser. The checks reach each seam through the outermost interface they
call. A seam is an argument for a library function, or an environment variable or a flag
for a command. The README names each seam. Write "none" only if no acceptance line
needs a seam.

- clock: `send(..., { now })` takes the current time

## Files

App files this change may touch, from the spec's code map. The builder changes only
these. A shared file names this spec's parts. Only those parts change.

- path/to/file
- path/to/server.py: POST /reset route and handle_reset

## Check files

Check files for this change, named after the spec as `DES-pdlc-check-tagging` (check
naming) says. Only the test writer writes these.

- path/to/check

## Steps

### Step 1 · Short name · [ ]

- Requirement: CAP-name.R1
- Check: the check that proves it, named with the requirement ID, or `manual check`
- Done when: the check passes

## Manual checks

Acceptance lines no check can see, such as how a page looks. The user confirms them at
merge. One line each: `<requirement ID> · <the acceptance line> · how to confirm it`. If
there are none, write "none".

## Progress log

Newest last. Record decisions, not just actions.
