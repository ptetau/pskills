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
- The acceptance files to pass: each other intent whose `Acceptance-Passed:` holds a
  hash, and, for the last change under "Changes", this intent. Give `pdlc:builder` the paths.

## Outputs

- "Build CH-xxxx: <what changed>": the app files. Trailers: `Intent`, `Change`, `Req`,
  `Ticket`.
- Each requirement `built`. A `(retire)` requirement leaves its spec.
- The handoff `build → verify`.
- "Built CH-xxxx", with `Intent` and `Change`: specs, change spec, handoff.
- The reply names `/pdlc:verify`.

## Constraints

- Follow `pdlc/README.md`: "Bookkeeping on main", "Who does what", "Rounds", "Commits".
- `Tests-Locked:` with no hash and no `acceptance`: stop; `/pdlc:tests` comes first.
- New base commits: merge the base first, with `Intent` and `Change`.
- The builder changes only app files under "Files". Another file is a question for the user.
- A check called incorrect stays. Send the reason to `/pdlc:tests`, or `/pdlc:acceptance`.

## Done when

- All checks pass, through the checks port.
- `git diff --name-only <Tests-Locked hash> -- <check files>` shows nothing. With
  `Tests-Locked: acceptance`, count from `Acceptance-Locked`.
