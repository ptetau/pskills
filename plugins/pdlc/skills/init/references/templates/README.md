# pdlc

This folder holds pdlc's state for this project. Every pdlc skill reads this file first.

## Core rules

1. All work enters through the inbox.
2. Specs come before code. An intent must be `ready` before any change is planned.
3. A change covers exactly one job, one capability, or one design spec.
4. A job owns its entry points: its routes or request handlers, commands, page scripts.
   A capability holds only the shared logic under them. A job change uses capabilities
   but never edits their code. A missing capability becomes its own earlier change.
5. Checks are written before code, by the test writer, from the spec alone. Then they are
   locked. Nobody who writes app code may change them.
6. Reviews are independent: one fresh reviewer per remit, each seeing only its packet.
7. A change merges only when its requirements are `verified`, its tests are unchanged
   since the lock, every review remit passed, its branch merges into main without
   conflicts, and every other change of its intent is `in review` or `merged`. An
   intent's changes merge together, bottom of the stack first. `bin/check_merge.py`
   checks all of this.
8. These files are the truth. Boards and dashboards only show them.
9. Every commit has a subject and trace trailers from
   `specs/design/DES-pdlc-commit-trailers.md`. A hook checks each new commit on a pdlc
   branch; fix what it names at once, with `git commit --amend`.
10. Write everything as `specs/design/DES-writing-style.md` (the writing rules) says: specs,
    handoffs, commit messages, pull requests, review results, code comments and messages
    to the user.

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
  - `review/<remit>/packet.md` and `result.md`: each independent review;
  - `proposal.md`: the merge proposal, when the project has no remote.
- `templates/`: blank copies of each document. When you write one, replace each
  `<placeholder>` and the guide sentence under each heading with real content.
- `bin/`: `check_merge.py`, `check_writing.py`, `make_packets.py`, `record_gif.mjs`,
  `record_merges.py`.
- `.tools/`: tools the visual review installs. Not committed.

## Code maps

Each job and capability lists what it owns in its "Code map". Changes are scoped by it.

- A job owns its entry points (a route or request handler, a command, a page script or
  event handler), with its line in any routing table or command list.
- A capability owns the shared logic under them: storage, outside services, and the
  plumbing every job uses (starting the server, routing, reading a request, writing a
  reply).
- A file that holds parts of several specs is shared. Each code map names its parts:
  `src/server.py: POST /reset route and handle_reset` for a job, and
  `src/server.py: the rest` for the capability that holds the plumbing.
- A change may list a shared file in "Files", with its own parts. It changes only those
  parts. A new route or command adds its own part beside the others.
- The project's README is in no code map. A change changes only what the README says
  about its own spec, and how to run the app and the checks.

## Who does what

| Who | Does | Never |
|---|---|---|
| main session (the skills) | plans, runs checks, commits, keeps the records | writes checks or app code for a change itself |
| `pdlc:test-writer` | writes checks from the spec | reads app code |
| `pdlc:builder` | writes app code until the checks pass | changes checks or `pdlc/` files |
| `pdlc:reviewer` | judges one packet for one remit | sees anything but its packet |
| `pdlc:recon` | maps existing code | writes anything |

A guard in the pdlc plugin enforces these lanes.

Starting an agent:

- Give it absolute paths: the project root, and the full path of each file it needs.
- Run it in the foreground and wait for its reply. Agents that work side by side (the
  reviewers) start together, in one message. Never stop an agent for being slow.
- If the guard or a tool blocks it, fix the path and run it once more from the project
  root. If it fails again, that counts as one failure of its stage. A blocked agent is
  never a reason to stop.

## Stages and handoffs

For an intent: intake → ready → change. For each change: tests → build → show → verify.
`/pdlc:ship` runs them all.

Every stage starts by reading the latest handoff, and ends by writing one:

- intent stages write the intent's "Handoff" section, with the template's sections as
  `###` headings under it, so the whole handoff stays inside that one section;
- change stages write `changes/CH-xxxx-name/handoff.md`.

Use `templates/handoff.md`. Its title is one from the template's list. Keep every
section, with "none" under one that is empty. Take the time from the real clock
(`date -Iseconds`). Replace the old handoff; git keeps the history.

