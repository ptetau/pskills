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
`/decompose` is installed, recommend that the user runs `/decompose` first, and then
`/blueprint`. `/decompose` decides where the main parts go. `/blueprint` turns that design
into types, error codes, and signatures. Recommend that the user then starts the first
intent with `/pdlc:intake <name>.blueprint.md`. Do not run `/decompose` or `/blueprint`
yourself, and do not wait for them. Continue with the next step.

Start the `pdlc:recon` agent, and ask for a **thin map** of the project. Show the user
what recon found, as two short lists: capabilities and jobs. Give the code map of each
item. Ask if the user wants to merge, split, or rename an item. These boundaries are
important, because each change must stay inside one boundary.

Map the code as "Code maps" in `pdlc/README.md` says. Each entry point belongs to the
job that it serves. An entry point is a route, a request handler, a command, a page
script, or an event handler. Capabilities hold only the shared logic under the jobs:
storage, outside services, and the plumbing that every job uses.

Map a file that holds parts of several specs by parts. Each job names its own parts. The
capability lists the file with `: the rest`. Each file, or part, belongs to a maximum of
one code map. Leave the README out of every map.

Recon can list "Unsure" items. Do not put an "Unsure" item into a spec. Put each one in
your summary at the end.

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
3. Copy the result to `pdlc/specs/design/`. Do not copy its `## Question` section.

### 4. Set up checks and the visual review

Complete the "Checks" section of `pdlc/config.md` with the answer from recon. Write these
six items:

- The command that runs all checks.
- The command that runs only the checks of one requirement.
- The check folders. If the project has no check folders yet, write `tests/`.
- The acceptance file: the path of the acceptance checks of one intent, with `{intent}`
  where the ID goes. The "all" command must not run this file.
- The acceptance command: the command that runs acceptance files, with `{files}` where the
  paths go.
- The one ID form.

For example, Python `unittest` skips `tests/acceptance_{intent}.py`, and
`python3 -m unittest {files}` runs it. `node --test` skips
`acceptance/{intent}.acceptance.js`, and `node --test {files}` runs it. If the acceptance
file is outside the check folders, add its folder to the check folders.

Ask the user to make sure that the six items are correct. In `config.md`, replace each
placeholder, each example, and each "(or …)" hint with the value that you chose, or with
`none`.

If the project can run checks, make sure that the "all" command skips acceptance files:

1. Write an acceptance file for the made-up intent `IN-9999`, with one check that always
   fails.
2. Run the "all" command. The output must not show that check.
3. Run the acceptance command on the file. The check must fail.
4. Delete the file. If step 2 or 3 went wrong, select a different path, and try again.

Set the visual adapter:

- If the project serves pages, set `visual-web`. In the "Visual" section, write the
  `start` and `url` values from recon.
- If the project does not serve pages, set `visual-terminal`.

Add `pdlc/.tools/` to the `.gitignore` file of the project. Also add the folders that the
language and the tools of the project write when checks run. Examples are `__pycache__/`
for Python and `node_modules/` for Node. If the project has no code yet, its first change
adds those folders.

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
   Commit on `main` (the default branch of the project). Do not start a branch for this
   commit. The records of pdlc live on `main`, and each later stage looks for them there.
2. Tell the user how to start. `/pdlc:ship <what you want>` runs all the stages. The user
   can also run one stage at a time, and start with `/pdlc:intake`.
