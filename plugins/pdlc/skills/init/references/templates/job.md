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

## Requirements

What its user sees: the replies, output and pages of its entry points. `Source: recon`
marks a requirement that recon found in the code. No other requirement has a `Source`.

### JOB-name.R1 · Short title

Status: proposed · Intents: IN-0000

Write one or two sentences that say what must be true.

- Given ..., when ..., then ...
