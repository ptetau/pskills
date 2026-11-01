# JOB-name · <what the user gets done, in a few words, starting with a capital>

Status: stub

Keep these sections, in this order, and add no others.

## Who and why

Write who does this job, and what they try to achieve. Use two or three sentences.

## Relies on

- Capabilities: CAP-...
- Design: DES-...

## Code map

List what this job owns: its entry points, and the files that serve only this job. An entry
point is a route or request handler, a command, a page script, or an event handler. If a
file is shared with other specs, name the parts of this job in that file. See "Code maps"
in `pdlc/README.md`. pdlc uses this list to set the scope of changes.

- path/to/folder/
- path/to/server.py: POST /reset route and handle_reset

## Interface

List what the user of this job touches. A check drives the job only through these
entries, so a rebuild from the specs must keep each name. List each command and flag,
route, form field, and page element or page text that a check reads. See "Interfaces" in
`pdlc/README.md`.

The first line of an entry gives the name in backticks, the kind, and the file. Under it,
give what goes in, what comes out, and each error on its own line. An error line has the
code from `DES-errors`, the exact message, and `exit <n>` or `status <n>`. A command error
then gives `stderr` or `stdout`: the stream that gets the message. See "Interfaces" in
`pdlc/README.md`. A new entry ends its first line with ` · proposed`.

- `POST /reset` · route · `path/to/server.py`
  - in: the form field `email`, an email address
  - out: status 303 to `/reset/sent`, a page that shows "Check your email"
  - errors:
    - `INVALID_ADDRESS` · `error: the email address is not valid` · status 400

- `tool [--limit N] FILE` · command · `path/to/cli.py`
  - in: the path of a file, and an optional number N, greater than zero
  - out: on standard output, one line for each item. The exit code is 0.
  - errors:
    - `LIMIT_INVALID` · `error: --limit needs a whole number greater than zero` · exit 2 · stderr

### Test seams

List each seam that a check of this job sets at the surface of the user. A seam controls
the clock, randomness, or an outside vendor. For a command, the seam is an environment
variable or a flag. Write "none" if no acceptance line needs a seam.

- `APP_NOW` · seam: clock · `path/to/server.py`
  - in: an ISO 8601 time that the app uses in place of the real clock
  - errors: none

## Requirements

What its user sees: the replies, output and pages of its entry points. `Source: recon`
marks a requirement that recon found in the code. No other requirement has a `Source`.

### JOB-name.R1 · Short title

Status: proposed · Intents: IN-0000

Write one or two sentences that say what must be true. Keep each sentence at 25 words or
fewer, also in each acceptance line below. Give each ID a short description, as in
`R5 (usage line)`.

- Given ..., when ..., then ...
