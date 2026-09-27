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

What the checks may call, so the test writer never needs to see the code: function names
and arguments, commands and flags, routes, page elements. Each with the file it lives in.

- `name(args)` in `path/to/file`

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

Acceptance checks that can't be automated. The user confirms them at merge. Write "none"
if there are none.

## Progress log

Newest last. Record decisions, not just actions.
