---
name: build
description: >
  Builds one pdlc change spec, test first. Writes a failing test for each step, makes it
  pass, tidies up, and commits with trace trailers. Marks requirements built. Use when the
  user says "/pdlc:build" or wants a change spec built.
---

# pdlc build

> Skeleton. Not built yet. See `pdlc/OUTLINE.md` sections 5 and 6.
> A simplified `/quiz-plan-execute`.

## What it does

Turns one change spec into code on its own branch.

## Reads

- The change spec. It should be all the builder needs.
- The design specs it lists.

## Writes

- Code and tests, only in the files the change spec lists.
- One commit per step, with `Intent`, `Change`, `Req` and `Ticket` trailers.
- Requirement status `built`. The change spec's progress log.

## Steps

1. Open a branch through the delivery port.
2. For each step:
   1. Write a test named with the requirement ID. Run it. It must fail.
   2. Write the least code that makes it pass.
   3. Tidy up. Follow the design specs.
   4. Commit with the trace trailers. Log the step.
3. Mark the change's requirements `built`. Tell the tracker port.
4. Hand off to `verify`.

## Stop and ask when

- The work needs a file the change spec doesn't list.
- The same fix has failed twice.
