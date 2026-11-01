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

Init prepares a project of any type for pdlc. After init, the project has a `pdlc/`
folder, stub specs for its existing code, agreed conventions, check commands that work,
and adapters. All work then enters through the inbox.

## Constraints

- The session model is a Sonnet 5.5 class model or above ("Core rules" in the README
  template). On a lower model, init does no work. Init tells the user that pdlc needs a
  Sonnet 5.5 class model or above.
- The project is a git repository. If not, init stops and says so.
- A project that has `pdlc/` at its root already stops init, and the user hears that the
  project already has pdlc.
- With `defaults`, init asks no question. It accepts the map of recon as it is, takes the
  more common of two patterns, and takes each recommended answer. At the end, it lists
  each decision, so that the user can change it.
- The files to copy are in the `references/` folder next to this file. `pdlc/` holds:
  - `README.md` from `references/templates/README.md`, and `config.md` from
    `references/templates/config.md`.
  - `templates/` with each other file of `references/templates/`.
  - `ports/`, `adapters/`, `bin/`, and `reviews/`, each with the files of the same folder
    in `references/`.
  - The empty folders `inbox/`, `changes/`, `specs/jobs/`, `specs/capabilities/`, and
    `specs/design/`, each with a `.gitkeep` file, so that git keeps the folder.
- After the copy, init runs `python3 <the upgrade skill>/scripts/upgrade.py record`. The
  script writes `pdlc/version.json`, which the commit "Set up pdlc" holds.
- A project with no code yet has nothing to map. If `/decompose` is installed, init
  recommends `/decompose`, then `/blueprint`, then `/pdlc:intake <name>.blueprint.md`.
  `/decompose` decides where the main parts go, and `/blueprint` gives types, error codes,
  and signatures.
- Init does not run `/decompose` or `/blueprint`, and does not wait for them.
- For existing code, `pdlc:recon` makes a thin map. The user sees two short lists,
  capabilities and jobs, each item with its code map. The user can merge, split, or rename
  an item, because each change must stay inside one boundary.
- The map obeys "Code maps" in `pdlc/README.md`. Each entry point (a route, a request
  handler, a command, a page script, an event handler) belongs to the job that it serves.
  Capabilities hold only the shared logic: storage, outside services, and shared plumbing.
- The map gives a file with parts of several specs by its parts. Each job names its
  parts, and the capability lists the file with `: the rest`. Each file or part is in one
  code map at most. The README is in no map.
- An "Unsure" item of recon goes into the final summary, not into a spec.
- Each job and capability that the user keeps gets a spec from its template. The spec has
  `Status: stub`, the summary, the code map, and only "None written yet." under the
  "Interface" and under the requirements.
- Two patterns for the same thing are a question: which one is the convention? The answer
  becomes a design spec from the design template.
- Each file in `references/defaults/` with `Ask at init: yes` is a question, one at a time,
  with its options and its recommended option. The reply `skip` takes the recommendation.
- A different answer rewrites the rule to agree, with `Default: no`. Each default goes to
  `pdlc/specs/design/` without its `## Question` section.
- The "Checks" section of `pdlc/config.md` holds six items from recon, each confirmed by
  the user:
  - The command that runs all checks.
  - The command that runs the checks of one requirement.
  - The check folders, or `tests/` if there are none yet.
  - The acceptance file: the path of the acceptance checks of one intent, with `{intent}`
    where the ID goes. The "all" command does not run this file.
  - The acceptance command, with `{files}` where the paths go.
  - The one ID form.
- For example, Python `unittest` skips `tests/acceptance_{intent}.py`, and
  `python3 -m unittest {files}` runs it. `node --test` skips
  `acceptance/{intent}.acceptance.js`, and `node --test {files}` runs it.
- An acceptance file outside the check folders adds its folder to the check folders. No
  placeholder, example, or "(or …)" hint stays in `config.md`. Each one holds the chosen
  value, or `none`.
- When the project can run checks, a test proves that the "all" command skips acceptance
  files. An acceptance file for the made-up intent `IN-9999` has one check that always
  fails. The "all" command does not show the check, and the acceptance command fails it.
- That test file goes afterwards. If the test goes wrong, init takes a different path and
  tests again.
- The visual adapter is `visual-web` for a project that serves pages, with `start` and
  `url` from recon in "Visual". Else it is `visual-terminal`.
- `.gitignore` lists `pdlc/.tools/` and `pdlc/.logs/`, and the folders that the language
  and the tools write when checks run, for example `__pycache__/` and `node_modules/`.
  With no code yet, the first change adds those folders.
- A project with no way to run checks gets a recommendation: the first intent adds one.
- The user confirms the adapters in `pdlc/config.md`. The defaults are `inbox-files`,
  `checks-command`, `review-agent`, `delivery-github`, `visual-web` or `visual-terminal`,
  and no tracker.
- `tracker-github-projects` and `tracker-linear` are available. A wanted tracker needs its
  tracker adapter first, and an intent can add it.
- The user gets the offer of the optional live dashboard: one page with tasks, questions,
  deliverables, and stuck items. On a yes, the `pdlc:dashboard` skill installs it. With
  `defaults`, init does not install it, and says at the end that `/pdlc:dashboard` adds it.

## Inputs

- The project, its git state, and the thin map from `pdlc:recon`.
- The `references/` folder next to this file: `templates/`, `ports/`, `adapters/`, `bin/`,
  `reviews/`, and `defaults/`.
- The answers of the user, or `defaults`.

## Outputs

- The `pdlc/` folder, with the stub specs, the design specs, and a complete `config.md`.
- The commit "Set up pdlc" on `main` (the default branch), with the new `pdlc/` folder and
  no other changes. Init starts no branch, because the records of pdlc live on `main`.
- For the user: each decision that init made, each "Unsure" item, and how to start.
  `/pdlc:ship <what you want>` runs all the stages. The user can also run one stage at a
  time, from `/pdlc:intake`.
