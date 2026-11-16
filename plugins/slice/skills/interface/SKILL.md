---
name: interface
description: >
  Designs the one test surface that all the slices need, for example HTTP endpoints or the public functions of a module. Creates it as stubs, and has the test-writer agent write red acceptance tests against it. Use when the user says "/slice:interface", or when the domain is mapped.
---

# slice interface

## Goal

One interface serves all the slices, is the smallest they need, and is good practice for the stack. Each slice has tests that fail only on missing behaviour.

## Inputs

- `spec.md`, `slices.md`, and `domain.md` in `slice/NNN-<name>/`, and `slice/config.md`.

## Outputs

- `slice/NNN-<name>/interface.md` from the template. Read by the test writer, implementer, and reviewer. It gives import lines, signatures, shapes, errors, and domain concepts.
- Stubs in the source folders, raising the not-implemented error (`raise NotImplementedError("not implemented")`). Read by the implementer.
- Tests in the tests folder, from `slice:test-writer`. Read by `slice.py`.
- Each slice `red` (`slice.py set <Sn> red`, after `slice.py test <Sn> --red` exits 0). Then `slice.py commit interface`.

## Constraints

- Judge the slices together: one naming style, one error form.
- Hold the OWASP Top 10 floor, in the idiom of the stack.
- The user approves the surface first.
- Give the test writer `interface.md`, not the stubs. A `broken` or "does not reach the surface" test goes back to it, at most 3 times.
- Outputs give each reader exactly what it reads: see `contracts.json`.

## Done when

- Each slice is `red`, and the interface is committed.
