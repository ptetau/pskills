---
name: acceptance
description: >
  Writes, locks, and reviews the acceptance checks of a pdlc intent, before its first
  change starts. The pdlc:test-writer agent writes black-box checks of each acceptance
  line, through what a user uses, and an independent reviewer judges them. Use when the
  user says "/pdlc:acceptance", or when the changes of an intent are planned.
---

# pdlc acceptance

## Goal

The acceptance checks of an intent are written, red, locked, and reviewed before its first
change starts. They prove each acceptance line as a user meets it.

## Inputs

- The user's intent, else the oldest `ready` intent that lists changes and has
  `Acceptance-Locked: none`. After a send-back, the `handoff.md` of that change.
- `pdlc/README.md`: "Acceptance checks", "Bookkeeping on main", "Checks before code",
  "Who does what", "Where pdlc commits", "Rounds", "Commits".

## Outputs

- The intent is `building`, with `Branch:`, `Acceptance-File:`, and `Acceptance-Locked:`.
- Commits, in this order: "Acceptance IN-xxxx" (`Intent`, `Req`), "Lock acceptance IN-xxxx",
  "Review acceptance IN-xxxx" (packet from `python3 pdlc/bin/make_packets.py IN-xxxx`),
  "Acceptance reviewed IN-xxxx". The last three have `Intent`; on a change branch, add `Change`.
- Handoff `acceptance → tests`, or `acceptance → build` after a send-back. Next: `/pdlc:tests` or `/pdlc:build`.

## Constraints

- `pdlc:test-writer` gets only the absolute path of the brief from
  `python3 pdlc/bin/make_packets.py IN-xxxx --brief`.
- `Acceptance-File:` is the `pdlc/config.md` path, with the intent ID in the project form.
- Add a missing "acceptance file" or "acceptance" line of `pdlc/config.md` in the first commit.

## Done when

The review passes. If each requirement is `retiring`, `Acceptance-File:` and
`Acceptance-Locked:` stay `none`.
