---
name: interface
description: >
  Designs the one test surface that all the slices need, for example HTTP endpoints or the public functions of a module. Creates it as stubs that compile, and has the test-writer agent write red acceptance tests against it. Use when the user says "/slice:interface", or when
  the slices are planned.
---

# slice interface

## Goal

One interface serves all the slices, is the smallest that they need, and is good practice
for the stack. It exists as stubs. Each slice has acceptance tests that fail because the
behaviour is missing.

## Inputs

- `slice/spec.md`, `slice/slices.md`, and `slice/config.md`.

## Outputs

- `slice/interface.md` from the template: the surface, and for each slice the parts that it uses.
- Stubs in the source folders that compile and do nothing.
- Tests in the tests folder, written by `slice:test-writer`, one slice at a time.
- Each slice is `red`: `slice.py set <Sn> red`, after `slice.py test <Sn> --red` exits 0.
- The reply names `/slice:build`.

## Constraints

- Judge all the slices together: one naming style, one error form, one shape for the same data.
- The user approves the surface before the stubs. Use `AskUserQuestion` for a real choice.
- A `broken` test goes back to the test-writer, at most 3 times. Then stop and show it to the user.
- `slice.py` means `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py`.

## Done when

- Each slice is `red`, and no test is `broken`.
