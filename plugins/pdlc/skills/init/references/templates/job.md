# JOB-name · <what the user gets done, in a few words, starting with a capital>

Status: stub

Keep these sections, in this order, and add no others.

## Who and why

Who does this job, and what they are trying to achieve. Two or three sentences.

## Relies on

- Capabilities: CAP-...
- Design: DES-...

## Code map

What this job owns: its entry points (routes or request handlers, commands, page scripts
or event handlers) and files that serve only it. In a file shared with other specs, name
its parts. See "Code maps" in `pdlc/README.md`. Used to scope changes.

- path/to/folder/
- path/to/server.py: POST /reset route and handle_reset

## Requirements

What its user sees: the replies, output and pages of its entry points. `Source: recon`
marks a requirement recon found in the code; no other requirement has a `Source`.

### JOB-name.R1 · Short title

Status: proposed · Intents: IN-0000

One or two sentences saying what must be true.

- Given ..., when ..., then ...
