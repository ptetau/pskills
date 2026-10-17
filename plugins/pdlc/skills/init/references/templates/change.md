# CH-0000 · Short name

Intent: IN-0000 · Scope: CAP-name · Status: planned · Ticket: none · Branch: none · Base: main

## Delivers

Write one or two sentences: what is true when this change merges.

## Requirements

Copy the requirements from the specs, with their acceptance checks. Add ` (retire)` to the
heading of a requirement that this change removes.

### CAP-name.R1 · Short title

- Given ..., when ..., then ...

## Relies on

- CAP-... (used, not changed)
- DES-... (conventions to follow)

## Interface

List what the checks can call, so that the test writer can write the checks without the
code. Give the file of each entry. Give what goes in and what comes out, with types where
the language has them. Give each error that the entry can give, by its code from
`DES-errors`.

- `send(template: TemplateName, to: Email) -> SentId` in `src/email.js`
  - errors: `TEMPLATE_NOT_FOUND`, `INVALID_ADDRESS`

### Test seams

Say how a check controls what it cannot wait for or reach: the clock, randomness, and
outside vendors or stores. If the checks need no test seams, write "none".

- clock: `send(..., { now })` takes the current time

## Files

List the app files that this change can touch. The builder changes only these files.

- path/to/file

## Check files

List the check files for this change. Only the test writer writes these files.

- path/to/check

## Steps

### Step 1 · Short name · [ ]

- Requirement: CAP-name.R1
- Check: the check that proves the requirement, named with the requirement ID
- Done when: the check passes

## Manual checks

List the acceptance checks that cannot be automated. At merge, the user makes sure that
these checks pass. If there are no manual checks, write "none".

## Progress log

Add the newest entry last. Record decisions, not only actions.
