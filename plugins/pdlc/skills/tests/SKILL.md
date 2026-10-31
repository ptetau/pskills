---
name: tests
description: >
  Writes and locks the component checks of a pdlc change before any app code. The
  pdlc:test-writer agent writes the checks from the spec only. Each new check fails
  first, and an independent reviewer judges the checks against the spec. Use when the
  user says "/pdlc:tests", or when a change is planned and ready for its checks.
---

# pdlc tests

## Goal

The component checks of one change are written from the spec, by a test writer that does
not see the code, before any app code. The checks are red, locked, and reviewed. The
acceptance checks of the intent come earlier, from `/pdlc:acceptance`. For the only change
of an intent, the acceptance checks are its checks.

## Constraints

- The rules of `pdlc/README.md` hold, and "Bookkeeping on main" runs first. Red, lock, and
  review obey "Checks before code". The base and the branch obey "Stacked changes".
- The change is the one that the user names, or else the first `planned` change in the
  order of the intent.
- The first change of an intent needs the acceptance stage complete: the intent handoff
  has the title `acceptance → tests`. If not, `/pdlc:acceptance` runs first.
- Suppose the intent lists only this change, "Check files" is `- none`, and the intent has
  an `Acceptance-Locked` hash. Then the skill starts the branch as usual, and sets
  `Tests-Locked: acceptance` and the status `building`. No test writer and no reviewer
  run, and the skill makes no packet.
- A change that has a branch already came back from `/pdlc:build` or `/pdlc:verify`. The
  skill works on that branch, keeps its `Base:`, starts from the reason of the send-back,
  and keeps the status until the finish.
- A merge of the previous change first is not necessary, but that change is `in review`
  or `merged`. If not, its `verify` and show stages finish first.
- The delivery port starts the branch of the change ("Stacked changes").
- The `pdlc:test-writer` agent gets the absolute path of the change spec and nothing else,
  and writes the files under "Check files". After a failed review, the prompt also holds
  the problems as text ("Checks before code").
- The test writer cannot delete files. When it reports that a check file served only a
  `(retire)` requirement, the skill removes the file with `git rm` before the lock.
- Red runs the checks of each requirement through the checks port.

## Inputs

- `pdlc/README.md`, the shared rules.
- The change spec, and its `handoff.md`, or else the "Handoff" of the intent.
- The intent, its "Changes", and the branches of the earlier changes.

## Outputs

- The change spec has `Branch:`, `Base:`, and `Tests-Locked: <hash>` (or `acceptance`)
  right under its header. The change is `testing` while the checks are written, then
  `building`. The intent is `building`.
- The commits, in this order, each with the trailers `Intent` and `Change`:
  - "Start CH-xxxx": the branch, the base, and the statuses. A send-back has no new start.
  - "Tests CH-xxxx", also with `Req`: the check files.
  - "Lock tests CH-xxxx": the lock line.
  - "Review tests CH-xxxx": the packet from `python3 pdlc/bin/make_packets.py CH-xxxx tests`
    and the result, in `pdlc/changes/CH-xxxx-…/review/tests/`.
  - "Tests reviewed CH-xxxx": the status and the handoff.
- The handoff `tests → build`: the checks and what each one proves, the lock, and what
  the builder must know.
- For the only change of an intent, the commits are only these two, each with the trailers
  `Intent` and `Change`:
  - "Start CH-xxxx": the branch, the base, and the status `testing`.
  - "Tests reviewed CH-xxxx": `Tests-Locked: acceptance`, the status `building`, and the
    handoff. The handoff names the acceptance file and its lock.
- For the user: `/pdlc:build` is next.
- The stage is done when the tests review of the newest lock passes. The third failed
  review stops the stage ("Rounds"). For the only change of an intent, the stage is done
  when the handoff is committed.
