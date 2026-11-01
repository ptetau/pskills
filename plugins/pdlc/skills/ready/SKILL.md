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

A test writer can write each check with no guess. Each requirement is clear and `ready`. No spec shows old behaviour.

## Inputs

- `pdlc/README.md`: "Spec patches", "Questions".
- The intent that the user names, or the oldest `specifying` intent. The argument `defaults`.

## Outputs

- Each `proposed` requirement becomes `ready`; `retiring` stays.
- The handoff `ready → change`, or `ready → user` at a stop.
- The commit "Ready IN-xxxx: <name>" with trailer `Intent`, also at a stop.

## Constraints

- Settle implied behaviour: bad input, limits. Each failure line names a code in `DES-errors`.
- Lines give concrete values and exact output, not "any file".
- The order of two errors comes from the intent.
- Each `(assumed)` mark has `<requirement>: <question> → <answer> (assumed)` in "Notes" and in "Decided on defaults".
- A contradiction stays `proposed`: ask, never select, also with `defaults`.
- Run `python3 pdlc/bin/check_handoff.py IN-xxxx --stage ready`. After three failed runs, put the problems under "Open" and stop with `ready → user`.

## Done when

- Each requirement is `ready` or `retiring`, or a contradiction stopped ready.
- The check exits 0, or the stop happened. The commit exists.
