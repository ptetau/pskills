---
name: init
description: >
  Sets pdlc up in a project, new or existing. Creates the pdlc folder, runs recon on
  existing code, confirms default conventions with the user, and picks adapters. Use when
  the user says "/pdlc:init", "set up pdlc", or wants to start using pdlc in a project.
---

# pdlc init

> Skeleton. Not built yet. See `pdlc/OUTLINE.md` sections 3, 10 and 11.

## What it does

Gets a project ready for pdlc. After init, all work can enter through the inbox.

## Reads

- The project's code, docs and git history (existing projects only, through the `recon` agent).

## Writes

- `pdlc/` with `config.md`, `ports/`, `adapters/`, `inbox/`, `specs/` and `changes/`.
- Stub job and capability specs from recon.
- Design specs for the defaults the user confirmed.

## Steps

1. If `pdlc/` already exists, stop and say so.
2. Create the folders and copy in the templates, port contracts and default adapters.
3. If there is existing code, send the `recon` agent for a thin map. Show the user the
   capabilities and jobs it found. Let them merge, split or rename.
4. Quiz the user on each default, one card at a time. The default is marked recommended,
   so `skip` accepts it. Write each answer as a design spec.
5. Ask which adapter to use for each port. Write the choices to `config.md`.
6. Tell the user how to add their first intent.

## Stop and ask when

- Recon finds two patterns for the same thing. Ask which one is the convention.
