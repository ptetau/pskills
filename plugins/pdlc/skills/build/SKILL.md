---
name: build
description: >
  Builds one pdlc change whose checks are written and locked. The pdlc:builder agent
  writes app code until the checks pass, and cannot change the checks. Commits with trace
  trailers, and marks the requirements as built. Use when the user says "/pdlc:build", or
  when the tests of a change are locked and reviewed.
---

# pdlc build

## Goal

Make the locked checks of one change pass with app code.

## Inputs

- The change that the user names, else the first `building` one.
- Acceptance files: each other intent whose `Acceptance-Passed:` holds a
  hash, and, for the last change under "Changes", this intent. Give `pdlc:builder` the paths.

## Outputs

- Commits: `pdlc.py commit build` (the app files), then `pdlc.py commit built` (specs,
  change spec, handoff).
- `pdlc.py set CH-xxxx --reqs built` (also ticks the steps, logs the build). A `(retire)` requirement leaves its spec.
- The handoff `build → verify`.
- The reply names `/pdlc:verify`.

## Constraints

- Follow `pdlc/README.md`: "Bookkeeping on main", "Who does what", "Where pdlc commits",
  "Acceptance checks", "Interfaces", "Rounds", "Commits".
- `Tests-Locked:` with no hash and no `acceptance`: stop. `/pdlc:tests` comes first.
- New base commits: merge the base with `git merge --no-ff -F` and `pdlc.py message merge --base`.
- The builder changes only app files under "Files". Ask the user about another file.
- A check called incorrect stays. Send the reason: `pdlc.py handoff CH-xxxx build tests` (or `build acceptance`), then `pdlc.py commit update CH-xxxx --text "<check> sent back"`.

## Done when

- All checks pass, through the checks port.
- `git diff --name-only <Tests-Locked hash> -- <check files>` shows nothing. With
  `Tests-Locked: acceptance`, count from `Acceptance-Locked`.
