---
name: ready
description: >
  Checks that an intent's spec patches are clear enough to build. Asks the user about
  anything unclear, one question at a time, and checks the specs for contradictions. Marks
  requirements ready when they pass. Use when the user says "/pdlc:ready" or wants to know
  if an intent is ready to build.
---

# pdlc ready

> Skeleton. Not built yet. See the plugin's `OUTLINE.md`, sections 4 and 7.

## What it does

Makes sure every `proposed` requirement for one intent is clear, testable and consistent.

## Reads

- The intent and every requirement it touched.
- The specs those requirements sit next to or rely on.

## Writes

- Clarified requirements, marked `ready`.
- The intent's status: `ready` once every requirement is ready.

## Steps

1. For each proposed requirement, check it has acceptance checks that a check could prove.
2. Ask the user about anything unclear, one short question at a time, with a recommended
   answer (a simplified `/quiz`).
3. Check the new requirements against the specs around them for contradictions
   (a simplified `/argue`).
4. Check every capability and convention the requirements need exists. If a convention is
   missing, hand off to the `conventions` skill.
5. Mark each passing requirement `ready`. Update the intent and tell the tracker port.

## Stop and ask when

- Two requirements contradict each other.
