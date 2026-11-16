---
name: interface
description: >
  Designs the one test surface that all the slices need, for example HTTP endpoints or the public functions of a module. Creates it as stubs, and has the test-writer agent write red acceptance tests against it. Use when the user says "/slice:interface", or when the domain is mapped.
model: claude-opus-5-5
effort: medium
---

# slice interface

## Goal

One smallest interface, good practice for the stack, serves all the slices. Each slice has tests that fail only on missing behaviour.

## Inputs

- `spec.md`, `slices.md`, `domain.md` in `slice/NNN-<name>/`; `slice/config.md`.

## Outputs

- `slice/NNN-<name>/interface.md` from the template, with its `Status:` and `- Changed:` lines. Read by the test writer, implementer, and reviewer. It gives the call forms.
- Stubs in the source folders and `source files`, failing with the not-implemented error of the stack (message "not implemented"). Read by the implementer.
- Tests from `slice:test-writer`, named `test_NNN_Sn_Rn_<what>`, in the tests folder. Read by `slice.py`.
- Each slice `red`: `slice.py set <Sn> red` once `slice.py test <Sn> --red` exits 0, for every slice before any build. Then `slice.py commit interface`.

## Constraints

- Judge the slices together.
- Hold the OWASP Top 10 floor, in the stack idiom.
- After the user approves the surface, set `Status: approved`, before the test writer runs.
- Give the test writer `interface.md`, not the stubs. A `broken` or "does not reach the surface" test goes back to it, at most 3 times.
- Outputs give each reader exactly what it reads: see `contracts.json`.

## Done when

- Every slice is `red` before any build starts, and the interface is committed.
