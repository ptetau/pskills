---
name: plan
description: >
  Breaks a ratified slice/spec.md into vertical slices: user stories that each cut through
  every layer of the app, in build order. Use when the user says "/slice:plan", or when the
  spec is ratified.
---

# slice plan

## Goal

`slice/slices.md` holds the vertical slices of the spec, in the order to build them. Each
slice works alone, end to end, and the user can see its result.

## Inputs

- `slice/spec.md`, which must say `Status: ratified`. If it does not, stop and name `/slice:spec`.

## Outputs

- `slice/slices.md` from `${CLAUDE_PLUGIN_ROOT}/templates/slices.md`: for each slice (`S1` for the first, `S2` for the second), the story, the acceptance lines, the layers, and `Status: planned`.
- The reply lists the slices, and names `/slice:interface`.

## Constraints

- A slice cuts through each layer that its story needs (for example UI, API, store).
- The first slice is the thinnest path that works. Each later slice adds one story on top of the earlier ones.
- An acceptance line is a concrete check: given, when, then, with exact values.
- Each acceptance line comes from the spec. If the spec lacks one, ask the user, and do not guess.
- Put the title in the heading as `## S1: <title>`. The commit subject uses it.

## Done when

- Each behaviour of the spec is in exactly one slice.
- Each slice has a story, acceptance lines, and layers.
