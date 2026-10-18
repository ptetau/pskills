# pdlc

This folder holds the pdlc state for this project. Each pdlc skill reads this file first.

## Core rules

1. All work enters through the inbox.
2. Specs come before code. An intent must be `ready` before you plan a change for it.
3. A change covers exactly one job, one capability, or one design spec.
4. A job owns its entry points: its routes or request handlers, commands, and page
   scripts. A capability holds only the shared logic under the entry points. A job change
   uses capabilities, but does not edit their code. A missing capability gets its own
   change, before the job change.
5. The test writer writes the checks before the code, from the spec only. Then the checks
   are locked. A writer of app code must not change the checks.
6. Reviews are independent. Each remit gets one fresh reviewer, and each reviewer sees only
   its packet.
7. A change merges only when all of these are true:
   - The requirements of the change are `verified`.
   - The tests of the change did not change after the lock.
   - Each review remit passed.
   - The branch of the change merges into main without conflicts.
   - Every other change of the same intent is `in review` or `merged`.

   The changes of an intent merge together, with the bottom of the stack first.
   `bin/check_merge.py` checks all of these conditions.
8. These files are the truth. Boards and dashboards only show what these files contain.
9. Each commit has a subject and trace trailers (see
   `specs/design/DES-pdlc-commit-trailers.md`). The trailers come after a blank line, one
   on each line. Write `Intent: IN-xxxx` first. On the branch of a change, add
   `Change: CH-xxxx`. When the commit changes code, checks, or the README, add
   `Req: <IDs>`. The skill of each stage gives the subject. A hook checks each new commit
   on a pdlc branch. Fix what the hook names at once, with `git commit --amend`.
10. Write all text to the rules in `specs/design/DES-writing-style.md`. This includes
    specs, intents, change specs, handoffs, commit messages, pull requests, review
    results, code comments, and replies to the user. The rules in short: write sentences
    of 25 words or fewer (20 in an instruction), in the active voice, with one topic in
    each sentence. Write "must" or "can", not "should". Do not use a semicolon. Give
    each ID a short description in the same sentence, as in `R5 (usage line)`. Read the
    full rules before you write or change a spec or an intent. For a handoff, a proposal,
    a commit message, or a reply, the short form is sufficient.
    `bin/check_writing.py <file>` finds the breaks that a script can find.

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
  - `proposal.md`: the merge proposal, when the project has no remote.
- `templates/`: blank copies of each document. When you write one, replace each
  `<placeholder>` and the guide sentence under each heading with real content.
- `bin/`: `check_merge.py`, `check_writing.py`, `make_packets.py`, `record_gif.mjs`,
  `record_merges.py`.
- `.tools/`: the tools that the visual review installs. This folder is not committed.

## Code maps

Each job and capability lists what it owns in its "Code map". The scope of a change comes
from that code map.

- A job owns its entry points (a route or request handler, a command, a page script or
  event handler), with its line in any routing table or command list.
- A capability owns the shared logic under them: storage, outside services, and the
  plumbing every job uses (starting the server, routing, reading a request, writing a
  reply).
- A file that holds parts of several specs is shared. Each code map names its parts:
  `src/server.py: POST /reset route and handle_reset` for a job, and
  `src/server.py: the rest` for the capability that holds the plumbing.
- A change is permitted to list a shared file in "Files", with its own parts. The change
  edits only those parts. A new route or command adds its own part beside the others.
- The project's README is in no code map. A change changes only what the README says
  about its own spec, and how to run the app and the checks.

## Who does what

| Who | Does | Never |
|---|---|---|
| main session (the skills) | plans, runs checks, commits, keeps the records | writes checks or app code for a change itself |
| `pdlc:test-writer` | writes checks from the spec | reads app code |
| `pdlc:builder` | writes app code until the checks pass | changes checks or `pdlc/` files |
| `pdlc:reviewer` | judges one packet for one remit | sees anything other than its packet |
| `pdlc:recon` | maps existing code | writes anything |

A guard in the pdlc plugin keeps the roles in these lanes.

Starting an agent:

- Give it absolute paths: the project root, and the full path of each file it needs.
- Start it with the Agent tool, with `run_in_background: false`. Then the tool call
  returns the reply of the agent. Do not wait for an agent with a sleep, a loop, a
  monitor, or a notification. Start agents that work side by side (the reviewers) in one
  message, each with `run_in_background: false`. Do not stop an agent because it is slow.
- If the guard or a tool blocks an agent, fix the path. Then run the agent once more from
  the project root. If the agent fails again, that counts as one failure of its stage. A
  blocked agent is not a reason to stop.

## Stages and handoffs

The stages for an intent are intake → ready → change. The stages for each change are
tests → build → show → verify. `/pdlc:ship` runs all the stages.

Each stage first reads the latest handoff. At its end, each stage writes a new handoff:

- An intent stage writes the "Handoff" section of the intent. The sections of the template
  are `###` headings under that section. Thus, the full handoff stays inside that one
  section.
