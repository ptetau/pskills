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
change starts. They prove each acceptance line as a user meets it, and fail until the last
change of the intent is built ("Acceptance checks" in `pdlc/README.md`).

## Constraints

- The rules of `pdlc/README.md` hold, and "Bookkeeping on main" runs first. Red, lock, and
  review obey "Checks before code". The test writer and the reviewer obey "Who does what".
- The intent is the one that the user names, or else the oldest `ready` intent that lists
  changes and has `Acceptance-Locked: none`. After a send-back from `/pdlc:build` or
  `/pdlc:verify`, the reason is in the `handoff.md` of that change, and app code exists.
- The work is at the top of the stack of the intent. The top is the branch of its newest
  change that has a branch, or the intent branch before the first change.
- With `Branch: none`, the delivery port starts the intent branch ("Where pdlc commits"),
  from the newest unmerged pdlc branch, or else from main.
- When each requirement of the intent is `retiring`, there is nothing to prove.
  `Acceptance-File:` and `Acceptance-Locked:` stay `none`, and only the finish remains.
- A `pdlc/config.md` with no "acceptance file" line or no "acceptance" line gets them, as
  `/pdlc:init` writes them, in the commit of the acceptance file.
- `Acceptance-File:` holds the "acceptance file" path of `pdlc/config.md`, with the intent
  ID for `{intent}`, in the ID form of the project.
- The `pdlc:test-writer` agent gets the absolute path of the intent file and nothing else,
  and writes the acceptance file. After a failed review, the prompt also holds the
  problems as text ("Checks before code").
- The test writer can remove a check from the acceptance file of an earlier intent, when
  this intent changes or retires its requirement. This intent proves the new line.
- Red runs through **run acceptance** of the checks port. On the branch of a change, each
  commit also has the trailer `Change`.
- A new lock makes an old `Acceptance-Passed:` out of date. The merge check finds both.

## Inputs

- `pdlc/README.md`, the shared rules.
- The intent, its "Handoff", the change specs of its "Changes", and `pdlc/config.md`.
- After a send-back, the `handoff.md` of the change that sent the intent back.

## Outputs

- The intent is `building`, with `Branch:`, `Acceptance-File:`, and the lock hash on
  `Acceptance-Locked:`.
- The commits, in this order:
  - "Acceptance IN-xxxx" with the trailers `Intent` and `Req`: the acceptance files, the
    intent, and any new `config.md` lines.
  - "Lock acceptance IN-xxxx" with the trailer `Intent`: the lock line.
  - "Review acceptance IN-xxxx" with the trailer `Intent`: the packet from
    `python3 pdlc/bin/make_packets.py IN-xxxx` and the result, in
    `pdlc/acceptance/IN-xxxx-…/review/tests/`.
  - "Acceptance reviewed IN-xxxx" with the trailer `Intent`: the handoff.
- The handoff `acceptance → tests` in the intent: the checks, the lock, and what each
  change must give the checks. After a send-back, the handoff `acceptance → build` in the
  `handoff.md` of that change.
- For the user: `/pdlc:tests` is next, or `/pdlc:build` after a send-back.
- The stage is done when the review passes, or when the intent only retires requirements.
  The third failed review stops the stage ("Rounds").
