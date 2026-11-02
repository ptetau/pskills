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
change starts.

## Inputs

- The user's intent, else the oldest `ready` intent that lists changes and has
  `Acceptance-Locked: none`. After a send-back, the `handoff.md` of that change.
- `pdlc/README.md`: "Acceptance checks", "Bookkeeping on main", "Where pdlc commits",
  "Commits".

## Outputs

- The intent is `building`, with `Branch:`, `Acceptance-File:`, and `Acceptance-Locked:`.
- Commits in order: "Acceptance IN-xxxx" (`Intent`, `Req`), "Lock acceptance IN-xxxx",
  "Review acceptance IN-xxxx" (packet from `python3 pdlc/bin/make_packets.py IN-xxxx`),
  "Acceptance reviewed IN-xxxx". The last three have `Intent`. On the branch of a change, each has `Change`.
- Handoff `acceptance → tests`, or `acceptance → build` after a send-back.

## Constraints

- `pdlc:test-writer` gets only the absolute path of the brief from
  `python3 pdlc/bin/make_packets.py IN-xxxx --brief`.
- `Acceptance-File:` is the "acceptance file" path of `pdlc/config.md`, with the intent ID for `{intent}`, in the ID form of the project.
- Add a missing "acceptance file" or "acceptance" line of `pdlc/config.md` in the first commit.

## Done when

The review passes, or each requirement of the intent is `retiring`. In the retiring case nothing is proved, and `Acceptance-File:` and `Acceptance-Locked:` stay `none`.
