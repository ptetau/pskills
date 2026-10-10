# CAP-name · <what it can do, in a few words, starting with a capital>

Status: stub

Keep these sections, in this order, and add no others.

## What it is for

What this capability offers to jobs, independent of any one job: a store, an outside
service, or plumbing every job uses. Two or three sentences.

## Code map

The shared logic it owns. Where a file also holds job entry points, list it as
`path/to/server.py: the rest`. See "Code maps" in `pdlc/README.md`. Used to scope
changes.

- path/to/folder/

## Requirements

What it offers to jobs: a call and what it returns, a stored record, a shared reply or
error shape. Never one job's user-facing behaviour; that belongs to the job.
`Source: recon` marks a requirement recon found in the code; no other requirement has a
`Source`.

### CAP-name.R1 · Short title

Status: proposed · Intents: IN-0000

One or two sentences saying what must be true.

- Given ..., when ..., then ...
