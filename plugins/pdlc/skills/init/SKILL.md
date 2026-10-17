---
name: init
description: >
  Prepares a project of any kind, new or existing, for pdlc. Creates the pdlc folder, maps
  the existing code with the recon agent, agrees the default conventions with the user,
  and selects the adapters. Use when the user says "/pdlc:init", "set up pdlc", or wants
  to start to use pdlc in a project. With the argument "defaults", the skill accepts each
  recommended answer and asks no questions.
---

# pdlc init

This skill prepares a project for pdlc, for any type of system. After init, all work
enters through the inbox.

The files to copy are in the `references/` folder next to this file.

## Before you start

- The project must be a git repository. If the project is not a git repository, stop and
  say so.
- If `pdlc/` already exists at the project root, stop. Tell the user that the project
  already has pdlc.
- If the user gave `defaults`, do not ask any questions. Do these steps instead:
  - Accept the map from recon as it is.
  - Where two patterns compete, select the more common pattern.
  - Take the recommended answer to each question.
  - At the end, list each decision that you made, so that the user can change it.

## Steps

### 1. Create the folder

Create `pdlc/` at the project root, with these contents:

- `pdlc/README.md` from `references/templates/README.md`.
- `pdlc/config.md` from `references/templates/config.md`.
- `pdlc/templates/`: each other file in `references/templates/`.
- `pdlc/ports/`: each file in `references/ports/`.
- `pdlc/adapters/`: each file in `references/adapters/`.
- `pdlc/bin/`: each file in `references/bin/`.
- `pdlc/reviews/`: each file in `references/reviews/`.
- The empty folders `pdlc/inbox/`, `pdlc/changes/`, `pdlc/specs/jobs/`,
  `pdlc/specs/capabilities/`, and `pdlc/specs/design/`. Put a `.gitkeep` file in each
  empty folder, so that git keeps the folder.

### 2. Map existing code

If the project has no code yet (a new build), there is nothing to map. In that case, if
`/decompose` is installed, recommend that the user runs `/decompose` first. `/decompose`
decides where the main parts go. Recommend that the user then starts the first intent
with the result of `/decompose`. Do not run `/decompose` yourself, and do not wait for
it. Continue with the next step.

Start the `pdlc:recon` agent, and ask for a **thin map** of the project. Show the user
what recon found, as two short lists: capabilities and jobs. Give the code map of each
item. Ask if the user wants to merge, split, or rename an item. These boundaries are
important, because each change must stay inside one boundary.

Each file belongs to a maximum of one code map. If a file is in two code maps, ask which
spec owns the file. If a file mixes job code and capability code, give the file to the
job. Then write a note that a later change can split the capability out.

For each job and capability that the user keeps, create a spec from the job template or
the capability template. In each new spec, do these steps:

1. Set `Status: stub`.
2. Write the summary and the code map.
3. In the requirements section, write only the line "None written yet."

If recon found two patterns for the same thing, ask the user which pattern is the
convention. Write the answer as a design spec from the design template.

### 3. Agree the defaults

For each file in `references/defaults/`, do these steps:

1. If the file says `Ask at init: yes`, ask the question of the file. Ask one question at
   a time. Show the options, and mark the recommended option. The user can reply `skip`
   to take the recommendation.
2. If the user selects a different option, write the rule again to agree with the
   answer. Then set `Default: no`.
3. Copy the result to `pdlc/specs/design/`.

### 4. Configure the checks and the visual review

Complete the "Checks" section of `pdlc/config.md` with the answer from recon. Write these
three items:

- The command that runs all checks.
- The command that runs only the checks of one requirement.
- The check folders.

Ask the user to make sure that the three items are correct.

Set the visual adapter:

- If the project serves pages, set `visual-web`. In the "Visual" section, write the
  `start` and `url` values from recon.
- If the project does not serve pages, set `visual-terminal`.

Add `pdlc/.tools/` to the `.gitignore` file of the project.

If the project has no way to run checks yet, tell the user. Recommend that the first
intent adds a way to run checks.

### 5. Pick adapters

Show the adapters in `pdlc/config.md`. Ask if the defaults are correct. pdlc ships these
defaults:

- `inbox-files`, `checks-command`, `review-agent`, and `delivery-github`.
- `visual-web` or `visual-terminal`.
- No tracker. The `tracker-github-projects` and `tracker-linear` adapters are available.

If the user wants a tracker, say that the tracker needs a tracker adapter first. An
intent can add the tracker adapter.

### 6. Offer the live dashboard

Ask if the user wants the optional live dashboard of pdlc. The dashboard is one page. The
page shows tasks, the questions that wait for the user, deliverables, and each stuck item.

- If the user says yes, follow the `pdlc:dashboard` skill.
- With `defaults`, do not install the dashboard. Instead, at the end, tell the user that
  `/pdlc:dashboard` adds the dashboard.

### 7. Finish

1. Commit the new `pdlc/` folder and no other changes. Use the message "Set up pdlc".
2. Tell the user how to start. `/pdlc:ship <what you want>` runs all the stages. The user
   can also run one stage at a time, and start with `/pdlc:intake`.
