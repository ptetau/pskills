---
name: conventions
description: >
  Establishes or changes a pdlc convention with the user. Writes the agreed convention as a
  design spec, then files one migration intent per affected job or capability. Use when the
  user says "/pdlc:conventions", wants to set or change how something is done, or another
  pdlc skill finds a missing convention.
---

# pdlc conventions

> Skeleton. Not built yet. See the plugin's `OUTLINE.md`, section 10.

## What it does

Keeps the software consistent by writing conventions down and agreeing them with the user.

## Reads

- The design specs.
- Examples from the code, when choosing between existing patterns.

## Writes

- A new or changed design spec.
- Migration intents in the inbox, one per affected job or capability.

## Steps

1. Say what needs deciding and why, in one or two sentences.
2. Offer two or three options, each with a real example from this codebase. Mark one
   recommended.
3. Write the choice as a design spec.
4. If it changes an existing convention, find the jobs and capabilities that follow the old
   one. File one migration intent for each. Don't start them. The user chooses when.

## Rules

- Never change a convention without asking the user.
