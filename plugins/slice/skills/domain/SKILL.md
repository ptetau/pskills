---
name: domain
description: >
  Models the domain and the boundary of the system before any interface exists, and shows that each numbered requirement is met by the model. Writes a design document only. Use when the user says "/slice:domain", or when the slices are planned.
---

# slice domain

## Goal

`domain.md` holds a model and a boundary that are sufficient for the spec. Each requirement maps to the parts that meet it. A requirement with no mapping is a gap, and the stage stops.

## Inputs

- `slice/NNN-<name>/spec.md` and `slice/NNN-<name>/slices.md`.

## Outputs

- `slice/NNN-<name>/domain.md` from `${CLAUDE_PLUGIN_ROOT}/templates/domain.md`. Read by `interface`, the agents, and `slice.py status`, which reads each `- Rn:` line of the requirement map.
- The reply names `/slice:interface`.

## Constraints

- Write no code. This is a design document.
- Give each object with a lifecycle a state machine: states, start, end, and transitions (trigger, guard, effect). Name each refused transition and its error. A requirement that changes state maps to its transitions.
- Name the boundary: what is inside, what is outside, and each external actor.
- On a gap, ask the user with `AskUserQuestion`, or fix the spec with the user.
- Outputs give each reader exactly what it reads: see `contracts.json`.

## Done when

- `slice.py status` says `domain: mapped`.