- A change stage writes `changes/CH-xxxx-name/handoff.md`.

Use `templates/handoff.md`. Take the title from the list in the template. Keep every
section, and write "none" under a section that is empty. Take the time from the real clock
(`date -Iseconds`). Replace the old handoff. Git keeps the history.

Each stage, and each stop, ends in the same way:

- The stage sets the statuses that it owns. The tests stage sets `testing`, then
  `building`. The verify stage sets `in review` when everything passed.
  `bin/record_merges.py` sets `merged` and `done`.
- The stage commits everything that it wrote: specs, the intent, the change folder, review
  packets, and results. Then `git status --porcelain` shows nothing. The stage deletes the
  files that the checks leave behind (caches and build output), and does not commit them.
  Init lists the folders of these files in `.gitignore`.
- The handoff of the stage says only what the files show. Count the checks that ran and
  the acceptance lines shown. Do not estimate.

## Where pdlc commits

- Init commits on main. The intent stages (intake, ready, change) also commit on main when
  no pdlc branch is unmerged. The records of pdlc are not code, so this is by design, also
  where the usual rule is to branch first.
- A change commits on its own branch: its code, status, lock, and handoff. On main, a
  change that did not merge yet still has the status `planned`.
- While any pdlc branch is unmerged, only `bin/record_merges.py` commits on main. The
  intent stages then work on the own branch of the intent, `pdlc/IN-xxxx-<short-name>`.
  That branch starts from the newest unmerged branch: the first line of
  `git branch --no-merged main --list 'pdlc/*' --sort=-committerdate`. In that command,
  use the branch pattern from `DES-pdlc-branches` (the branch names). The `Branch:` of the
  intent names the branch of the intent. The spec patches of the intent then come after
  the work that they change, so every branch merges into main in order, with no conflicts.
- Do not commit on a branch that merged into main, not even a status or a `Base:`. Work
  that you find after a change merged is a new change. The merge check refuses the branch
  of a merged change if the branch has new commits.

Before you select an intent or a change by its status, do these steps:

1. List the unmerged branches.
2. Read the `change.md` of each change from its own branch
   (`git show <branch>:pdlc/changes/<folder>/change.md`).
3. Read each intent from the newest branch that has it.

A change with no branch is `planned`.

## Stacked changes

A change is built on the branch of the change before it, also before that earlier change
merges. The `Base:` of the change names that branch, and the pull request of the change
targets that branch.

The first change of an intent is built on the newest unmerged change of an earlier intent.
If there is none, the first change is built on main. If the intent has a `Branch:`, the
first change starts from that branch. Then the first change carries the spec patches of
the intent into the same pull request. If that branch does not hold the base of the change
yet, the tests skill merges the base into that branch first.

The changes of an intent merge together, with the bottom of the stack first. The merge
check fails each of them until all are `in review`. The base of a change can merge into
main before the verify stage proposes the change (`git merge-base --is-ancestor <base> main`
succeeds). If so, set the `Base:` of the change to main on the branch of the change. Then
propose against main. Do not rewrite `Base:` on a branch that merged into main.

## Statuses

- Intent: new → specifying → ready → building → in review → done. Also paused, cancelled.
- Requirement: proposed → ready → built → verified. Also retiring.
- Change: planned → testing → building → in review → merged. Also cancelled.
- Spec file: stub (no requirements written yet) or active.

## Asking questions

Ask the user one short question at a time. Offer two or three answers. Mark the answer
that you recommend, and give one line on why. The user can reply `skip` to take the
recommended answer.

A skill can decide something without an instruction: a name, a limit, a message, an order,
or a default answer. Mark each such decision `(assumed)` where you write it in a spec or a
change spec. Also list the decision in the handoff. Thus, no guess stays hidden.

Write the marker plain, right after the words that it marks. Put any reason outside the
brackets, as in "at most 20 items (assumed), to keep the list short". The merge check
rejects any other form in a change.

If the skill runs with `defaults`, do not ask. Take your recommended answer. Record each
answer as `<question> → <answer> (assumed)` in two places: "Decided on defaults" in the
handoff, and "Notes" in the intent. Then the user can change the answer later.

## Before any work

Switch to main. If there is a remote, pull main. Then run
`python3 pdlc/bin/record_merges.py`. The script sets each change whose branch merged to
`merged`. It sets each intent whose changes all merged to `done`. Then it commits those
records on main.

Do not do this bookkeeping by hand. Do not do it on another branch.

## New behaviour needs approval

A review point can need new behaviour: behaviour that no acceptance line, design spec, or
remit rule asks for. Do not build it on the branch of a change. The verify stage adds it
as a new intent with the status `new`, whose "Notes" start with `Awaits approval:`. No
skill takes up such an intent on its own, also with `defaults`. Work on the intent starts
only when the user names it. Then remove the `Awaits approval:` line.

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
