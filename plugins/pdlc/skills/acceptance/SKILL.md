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
- Four commits and a handoff. The packet of the review comes from `python3 pdlc/bin/make_packets.py IN-xxxx`.
- `pdlc.py set`. `pdlc.py commit` kinds in order: acceptance, lock-acceptance, review-acceptance, acceptance-reviewed. `pdlc.py handoff IN-xxxx acceptance tests`.

## Constraints

- `pdlc:test-writer` gets only the absolute path of the brief from
  `python3 pdlc/bin/make_packets.py IN-xxxx --brief`.
- Add a missing "acceptance file" or "acceptance" line of `pdlc/config.md` in the first commit.
- A missing "Interface" item goes into its spec and change spec as `proposed`. Only the third failed review stops the stage.
- The final reply names `/pdlc:tests` as next, or `/pdlc:build` after a send-back.

## Done when

The review passes, or each requirement of the intent is `retiring`. In the retiring case nothing is proved, and `Acceptance-File:` and `Acceptance-Locked:` stay `none`.
