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

The checks of one change exist before any app code: red, locked, and reviewed.

## Inputs

The change that the user names, else the first `planned` one. Its `handoff.md`.

## Outputs

- Fields `Branch:`, `Base:`, `Tests-Locked: <hash>`. The change is `testing`, then
  `building`. The intent is `building`.
- Commits, each with `Intent` and `Change`. Order: "Start CH-xxxx", "Tests CH-xxxx"
  (also `Req`), "Lock tests CH-xxxx", "Review tests CH-xxxx" (packet from
  `python3 pdlc/bin/make_packets.py CH-xxxx tests`), "Tests reviewed CH-xxxx".
- Handoff `tests → build` names each check, the requirement it proves, and the lock hash. Next: `/pdlc:build`.

## Constraints

- `pdlc/README.md` binds, in particular "Bookkeeping on main", "Checks before code",
  and "Stacked changes".
- The first change needs the handoff `acceptance → tests`, else run `/pdlc:acceptance`.
- Short path: the intent lists only this change, "Check files" is `- none`, and the
  intent has `Acceptance-Locked`. Then no writer, reviewer, or packet. Only "Start
  CH-xxxx" and "Tests reviewed CH-xxxx", with `Tests-Locked: acceptance`.
- `pdlc:test-writer` gets only the absolute path of the brief from
  `python3 pdlc/bin/make_packets.py CH-xxxx --brief`, and writes only "Check files".
  `git rm` a file that served only a `(retire)` requirement.
- Keep the trailers in one block, as README "Commits" says.

## Done when

The tests review of the newest lock passes. Short path: the handoff is committed.
