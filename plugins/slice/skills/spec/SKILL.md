---
name: spec
description: >
  Turns a specification, for one change or a full app, into a ratified, numbered spec folder. Finds each ambiguity that changes what gets built, and asks the user about it, one question at a time, with a recommended answer. Use when the user says "/slice:spec", or gives a specification to build.
model: claude-opus-5-5
effort: medium
---

# slice spec

## Goal

`slice/NNN-<name>/spec.md` holds the requirements (R1) and decisions (D1) of the user, with no open ambiguity that changes what gets built, and the user ratified it.

## Inputs

- A file path, or the words of the user. Else the highest draft.

## Outputs

- `slice/config.md` from `${CLAUDE_PLUGIN_ROOT}/templates/config.md`, with the ratified stack and a `security scan` command that fits it (`none` if none fits). Read by `slice.py` and the guard.
- `slice/NNN-<name>/spec.md` from the spec template, with the next NNN. Read by `plan`, `domain`, and agents. `Status: draft`, then `ratified`.
- The reply names `/slice:plan`.

## Constraints

- Ask with `AskUserQuestion`: one question at a time, or up to 4 independent ones. Give 2 to 4 answers. Put the recommended one first, marked "(Recommended)", with a reason from the words of the user. With no evidence, recommend none.
- Ask only about an ambiguity that changes the build.
- If no stack is fixed, recommend a modern, well regarded, minimal, fast, common one, with a reason.
- Number each requirement and decision.
- Set `Status: ratified` only after the user confirms the summary.
- Outputs give each reader exactly what it reads: see `contracts.json`.

## Done when

- `spec.md` says `Status: ratified`, and the user confirmed the summary.
