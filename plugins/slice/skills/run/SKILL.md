---
name: run
description: >
  Runs the slice stages in order, from the state in slice/: spec, plan, domain, interface, build. Continues where it stopped. Use when the user says "/slice:run", or wants a specification built all the way.
---

# slice run

## Goal

A specification becomes committed slices, with the fewest stops. It stops only for a question to the user or a limit.

## Inputs

- The output of `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py status`. Its `next:` line names the stage.
- The specification, for a first run: a file path or the words of the user.

## Outputs

- Each stage runs through its own skill: `/slice:spec`, `/slice:plan`, `/slice:domain`, `/slice:interface`, `/slice:build`.
- The reply: the slices done, and the slice or question that stopped the run.

## Constraints

- Run `status` after each stage, and follow `next:`.
- The user ratifies the spec and approves the interface. Do not skip these two stops.
- `next: ask the user about <Sn>` ends the run. Show what fails, and ask.
- Start no stage twice for the same state.
- Outputs give each reader exactly what it reads: see `contracts.json`.

## Done when

- `status` says `next: all slices done`, or the run stopped with a question.