Every stage, and every stop, ends the same way:

- It sets the statuses it owns: tests sets `testing`, then `building`; verify sets
  `in review` when everything passed; `bin/record_merges.py` sets `merged` and `done`.
- It commits everything it wrote: specs, the intent, the change folder, review packets
  and results. Then `git status --porcelain` shows nothing. Files the checks leave
  behind (caches, build output) are deleted, never committed; init lists their folders
  in `.gitignore`.
- Its handoff says only what the files show. Count, don't estimate: checks that ran,
  acceptance lines shown.

## Where pdlc commits

- Init, and the intent stages (intake, ready, change) when no pdlc branch is unmerged,
  commit on main. pdlc's records aren't code, so this is by design, even where the usual
  rule is to branch first.
- A change commits on its own branch: its code, status, lock and handoff. On main, a
  change that hasn't merged still reads `planned`.
- While any pdlc branch is unmerged, nothing is committed on main except what
  `bin/record_merges.py` commits. The intent stages work on the intent's own branch,
  `pdlc/IN-xxxx-<short-name>`, started from the newest unmerged branch: the first line of
  `git branch --no-merged main --list 'pdlc/*' --sort=-committerdate` (use the pattern
  in `DES-pdlc-branches`). The intent's `Branch:` names it. Its spec patches then come
  after the work they change, so every branch merges into main in order, with no
  conflicts.
- Never commit on a branch that has merged into main, not even a status or a `Base:`.
  Work found after a change merged is a new change. The merge check refuses a merged
  change's branch with new commits.

Before picking an intent or a change by its status, list the unmerged branches. Read each
change's `change.md` from its own branch
(`git show <branch>:pdlc/changes/<folder>/change.md`), and each intent from the newest
branch that has it. A change with no branch is `planned`.

## Stacked changes

A change is built on the branch of the change before it, even before that one merges.
Its `Base:` names that branch, and its pull request targets it. An intent's first change
is based on the newest unmerged change of an earlier intent, or on main if there is none.
If the intent has a `Branch:`, its first change starts from that branch, so it carries
the intent's spec patches into the same pull request. If that branch doesn't hold the
change's base yet, the tests skill merges the base into it first.

An intent's changes merge together, bottom of the stack first. The merge check fails
each of them until all are `in review`. If a change's base has merged into main before
the change is proposed (`git merge-base --is-ancestor <base> main`), set its `Base:` to
main on its own branch and propose against main. Never rewrite `Base:` on a branch that
has merged.

## Statuses

- Intent: new → specifying → ready → building → in review → done. Also paused, cancelled.
- Requirement: proposed → ready → built → verified. Also retiring.
- Change: planned → testing → building → in review → merged. Also cancelled.
- Spec file: stub (no requirements written yet) or active.

## Asking questions

Ask the user one short question at a time. Offer two or three answers and mark the one you
recommend, with one line on why. The user can reply `skip` to take it.

Anything a skill decides without being told (a name, a limit, a message, an order, a
default answer) is marked `(assumed)` where it is written in a spec or change spec, and
listed in the handoff, so nothing is guessed silently. Write the marker exactly so: plain,
right after what it marks, with any reason outside the brackets ("at most 20 items
(assumed), to keep the list short"). The merge check rejects any other form in a change.

If the skill was run with `defaults`, don't ask. Take your recommended answer, and record
each one in the handoff's "Decided on defaults" and the intent's "Notes" as
`<question> → <answer> (assumed)` so the user can change it later.

## Before any work

Switch to main, pull it if there is a remote, and run
`python3 pdlc/bin/record_merges.py`. It sets each change whose branch has merged to
`merged`, and each intent whose changes have all merged to `done`, and commits that on
main. Never do this bookkeeping by hand, and never on another branch.

## New behaviour needs approval

A review point that needs new behaviour (no acceptance line, design spec or remit rule
asks for it) is never built on a change's branch. Verify files it as a new intent, status
`new`, whose "Notes" start with `Awaits approval:`. No skill takes up such an intent on
its own, even with `defaults`. It starts only when the user names it; then remove that
line.

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
