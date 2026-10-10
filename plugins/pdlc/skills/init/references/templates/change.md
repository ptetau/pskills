# CH-0000 · Short name

Intent: IN-0000 · Scope: CAP-name · Status: planned · Ticket: none · Branch: none · Base: main
Tests-Locked: none

Keep these sections, in this order, and add no others.

## Delivers

One or two sentences. What is true when this change merges.

## Requirements

Copied from the specs: each heading and its acceptance lines, in number order, and
nothing else (no `Status:` line). Add ` (retire)` to the heading of a requirement this
change removes.

### CAP-name.R1 · Short title

- Given ..., when ..., then ...

## Relies on

- CAP-... (used, not changed)
- DES-... (conventions to follow)

## Interface

What the checks may call, so the test writer never needs to see the code. For each entry:
the file it lives in, what goes in and what comes out (with types where the language has
them), and every error it can give, by code from `DES-errors`.

- `send(template: TemplateName, to: Email) -> SentId` in `src/email.js`
  - errors: `TEMPLATE_NOT_FOUND`, `INVALID_ADDRESS`

### Test seams

How a check controls what it can't wait for or reach: the clock, randomness, outside
vendors or stores, and a stand-in for a surface the runner can't drive (a page with no
browser). Each seam is reached through the outermost interface the checks call: an
argument for a library function, an environment variable or a flag for a command, named
in the README. Write "none" only if no line needs one.

- clock: `send(..., { now })` takes the current time

## Files

App files this change may touch, from the spec's code map. The builder changes only
these. A shared file names this spec's parts; only those parts change.

- path/to/file
- path/to/server.py: POST /reset route and handle_reset

## Check files

Check files for this change, named after the spec as `DES-pdlc-check-tagging` says. Only
the test writer writes these.

- path/to/check

## Steps

### Step 1 · Short name · [ ]

- Requirement: CAP-name.R1
- Check: the check that proves it, named with the requirement ID, or `manual check`
- Done when: the check passes

## Manual checks

Acceptance lines no check can see, such as how a page looks. The user confirms them at
merge. One line each: `<requirement ID> · <the acceptance line> · how to confirm it`.
Write "none" if there are none.

## Progress log

Newest last. Record decisions, not just actions.
