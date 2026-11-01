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

## Interface

List the calls that jobs use, each with its file. A check calls the capability only
through these entries, so a rebuild from the specs must keep each name. See "Interfaces"
in `pdlc/README.md`.

The first line of an entry gives the name in backticks, the kind, and the file. Under it,
give what goes in, what comes out, and each error on its own line: the code from
`DES-errors`, the exact message, and `raises <Name>`. A new entry ends its first line with
` · proposed`.

- `send(template: TemplateName, to: Email) -> SentId` · function · `src/email.js`
  - in: the name of a template, and an email address
  - out: the ID of the sent email
  - errors:
    - `TEMPLATE_NOT_FOUND` · `no template named <name>` · raises `TemplateNotFound`
    - `INVALID_ADDRESS` · `not a valid email address: <address>` · raises `InvalidAddress`

### Test seams

List each seam that this capability gives to checks. A seam controls the clock,
randomness, or an outside vendor or store. Write "none" if no acceptance line needs a
seam.

- `EMAIL_OUTBOX_DIR` · seam: outside vendor · `src/email.js`
  - in: a folder. When it is set, `send` writes each email there as a file, and sends
    nothing.
  - errors: none

## Requirements

What it offers to jobs: a call and what it returns, a stored record, a shared reply or
error shape. Do not list the user-facing behaviour of one job. That behaviour belongs to the
job. `Source: recon` marks a requirement that recon found in the code. No other
requirement has a `Source`.

### CAP-name.R1 · Short title

Status: proposed · Intents: IN-0000

Write one or two sentences that say what must be true. Keep each sentence at 25 words or
fewer, also in each acceptance line below. Give each ID a short description, as in
`R5 (usage line)`.

- Given ..., when ..., then ...
