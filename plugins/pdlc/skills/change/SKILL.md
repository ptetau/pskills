---
name: change
description: >
  Makes one or more change specs from a ready pdlc intent. Each change covers exactly one
  job, one capability, or one design spec. Each change lists the interface that its
  checks are permitted to call, and only the files that it is permitted to touch.
  Capability changes come before the jobs that need them. Use when the user says
  "/pdlc:change", or wants to plan the work for a ready intent.
---

# pdlc change

## Goal

Divide a `ready` intent into changes, one spec each, in the order of what each needs.
Each change spec lets the test writer work without the code.

## Inputs

The intent that the user names, else the oldest `ready` one.

## Outputs

- `pdlc/changes/CH-xxxx-<short-name>/change.md` from `pdlc/templates/change.md`:
  `Status: planned`, `Branch: none`, `Base: main`. "Requirements" are word for word.
  "Relies on" has `used, not changed`, `DES-writing-style`, `DES-pdlc-check-tagging`,
  `DES-errors`.
- New "Interface" entries in their specs, with ` · proposed`.
- Handoff `change → acceptance`.
- The commit "Plan IN-xxxx: <names of changes>", trailer `Intent`, after
  `python3 pdlc/bin/check_order.py IN-xxxx` exits 0.
- The reply: `/pdlc:acceptance` next.

## Constraints

- `pdlc/README.md` binds, in particular "Bookkeeping on main" and "Interfaces".
- Not `ready` (`/pdlc:ready` first), or a need-cycle that no change breaks: stop with `change → user`.
- "Interface" lets the checks drive the user surface. A command error gets `stderr` or
  `stdout`. A new name has `(assumed)`.
- A seam sits at the outermost interface, or, with no runner, is a `stand-in`. A
  missing tool is not a stop.
- A job change lists README in "Files". Its step is last, "Check" `none`.

## Done when

`check_order.py` exits 0.
