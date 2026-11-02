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
- Commits, in order: `pdlc.py start CH-xxxx` (it sets `Branch:`, `Base:`, and the status,
  makes the branch, and commits "Start CH-xxxx"; never pick the base), then `pdlc.py commit`
  kinds `tests`, `lock-tests`, `review-tests` (packet from `python3 pdlc/bin/make_packets.py CH-xxxx tests`), `tests-reviewed`.
  Fields: `pdlc.py set`. Handoff: `pdlc.py handoff CH-xxxx tests build`. Next: `/pdlc:build`.

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

## Done when

The tests review of the newest lock passes. Short path: the handoff is committed.
