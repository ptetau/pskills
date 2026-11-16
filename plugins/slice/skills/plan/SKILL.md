---
name: plan
description: >
  Breaks a ratified spec into vertical slices: user stories that each cut through every layer of the app, in build order. Use when the user says "/slice:plan", or when the spec is ratified.
---

# slice plan

## Goal

`slices.md` holds the vertical slices of the spec, in build order. Each slice works alone, end to end, and the user can see its result. Each requirement is in a slice.

## Inputs

- `slice/NNN-<name>/spec.md` (the highest NNN), which must say `Status: ratified`. If it does not, stop and name `/slice:spec`.

## Outputs

- `slice/NNN-<name>/slices.md` from `${CLAUDE_PLUGIN_ROOT}/templates/slices.md`. Read by `domain`, `interface`, `build`, the agents, and `slice.py`. Each slice (`S1`, `S2`) has a story, `Requirements:`, acceptance lines, layers, and `Status: planned`.
- The reply lists the slices, and names `/slice:domain`.

## Constraints

- A slice cuts through each layer that its story needs (for example UI, API, store).
- The first slice is the thinnest path that works. Each later slice adds one story.
- An acceptance line is a concrete check, with exact values, and cites its requirement.
- Each acceptance line comes from the spec. If the spec lacks one, ask the user.
- Put the title in the heading as `## S1: <title>`. The commit subject uses it.
- Outputs give each reader exactly what it reads: see `contracts.json`.

## Done when

- `slice.py status` lists no requirement as uncovered by a slice.
