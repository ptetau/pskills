# pdlc

This folder holds pdlc's state for this project. Every pdlc skill reads this file first.

## Core rules

1. All work enters through the inbox.
2. Specs come before code. An intent must be `ready` before any change is planned.
3. A change covers exactly one job, one capability, or one design spec.
4. A job change uses capabilities but never edits them. A missing capability becomes its
   own earlier change.
5. A change merges only when every requirement it touches is `verified`.
6. These files are the truth. Boards only show them.
7. Every commit carries trace trailers (see `specs/design/DES-pdlc-commit-trailers.md`).
8. Write plainly (see `specs/design/DES-writing-style.md`).

## Layout

- `config.md`: which adapter fills each port, how to run checks, board columns.
- `ports/`: what each port does. `adapters/`: how this project does it.
- `inbox/`: one file per intent.
- `specs/jobs/`, `specs/capabilities/`, `specs/design/`: the specs.
- `changes/`: one change spec per change.
- `templates/`: blank copies of each document.
- `bin/check_merge.py`: the merge check. CI can run it too.

## Statuses

- Intent: new → specifying → ready → building → in review → done. Also paused, cancelled.
- Requirement: proposed → ready → built → verified. Also retiring.
- Change: planned → building → in review → merged. Also cancelled.
- Spec file: stub (no requirements written yet) or active.

## Using a port

To use a port, read `ports/<port>.md` for what it does, then find the port's adapter in
`config.md` and follow `adapters/<adapter>.md`. Never call a tool directly when a port
covers it.

## Before any work

Catch up on merges. For each change with status `in review`, ask the delivery port if it has
merged. If it has, set the change to `merged`. When every change for an intent has merged,
set the intent to `done`.

## After any status change

Tell the tracker port about the intent or change whose status changed. If the tracker is
`none`, skip this.
