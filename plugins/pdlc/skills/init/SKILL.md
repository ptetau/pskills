---
name: init
description: >
  Prepares a project of any kind, new or existing, for pdlc. Creates the pdlc folder, maps
  the existing code with the recon agent, agrees the default conventions with the user,
  and selects the adapters. Use when
  the user says "/pdlc:init", "set up pdlc", or wants to start to use pdlc in a project.
  With the argument "defaults", the skill accepts each recommended answer and asks no
  questions.
---


# pdlc init

## Goal

The project has `pdlc/` with stub specs, conventions, working checks, and adapters.

## Inputs

- The project, `pdlc:recon` map, `references/`, answers, or `defaults`.

## Outputs

- `pdlc/` gets `references/templates/README.md`, `references/templates/config.md`,
  `templates/`, `ports/`, `adapters/`, `bin/`, `reviews/`, and `references/defaults/` in
  `specs/design/` without `## Question`. Empty `inbox/`, `changes/`, `specs/jobs/`,
  `specs/capabilities/` get `.gitkeep`.
  `python3 <the upgrade skill>/scripts/upgrade.py record` writes `pdlc/version.json`.
- The commit `pdlc.py commit setup` on `main`, no new branch.
- Reply: each decision, "Unsure" item, `/pdlc:ship <what you want>`, `/pdlc:intake`.

## Constraints

- Stop if not a repository, or `pdlc/` exists.
- Offer the dashboard (`pdlc:dashboard`). With `defaults`, ask nothing, keep the map, take
  the more common pattern, name `/pdlc:dashboard`.
- No code: recommend `/decompose`, `/blueprint`, `/pdlc:intake <name>.blueprint.md`.
- Each file or part is in one code map at most. A stub has `Status: stub`, "None written yet."
- `Ask at init: yes` is a question. A changed answer sets `Default: no`.
- The user confirms six Checks items (`{intent}`, `{files}`, `none`). If checks run, prove
  "all" skips a failing `IN-9999` acceptance file. Delete it.
- Use `visual-web` or `visual-terminal`. `.gitignore` gets `pdlc/.tools/` and `pdlc/.logs/`.

## Done when

The commit exists. The tree is clean.
