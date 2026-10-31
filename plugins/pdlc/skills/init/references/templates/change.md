# CH-0000 · Short name

Intent: IN-0000 · Scope: CAP-name · Status: planned · Ticket: none · Branch: none · Base: main
Tests-Locked: none

The pdlc scripts read each header field. Thus, a header field holds only its bare value.
Do not add a name in brackets, and do not add backticks. For example, write
`Intent: IN-0001`, not `Intent: IN-0001 (poll-input-errors)`.

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
- JOB-... (used, not changed: the checks call its Interface)

## Interface

Copy each entry that the checks call from the "Interface" of its spec, as you copy the
requirements. Copy each line word for word, but not the ` · proposed` mark. An entry
comes from the spec of this change, or from a job or capability under "Relies on". If no
spec has the entry, add the entry to its spec first. `bin/check_merge.py` fails the change
when an entry is not in its spec. See "Interfaces" in `pdlc/README.md`.

- `send(template: TemplateName, to: Email) -> SentId` · function · `src/email.js`
  - in: the name of a template, and an email address
  - out: the ID of the sent email
  - errors: `TEMPLATE_NOT_FOUND`, `INVALID_ADDRESS`

### Test seams

Copy each seam that the checks use from "Test seams" of its spec, in the same way. A seam
says how a check controls what it cannot wait for or reach: the clock, randomness, and
outside vendors or stores. A test seam can also be a stand-in for a surface that the
runner cannot drive, such as a page with no browser. The checks reach each test seam
through the outermost interface that they call. The test seam is an argument for a library
function, or an environment variable or a flag for a command. The README of the project
also names each seam that a user can set. Write "none" only if no acceptance line needs a
test seam.

- `EMAIL_OUTBOX_DIR` · seam: outside vendor · `src/email.js`
  - in: a folder. When it is set, `send` writes each email there as a file, and sends
    nothing.
  - errors: none

## Files

List the app files that this change can touch, from the code map of the spec. The builder
changes only these files. For a shared file, name the parts that belong to this spec. The
builder changes only those parts.

- path/to/file
- path/to/server.py: POST /reset route and handle_reset

## Check files

List the component check files for this change. Name each file after the spec, as
`DES-pdlc-check-tagging` (check naming) tells you. Only the test writer writes these
files. The acceptance checks of the intent are in a different file, and are not listed
here. If this change is the only change of its intent, and the acceptance checks of the
intent are also its checks, write `- none`.

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
