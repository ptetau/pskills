---
name: plan
description: >
  Breaks a ratified spec into vertical slices: user stories that each cut through every layer of the app, in build order. Use when the user says "/slice:plan", or when the spec is ratified.
model: claude-opus-5-5
effort: medium
---

# slice plan

## Goal

`slices.md` holds the vertical slices of the spec, in build order. Each slice works alone, end to end, and the user can see its result. Each requirement is in a slice.

## Inputs

- `slice/NNN-<name>/spec.md` (the highest NNN), which must say `Status: ratified`. If it does not, stop and name `/slice:spec`.

## Outputs

- `slice/NNN-<name>/slices.md` from `${CLAUDE_PLUGIN_ROOT}/templates/slices.md`. Read by `domain`, `build`, agents, and `slice.py`. Each slice (`S1`, `S2`) has a story, `Requirements:`, acceptance lines, layers, and `Status: planned`.
- The reply lists the slices, and names `/slice:domain`.

## Constraints

- Each slice is one logical story that cuts through its layers (UI, API, store).
- First slice: thinnest working path. Each later slice adds one logical story.
- Acceptance lines are concrete checks with exact values, citing their requirement.
- Each acceptance line comes from the spec. Ask the user if missing.
- Give each slice `- Tier: hard` when it creates the structure that later slices extend, or holds inference or proofs. Else `- Tier: standard`.
- Put a clear, specific title in `## S1: <title>` (the commit subject uses it).
- Outputs give each reader exactly what it reads: see `contracts.json`.

## Done when

- `slice.py status` lists no requirement as uncovered by a slice.
