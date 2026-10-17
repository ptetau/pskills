# pdlc

This folder holds the pdlc state for this project. Each pdlc skill reads this file first.

## Core rules

1. All work enters through the inbox.
2. Specs come before code. An intent must be `ready` before you plan a change for it.
3. A change covers exactly one job, one capability, or one design spec.
4. A job change uses capabilities, but does not edit them. A missing capability gets its
   own change, before the job change.
5. The test writer writes the checks before the code, from the spec only. Then the checks
   are locked. A writer of app code must not change the checks.
6. Reviews are independent. Each remit gets one fresh reviewer, and each reviewer sees only
   its packet.
7. A change merges only when its requirements are `verified`, its tests did not change
   after the lock, and each review remit passed. `bin/check_merge.py` checks all three.
8. These files are the truth. Boards and dashboards only show what these files contain.
9. Each commit has trace trailers (see `specs/design/DES-pdlc-commit-trailers.md`). A
   commit that touches only `pdlc/` does not need a `Req` trailer.
10. Write all text to the rules in `specs/design/DES-writing-style.md`: specs, intents,
    change specs, handoffs, commit messages, and replies to the user.

## Layout

- `config.md`: the adapters, how to run checks, the check folders, the review remits, the
  visual review settings, and the board columns.
- `ports/`: what each port does.
- `adapters/`: how this project does the work of each port.
- `reviews/`: one file for each review remit. Each file says what the reviewer of that
  remit judges.
- `inbox/`: one file for each intent.
- `specs/jobs/`, `specs/capabilities/`, `specs/design/`: the specs.
- `changes/CH-xxxx-name/`: one folder for each change, with these items:
  - `change.md`: the change spec.
  - `handoff.md`: the latest handoff between stages.
  - `visual.json`, `review.gif`, `frames/`: the visual review.
  - `review/<remit>/packet.md` and `result.md`: each independent review.
- `templates/`: blank copies of each document.
- `bin/`: `check_merge.py`, `make_packets.py`, `record_gif.mjs`.
- `.tools/`: the tools that the visual review installs. This folder is not committed.

## Who does what

| Who | Does | Never |
|---|---|---|
| main session (the skills) | plans, runs checks, commits, keeps the records | writes checks or app code for a change itself |
| `pdlc:test-writer` | writes checks from the spec | reads app code |
| `pdlc:builder` | writes app code until the checks pass | changes checks or `pdlc/` files |
| `pdlc:reviewer` | judges one packet for one remit | sees anything other than its packet |
| `pdlc:recon` | maps existing code | writes anything |

A guard in the pdlc plugin keeps the roles in these lanes.

## Stages and handoffs

The stages for an intent are intake → ready → change. The stages for each change are
tests → build → show → verify. `/pdlc:ship` runs all the stages.

Each stage first reads the latest handoff. At its end, each stage writes a new handoff:

- An intent stage writes the "Handoff" section of the intent. The sections of the template
  are `###` headings under that section. Thus, the full handoff stays inside that one
  section.
- A change stage writes `changes/CH-xxxx-name/handoff.md`.

Use `templates/handoff.md`. Take the time from the real clock (`date -Iseconds`). Replace
the old handoff. Git keeps the history.

## Where change state lives

The status, the lock, and the handoff of a change are committed on the branch of that
change. On main, a change that did not merge yet still has the status `planned`. Before
you select a change by its status, do these steps:

1. List the change branches (`git branch --list`).
2. Read the `change.md` of each change from its branch
   (`git show <branch>:pdlc/changes/<folder>/change.md`).

A change with no branch is `planned`.

## Stacked changes

A change is built on the branch of the change before it, also before that earlier change
merges. The `Base:` of the change names that branch, and the pull request of the change
targets that branch. The base of the first change is main.

## Statuses

- Intent: new → specifying → ready → building → in review → done. Also paused, cancelled.
- Requirement: proposed → ready → built → verified. Also retiring.
- Change: planned → testing → building → in review → merged. Also cancelled.
- Spec file: stub (no requirements written yet) or active.

## Asking questions

Ask the user one short question at a time. Offer two or three answers. Mark the answer
that you recommend, and give one line on why. The user can reply `skip` to take the
recommended answer.

A skill can decide something without an instruction (a name, a limit, a default answer).
Mark each such decision *(assumed)* where you write it. Also list the decision in the
handoff. Thus, no guess stays hidden.

If the skill runs with `defaults`, do not ask. Take your recommended answer. Record each
answer as `<question> → <answer> (default)` in two places: "Decided on defaults" in the
handoff, and "Notes" in the intent. Then the user can change the answer later.

## Before any work

First, record the merges. For each change with status `in review`, ask the delivery port
if the change merged. If the change merged, set the change to `merged`. Then find each next
change of each merged change. A next change is a change whose `Base:` is the branch of the
merged change. For each merged change and each of its next changes, do these steps:

1. Set the `Base:` of the next change to the base of the merged change.
2. Commit the new `Base:` on the branch of the next change.
3. If the next change has a pull request, retarget the pull request to the same base.

When all the changes of an intent are merged, set the intent to `done`.

## pdlc's own files

`README.md`, `ports/`, `adapters/`, `templates/`, and `bin/` come from the pdlc plugin.
These files change only when pdlc is upgraded, on main, in a commit of their own. Do not
change these files on the branch of a change. An upgrade can also refresh the `DES-pdlc-*`
design specs and the `reviews/` files that still say `Default: yes`. When the project
changes one of these specs or files, the file says `Default: no` and belongs to the
project.

## Using a port

To use a port, do these steps:

1. Read `ports/<port>.md` to find what the port does.
2. Find the adapter of the port in `config.md`.
3. Follow `adapters/<adapter>.md`.

If a port covers a tool, do not call that tool directly.

## After any status change

Tell the tracker port about the intent or the change whose status changed. If the tracker
is `none`, skip this step.
