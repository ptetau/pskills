# CAP-name · <what it can do, in a few words, starting with a capital>

Status: stub

Keep these sections, in this order, and add no others.

## What it is for

Write what this capability offers to jobs, independent of any one job. The offer can be a
store, an outside service, or plumbing that every job uses. Use two or three sentences.

## Code map

List the shared logic that this capability owns. If a file also holds job entry points,
list the file as `path/to/server.py: the rest`. See "Code maps" in `pdlc/README.md`. pdlc
uses this list to set the scope of changes.

- path/to/folder/

## Requirements

What it offers to jobs: a call and what it returns, a stored record, a shared reply or
error shape. Do not list the user-facing behaviour of one job. That behaviour belongs to the
job. `Source: recon` marks a requirement that recon found in the code. No other
requirement has a `Source`.

### CAP-name.R1 · Short title

Status: proposed · Intents: IN-0000

Write one or two sentences that say what must be true.

- Given ..., when ..., then ...
