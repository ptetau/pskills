---
name: init
description: >
  Sets pdlc up in a project of any kind, new or existing. Creates the pdlc folder, maps
  existing code with the recon agent, confirms default conventions with the user, and
  picks adapters. Use when the user says "/pdlc:init", "set up pdlc", or wants to start
  using pdlc in a project. Pass "defaults" to accept every recommended answer without
  asking.
---

# pdlc init

Gets a project ready for pdlc, whatever kind of system it is. After init, all work enters
through the inbox.

The files to copy are in the `references/` folder next to this file.

## Before you start

- If the project isn't a git repository, stop and say so.
- If `pdlc/` already exists at the project root, stop. Say pdlc is already set up.
- If the user passed `defaults`, don't ask anything. Instead:
  - accept recon's map as it is;
  - wherever two patterns compete, pick the more common one;
  - take the recommended answer to every question;
  - at the end, list everything you decided, so the user can change it.

## Steps

### 1. Create the folder

Create `pdlc/` at the project root with:

- `pdlc/README.md` from `references/templates/README.md`.
- `pdlc/config.md` from `references/templates/config.md`.
- `pdlc/templates/`: every other file in `references/templates/`.
- `pdlc/ports/`: every file in `references/ports/`.
- `pdlc/adapters/`: every file in `references/adapters/`.
- `pdlc/bin/`: every file in `references/bin/`.
- `pdlc/reviews/`: every file in `references/reviews/`.
- Empty `pdlc/inbox/`, `pdlc/changes/`, `pdlc/specs/jobs/`, `pdlc/specs/capabilities/`
  and `pdlc/specs/design/`. Put a `.gitkeep` in each empty folder so git keeps the folder.

### 2. Map existing code

If the project has no code yet (a new build), there is nothing to map. If `/decompose` is
installed, recommend that the user runs it first, to decide where the main parts go. The
user then starts their first intent with the result of `/decompose`. Don't run
`/decompose` yourself, and don't wait for it. Carry on with the next step.

Start the `pdlc:recon` agent. Ask recon for a **thin map** of the project. Show the user
what recon found, as two short lists: capabilities and jobs, each with its code map. Ask
if the user wants to merge, split or rename any of them. These boundaries matter. Every
change must stay inside one of them.

Map the code as "Code maps" in `pdlc/README.md` says. Each entry point (a route or request
handler, a command, a page script or event handler) belongs to the job it serves.
Capabilities hold only the shared logic under them: storage, outside services, and the
plumbing every job uses.

Map a file that holds parts of several specs by parts. Each job names its own parts, and
the capability lists the file with `: the rest`. Each file, or part, is in one code map
only. Leave the README out of every map.

For each job and capability the user keeps, create a spec from the job or capability
template. Set `Status: stub`. Fill in the summary and code map. Leave the requirements
section with the line "None written yet." Put recon's "Unsure" items in your summary at
the end, never into a spec.

If recon found two patterns for the same thing, ask the user which one is the convention.
Write the answer as a design spec from the design template.

### 3. Agree the defaults

For each file in `references/defaults/`:

- If the file says `Ask at init: yes`, ask its question. Ask one question at a time.
  Show the options, with the recommended one marked. The user can reply `skip` to take
  the recommendation.
- If the user picks something else, rewrite the rule to match. Then set `Default: no`.
- Copy the result to `pdlc/specs/design/`, without its `## Question` section.

### 4. Set up checks and the visual review

Fill in the "Checks" section of `pdlc/config.md` with recon's answer:

- the command that runs all checks;
- the command that runs only one requirement's checks;
- the check folders (`tests/` if there are none yet);
- the one ID form.

Confirm these values with the user. In `config.md`, replace every placeholder, example and
"(or …)" hint with the value chosen, or `none`.

Set the visual adapter. If the project serves pages, use `visual-web`, and fill in
"Visual" `start` and `url` from recon. Otherwise, use `visual-terminal`.

Add `pdlc/.tools/` to the project's `.gitignore`. Also add the folders that the project's
language and tools write when checks run. Examples: `__pycache__/` for Python,
`node_modules/` for Node. If the project has no code yet, its first change adds those
folders instead.

If the project has no way to run checks yet, say so. Suggest that the first intent adds
one.

### 5. Pick adapters

Show the adapters in `pdlc/config.md`. Ask if the defaults are right. By default, pdlc
uses `inbox-files`, `checks-command`, `review-agent`, `delivery-github`, `visual-web` or
`visual-terminal`, and no tracker. pdlc also ships `tracker-github-projects` and
`tracker-linear`. If the user wants a tracker, say that a tracker needs a tracker adapter
first. The user can add that adapter as an intent.

### 6. Offer the live dashboard

pdlc has an optional live dashboard: one page showing tasks, questions waiting for the
user, deliverables and anything stuck. Ask if the user wants it. If the user says yes, follow the
`pdlc:dashboard` skill. With `defaults`, don't install the dashboard. At the end, mention
that `/pdlc:dashboard` adds it.

### 7. Finish

- Commit the new `pdlc/` folder on its own, with the message "Set up pdlc", on main
  (the project's default branch). Don't start a branch for this commit. pdlc's records
  live on main, and every later stage looks for them there.
- Tell the user how to start. `/pdlc:ship <what you want>` runs everything. Or the user
  can go a stage at a time, starting with `/pdlc:intake`.
