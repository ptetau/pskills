---
name: ready
description: >
  Makes sure that the spec patches of a pdlc intent are clear enough to build. Asks the
  user about each unclear item, one question at a time, looks for contradictions in the
  specs, and marks requirements ready. Use when the user says "/pdlc:ready", or asks if
  an intent is ready to build.
---

# pdlc ready

## Goal

A test writer can write each check with no guess. No spec shows old behaviour.

## Inputs

- The intent that the user names, or the oldest `specifying` intent. The argument `defaults`.

## Outputs

- Clear `proposed` requirements become `ready`.
- The handoff `ready → change`, or `ready → user` at a stop.
- The commit "Ready IN-xxxx: <name>" with trailer `Intent`, also at a stop.
- The reply: what changed, and `/pdlc:change` next.

## Constraints

- `pdlc/README.md` binds, in particular "Bookkeeping on main", "Spec patches", and "Questions".
- Settle implied behaviour: missing, empty, wrong-type, and too-large input, limits, order, existing data, unsafe input, and business rules. A missing design spec goes through `pdlc:conventions`. Each failure line, also for an existing error, names a code in `DES-errors`.
- Each line of the intent's requirements, also an existing or `ready` line, gives concrete values and exact output, not "any file" or "the same error".
- The order of two errors comes from the plain words of the intent, not code, and the sentences of both requirements name the exception.
- Each `(assumed)` mark has `<requirement>: <question> → <answer> (assumed)` in "Notes" and "Decided on defaults".
- A contradiction stays `proposed`: the user selects, also with `defaults`.
- After three failed runs of `python3 pdlc/bin/check_handoff.py IN-xxxx --stage ready`, put the problems under "Open" and stop.

## Done when

- The intent is `ready`, each requirement is `ready` or `retiring`, and the check exits 0. Or ready stopped.
