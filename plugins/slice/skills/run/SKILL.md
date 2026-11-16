---
name: run
description: >
  Runs the slice stages from the state in slice/, in the order that `slice.py next` gives: spec, plan, domain, interface, build. Continues where it stopped. Use when the user says "/slice:run", or wants a specification built all the way.
model: claude-opus-5-5
effort: medium
---

# slice run

## Goal

A specification becomes committed slices, with the fewest stops. It stops only for a question to the user or a limit.

## Inputs

- The output of `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py next`: a stage (`spec`, `plan`, `domain`, `interface`), `build <Sn>`, `stop <Sn>: <reason>`, or `done`.
- The specification, for a first run: a file path or the words of the user.

## Outputs

- Each stage runs through its own skill: `/slice:spec`, `/slice:plan`, `/slice:domain`, `/slice:interface`, `/slice:build`.
- Before each stage, one line that names the stage and why it starts. At the end, a short recap: the slices done, the commits, and the slice or question that stopped the run.

## Constraints

- Loop on `slice.py next`. Run what it prints, then run it again. Never choose or reorder the stages yourself.
- The user ratifies the spec and approves the interface. Do not skip these two stops.
- `stop <Sn>: <reason>` ends the run. Show what fails, and ask.
- Start no stage twice for the same state.
- Outputs give each reader exactly what it reads: see `contracts.json`.

## Done when

- `slice.py next` prints `done`, or the run stopped with a question.
