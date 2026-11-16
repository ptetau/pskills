---
name: spec
description: >
  Turns a specification, for one change or a full app, into a ratified slice/spec.md. Finds
  each ambiguity that changes what gets built, and asks the user about it, one question at
  a time, with a recommended answer. Use when the user says "/slice:spec", or gives a
  specification to build.
---

# slice spec

## Goal

`slice/spec.md` holds the specification and the decisions of the user, with no open
ambiguity that changes what gets built. The user ratified it.

## Inputs

- A file path, or the words of the user. Else the draft in `slice/spec.md`.

## Outputs

- `slice/config.md` from `${CLAUDE_PLUGIN_ROOT}/templates/config.md`, filled from the project files. Ask only for a value that the files lack.
- `slice/spec.md` from `${CLAUDE_PLUGIN_ROOT}/templates/spec.md`, with `Status: draft`, then `Status: ratified`.
- The reply names `/slice:plan`.

## Constraints

- Ask with `AskUserQuestion`: one question at a time, or up to 4 questions that do not depend on each other. Give 2 to 4 answers. Put the recommended one first, marked "(Recommended)", with a reason from the words of the user. With no evidence, recommend none. Follow `/quiz` "Step 2".
- Ask only about an ambiguity that changes what gets built: scope, behaviour, errors, limits, stack.
- Write each decision in the words of the user, with an ID and a short description.
- Show a summary of all decisions. Set `Status: ratified` only after the user confirms the summary.

## Done when

- `slice/spec.md` says `Status: ratified`, and the user confirmed the summary.
