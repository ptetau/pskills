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

- The project must be a git repository. If it isn't, stop and say so.
- If `pdlc/` already exists at the project root, stop. Say pdlc is already set up.
- If the user passed `defaults`, don't ask anything. Accept recon's map as it is, pick the
  more common pattern wherever two compete, and take the recommended answer to every
  question. List everything you decided at the end, so the user can change it.

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
  and `pdlc/specs/design/`. Put a `.gitkeep` in each so git keeps it.

### 2. Map existing code

If the project has no code yet (a new build), there is nothing to map. Instead, recommend
that the user runs `/decompose` first, if it is installed, to decide where the main parts
go, then starts their first intent with its result. Don't run it yourself, and don't wait
for it: carry on with the next step.

Start the `pdlc:recon` agent and ask for a **thin map** of the project. Then show the user
what it found, as two short lists: capabilities and jobs, each with its code map. Ask if
anything should be merged, split or renamed. These boundaries matter, because every change
must stay inside one.

Each file belongs to at most one code map. If a file is in two, ask which spec owns it. If
a file mixes job and capability code, give it to the job and note that the capability
could be split out later.

For each job and capability the user keeps, create a spec from the job or capability
template. Set `Status: stub`, fill in the summary and code map, and leave the requirements
section with the line "None written yet."

If recon found two patterns for the same thing, ask the user which one is the convention.
Write the answer as a design spec from the design template.

### 3. Agree the defaults

For each file in `references/defaults/`:

- If it says `Ask at init: yes`, ask its question. Show the options, one question at a
  time, with the recommended one marked. The user can reply `skip` to take the
  recommendation.
- If the user picks something else, rewrite the rule to match and set `Default: no`.
- Copy the result to `pdlc/specs/design/`.

### 4. Set up checks and the visual review

Fill in the "Checks" section of `pdlc/config.md` with recon's answer: the command that
runs all checks, the command that runs only one requirement's checks, and the check
folders. Confirm them with the user.

Set the visual adapter: `visual-web` if the project serves pages, with "Visual" `start`
and `url` filled in from recon; otherwise `visual-terminal`. Add `pdlc/.tools/` to the
project's `.gitignore`.

If the project has no way to run checks yet, say so. Suggest that the first intent adds
one.

### 5. Pick adapters

Show the adapters in `pdlc/config.md` and ask if the defaults are right. pdlc ships:
`inbox-files`, `checks-command`, `review-agent`, `delivery-github`, `visual-web` or
`visual-terminal`, and no tracker (`tracker-github-projects` and `tracker-linear` are
available). If the
user wants a tracker, say it needs a tracker adapter first, which can be added as an
intent.

### 6. Offer the live dashboard

Ask if they'd like pdlc's optional live dashboard: one page showing tasks, questions
waiting for them, deliverables and anything stuck. If yes, follow the `pdlc:dashboard`
skill. With `defaults`, don't install it; just mention at the end that `/pdlc:dashboard`
adds it.

### 7. Finish

- Commit the new `pdlc/` folder on its own, with the message "Set up pdlc".
- Tell the user how to start: `/pdlc:ship <what you want>` runs everything, or they can go
  a stage at a time, starting with `/pdlc:intake`.
