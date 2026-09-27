---
name: change
description: >
  Turns a ready intent into one or more change specs. Each change covers exactly one job,
  one capability, or one design spec. Capability milestones come before the jobs that need
  them. Use when the user says "/pdlc:change" or wants to plan the work for a ready intent.
---

# pdlc change

> Skeleton. Not built yet. See the plugin's `OUTLINE.md`, sections 2 and 5.

## What it does

Splits a ready intent into milestones and writes a change spec for each one.

## Reads

- The ready intent and its requirements.
- The specs those requirements rely on, and their code maps.

## Writes

- One change spec per milestone in `pdlc/changes/`.
- The intent file: its changes, in order.

## Steps

1. Group the intent's requirements by the job, capability or design spec they belong to.
   Each group is one milestone.
2. Order them: design first, then capabilities, then jobs.
3. For each milestone, write a change spec: what it delivers, the requirements with their
   acceptance checks, the specs it relies on, the files it may touch, and small steps.
4. Each step names the requirement it serves and the check that proves it.
5. Tell the tracker port about the new changes.

## Rules

- A job change may use capabilities. It never edits them.
- List only the files the change needs. Take them from the code map.
