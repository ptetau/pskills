# pdlc

This folder holds pdlc's state for this project. Every pdlc skill reads this file first.

## Core rules

1. All work enters through the inbox.
2. Specs come before code. An intent must be `ready` before any change is planned.
3. A change covers exactly one job, one capability, or one design spec.
4. A job change uses capabilities but never edits them. A missing capability becomes its
   own earlier change.
5. Checks are written before code, by the test writer, from the spec alone. Then they are
   locked. Nobody who writes app code may change them.
6. Reviews are independent: one fresh reviewer per remit, each seeing only its packet.
7. A change merges only when its requirements are `verified`, its tests are unchanged
   since the lock, and every review remit passed. `bin/check_merge.py` checks all three.
8. These files are the truth. Boards and dashboards only show them.
9. Every commit carries trace trailers (see `specs/design/DES-pdlc-commit-trailers.md`).
   Commits that only touch `pdlc/` need no `Req`.
10. Write plainly (see `specs/design/DES-writing-style.md`).

## Layout

- `config.md`: adapters, how to run checks, check folders, review remits, visual review
  settings, board columns.
- `ports/`: what each port does. `adapters/`: how this project does it.
- `reviews/`: one file per review remit, saying what that reviewer judges.
- `inbox/`: one file per intent.
- `specs/jobs/`, `specs/capabilities/`, `specs/design/`: the specs.
- `changes/CH-xxxx-name/`: one folder per change, holding:
  - `change.md`: the change spec;
  - `handoff.md`: the latest handoff between stages;
  - `visual.json`, `review.gif`, `frames/`: the visual review;
  - `review/<remit>/packet.md` and `result.md`: each independent review.
- `templates/`: blank copies of each document.
- `bin/`: `check_merge.py`, `make_packets.py`, `record_gif.mjs`.
- `.tools/`: tools the visual review installs. Not committed.

## Who does what

| Who | Does | Never |
|---|---|---|
| main session (the skills) | plans, runs checks, commits, keeps the records | writes checks or app code for a change itself |
| `pdlc:test-writer` | writes checks from the spec | reads app code |
| `pdlc:builder` | writes app code until the checks pass | changes checks or `pdlc/` files |
| `pdlc:reviewer` | judges one packet for one remit | sees anything but its packet |
| `pdlc:recon` | maps existing code | writes anything |

A guard in the pdlc plugin enforces these lanes.

## Stages and handoffs

For an intent: intake → ready → change. For each change: tests → build → show → verify.
`/pdlc:ship` runs them all.

Every stage starts by reading the latest handoff, and ends by writing one:

- intent stages write the intent's "Handoff" section, with the template's sections as
  `###` headings under it, so the whole handoff stays inside that one section;
- change stages write `changes/CH-xxxx-name/handoff.md`.

Use `templates/handoff.md`. Take the time from the real clock (`date -Iseconds`). Replace
the old handoff; git keeps the history.

## Where change state lives

A change's status, lock and handoff are committed on its own branch. On main, a change
that hasn't merged still reads `planned`. Before picking a change by its status, list the
change branches (`git branch --list`) and read each change's `change.md` from its branch
(`git show <branch>:pdlc/changes/<folder>/change.md`). A change with no branch is
`planned`.

## Stacked changes

A change is built on the branch of the change before it, even before that one merges.
Its `Base:` names that branch, and its pull request targets it. The first change's base is
main.

## Statuses

- Intent: new → specifying → ready → building → in review → done. Also paused, cancelled.
- Requirement: proposed → ready → built → verified. Also retiring.
- Change: planned → testing → building → in review → merged. Also cancelled.
- Spec file: stub (no requirements written yet) or active.

## Asking questions

Ask the user one short question at a time. Offer two or three answers and mark the one you
recommend, with one line on why. The user can reply `skip` to take it.

Anything a skill decides without being told (a name, a limit, a default answer) is
marked *(assumed)* where it is written, and listed in the handoff, so nothing is guessed
silently.

If the skill was run with `defaults`, don't ask. Take your recommended answer, and record
each one in the handoff's "Decided on defaults" and the intent's "Notes" as
`<question> → <answer> (default)` so the user can change it later.

## Before any work

Catch up on merges. For each change with status `in review`, ask the delivery port if it
has merged. If it has, set the change to `merged`. For any change whose `Base:` is its
branch, set that `Base:` to the merged change's own base, commit it on that change's
branch, and retarget its pull request (if it has one) to the same base. When every change for an intent has merged, set
the intent to `done`.

## pdlc's own files

`README.md`, `ports/`, `adapters/`, `templates/` and `bin/` come from the pdlc plugin. They
change only when pdlc is upgraded, on main, in a commit of their own. Never change them on
a change's branch. An upgrade may also refresh `DES-pdlc-*` design specs and `reviews/`
files that still say `Default: yes`. Once the project changes one, it says `Default: no`
and belongs to the project.

## Using a port

To use a port, read `ports/<port>.md` for what it does, then find the port's adapter in
`config.md` and follow `adapters/<adapter>.md`. Never call a tool directly when a port
covers it.

## After any status change

Tell the tracker port about the intent or change whose status changed. If the tracker is
`none`, skip this.
