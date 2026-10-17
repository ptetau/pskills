# CH-0000 · Short name

Intent: IN-0000 · Scope: CAP-name · Status: planned · Ticket: none · Branch: none · Base: main
Tests-Locked: none

Keep these sections, in this order, and add no others.

## Delivers

Write one or two sentences: what is true when this change merges.

## Requirements

Copy the requirements from the specs. For each requirement, copy the heading and the
acceptance lines, in number order. Copy nothing else, and do not copy the `Status:` line.
Add ` (retire)` to the heading of a requirement that this change removes.

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
outside vendors or stores. A test seam can also be a stand-in for a surface that the
runner cannot drive, such as a page with no browser. The checks reach each test seam
through the outermost interface that they call. The test seam is an argument for a library
function, or an environment variable or a flag for a command. The README of the project
names each test seam. Write "none" only if no acceptance line needs a test seam.

- clock: `send(..., { now })` takes the current time

## Files

List the app files that this change can touch, from the code map of the spec. The builder
changes only these files. For a shared file, name the parts that belong to this spec. The
builder changes only those parts.

- path/to/file
- path/to/server.py: POST /reset route and handle_reset

## Check files

List the check files for this change. Name each file after the spec, as
`DES-pdlc-check-tagging` (check naming) tells you. Only the test writer writes these
files.

- path/to/check

## Steps

### Step 1 · Short name · [ ]

- Requirement: CAP-name.R1
- Check: the check that proves the requirement, named with the requirement ID, or
  `manual check`
- Done when: the check passes

## Manual checks

List the acceptance lines that no check can see, for example how a page looks. At merge,
the user confirms these lines. Write one line for each, in this form:
`<requirement ID> · <the acceptance line> · how to confirm it`. If there are no manual
checks, write "none".

## Progress log

Add the newest entry last. Record decisions, not only actions.
