# CH-0000 · Short name

Intent: IN-0000 · Scope: CAP-name · Status: planned · Ticket: none · Branch: none · Base: main

## Delivers

One or two sentences. What is true when this change merges.

## Requirements

Copied from the specs, with their acceptance checks. Add ` (retire)` to the heading of a
requirement this change removes.

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
browser). Write "none" only if no line needs one.

- clock: `send(..., { now })` takes the current time

## Files

App files this change may touch. The builder changes only these.

- path/to/file

## Check files

Check files for this change. Only the test writer writes these.

- path/to/check

## Steps

### Step 1 · Short name · [ ]

- Requirement: CAP-name.R1
- Check: the check that proves it, named with the requirement ID
- Done when: the check passes

## Manual checks

Acceptance checks no check can see, such as how a page looks. The user confirms them at
merge. Write "none" if there are none.

## Progress log

Newest last. Record decisions, not just actions.
