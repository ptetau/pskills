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

The project has `pdlc/` with stub specs, conventions, working checks, and adapters. The README binds.

## Inputs

- The project, the map of `pdlc:recon`, `references/`, and the answers, or `defaults`.

## Outputs

- `pdlc/`: `README.md` and `config.md` from `references/templates/`; `templates/`, `ports/`,
  `adapters/`, `bin/`, `reviews/` from `references/`; `references/defaults/` into
  `specs/design/` without `## Question`; empty `inbox/`, `changes/`, `specs/jobs/`,
  `specs/capabilities/` with `.gitkeep`. Then
  `python3 <the upgrade skill>/scripts/upgrade.py record` writes `pdlc/version.json`.
- The commit "Set up pdlc" on `main`, no new branch.
- Reply: each decision, "Unsure" item, `/pdlc:ship <what you want>`, `/pdlc:intake`.

## Constraints

- Stop if not a repository, or `pdlc/` exists.
- `defaults`: no question; keep the map; take the more common pattern; no dashboard
  (`/pdlc:dashboard`).
- No code: recommend `/decompose`, `/blueprint`, `/pdlc:intake <name>.blueprint.md`.
- Each file or part is in one code map at most. A stub has `Status: stub`, "None written yet."
- `Ask at init: yes` is a question. A changed answer sets `Default: no`.
- Checks: user confirms six items; `{intent}`, `{files}`, `none`. Prove with a failing
  `IN-9999` acceptance file, then delete it.
- `visual-web` or `visual-terminal`; `.gitignore` gets `pdlc/.tools/`, `pdlc/.logs/`.

## Done when

The commit exists; the tree is clean.
