# pdlc

This folder holds the pdlc state for this project. This file holds the definitions and the
rules that all pdlc skills share. Each skill reads this file first, and names its sections.

## Core rules

1. pdlc runs only on a Sonnet 5.5 class model or above. On a lower model, for example a
   Haiku model, a pdlc skill or agent does no work. The skill or agent tells the user that
   pdlc needs a Sonnet 5.5 class model or above.
2. All work enters through the inbox.
3. Specs come before code. pdlc plans a change only for a `ready` intent.
4. A change covers exactly one job, one capability, or one design spec.
5. A job change uses capabilities, but does not edit their code ("Code maps"). A missing
   capability gets its own change, before the job change.
6. The test writer writes the checks from the spec, before the code. The acceptance checks
   of the intent come first, then the component checks of each change. An intent with one
   change usually has only its acceptance checks ("Acceptance checks"). A writer of app code does
   not change a locked check.
7. Each review remit gets one fresh reviewer, and the reviewer sees only its packet.
8. A change merges only when all of these are true, as `bin/check_merge.py` confirms:
   - The requirements of the change are `verified`.
   - Each "Interface" entry of the change is in the "Interface" of its spec, with the
     same error codes, and is not `proposed` there ("Interfaces").
   - The tests of the change did not change after the lock.
   - Each review remit passed.
   - The branch of the change merges into main without conflicts.
   - Every other change of the intent is `in review` or `merged`.
   - The acceptance checks of the intent are locked, reviewed, and passed at its last
     change.
9. These files are the truth. Boards and dashboards only show what these files contain.
10. The specs are sufficient to rebuild the project. The specs are the job, capability,
    and design specs in `specs/`, and `config.md`. A new build from the specs alone
    passes each acceptance check of the project. Change specs are history, not specs.
    Thus, each name that a check calls is in the "Interface" of a job or capability
    ("Interfaces").

## Commits

- The subject comes from "Subjects" in `specs/design/DES-pdlc-commit-trailers.md`. Each
  skill gives its subjects.
- The trailers follow a blank line, one on each line: `Intent: IN-xxxx` first, then
  `Change: CH-xxxx` on the branch of a change. A commit that changes code, checks, or the
  README also has `Req: <IDs>`.
- The pdlc trailers are the last paragraph of the message. Any other trailer, such as
  `Co-Authored-By`, goes directly under them, with no blank line between them.
- A hook examines each new commit. On a pdlc branch, it examines the subject and the
  trailers. On every branch, it examines the trailers of a commit with a pdlc subject.
  Also on every branch, it examines the writing in the specs, the intents, and the change
  folders. The skill fixes all the problems that the hook names in one edit, and
  amends the commit one time.

## Writing

- All text obeys `specs/design/DES-writing-style.md`: specs, intents, change specs,
  handoffs, commits, pull requests, review results, code comments, and replies.
- In short: 25 words or fewer in a sentence (20 in an instruction), the active voice, and
  one topic. The text has "must" or "can", not "should", and no semicolon. Each ID has a
  short description in the same sentence, as in `R5 (usage line)`.
- The limit holds also in an acceptance line. A long line becomes two lines, or ends its
  "then" part with a full stop and a second short sentence.
- A skill reads the full rules before it writes or changes a spec or an intent. For a
  handoff, a proposal, a commit message, or a reply, the short form is sufficient.
- The commit hook runs `bin/check_writing.py` on the lines that each commit writes, and
  shows every finding. Part 4 of `DES-writing-style` tells a writer to run the script. In
  pdlc, the hook does this step, and a skill does not run the script.

## Layout

- `config.md`: the adapters, the check commands and folders, the review remits, the visual
  settings, and the board columns.
- `ports/`: what each port does. `adapters/`: how this project does it.
- `reviews/`: one file for each remit, with what its reviewer judges.
- `inbox/`: one file for each intent.
- `specs/jobs/`, `specs/capabilities/`, `specs/design/`: the specs.
- `acceptance/IN-xxxx-name/`: `brief.md` of the test writer, and in `review/tests/`, the
  `packet.md` and `result.md` of the review of the acceptance checks of an intent.
- `changes/CH-xxxx-name/`: one folder for each change. It holds `change.md` (the change
  spec), `handoff.md`, `brief.md` of the test writer, `visual.json`, `review.gif`,
  `frames/`, `review/<remit>/packet.md` and `result.md`, and `proposal.md` when there is no
  remote.
- `templates/`: blank documents. A filled document has real content in place of each
  `<placeholder>` and each guide sentence.
- `bin/`: `check_handoff.py`, `check_merge.py`, `check_order.py`, `check_writing.py`,
  `make_packets.py`, `record_gif.mjs`, `record_merges.py`.
- `version.json`: the pdlc version of these files, and the hash of each file that pdlc wrote.
  Only `/pdlc:upgrade` and init write it.
- `.tools/`: the tools of the visual review. This folder is not committed.
- `.logs/`: the debug log of each ship run, `ship-<UTC start>.jsonl`, one JSON object on
  each line. A hook of the pdlc plugin writes it. This folder is not committed. After an
  interruption or an API error, type `/pdlc:ship` to continue, because a normal prompt ends
  the run.

## Code maps

The "Code map" of each job and capability lists what it owns, and gives the scope of a
change.

- A job owns its entry points (a route or request handler, a command, a page script or
  event handler), with its line in any routing table or command list.
- A capability owns the shared logic under them: storage, outside services, and the
  plumbing every job uses (starting the server, routing, reading a request, writing a
  reply).
- A file with parts of several specs is shared. Each code map names its parts:
  `src/server.py: POST /reset route and handle_reset` for a job, and
  `src/server.py: the rest` for the capability that holds the plumbing.
- A change can list a shared file in "Files" with its own parts, and edits only those
  parts. A new route or command adds its own part beside the others.
- The README of the project is in no code map. A change changes only what the README says
  about its own spec, and how to run the app and the checks.

## Interfaces

The "Interface" of each job and capability lists what a check can call. The names are
in the specs, so a rebuild from the specs keeps them, and the checks still pass.

- A job lists what its user touches: commands and flags, routes, form fields, and the
  page elements and page text that a check reads.
- A capability lists the calls that jobs use: the public functions, each with its file.
- Each test seam goes under "Test seams" in the "Interface" of the spec that owns it.
  A seam controls the clock, randomness, or an outside vendor or store.
- The first line of an entry gives the name in backticks, the kind, and the file. The
  merge check matches entries by the first text in backticks.
- Under the first line, "in" and "out" give what goes in and what comes out. For a
  command, "out" names the stream, for example "on standard output", and the exit code.
- "errors" is `errors: none`, or `errors:` with one line under it for each error. Each line
  gives the code, the exact message, and the result, with ` · ` between them:
  `` - `TOP_INVALID` · `error: --top needs a whole number greater than zero` · exit 2 · stderr ``.
  The result is `exit <n>` for a command, `status <n>` for a route, or `raises <Name>` for a
  function.
- A command error ends with the stream that gets the message: `stderr` or `stdout`. On
  an error, a command writes only the message to that stream, and the other stream is
  empty, unless "out" says otherwise. A route error and a function error have no stream.
- The code comes from `DES-errors`. An error that the app gives today, with no code in
  `DES-errors`, has `no code`. When a line of an intent uses that error, the error gets a
  code, as each failure line does. A function error with no message has `no message`.
- Each entry has an `errors:` line. An `(assumed)` mark goes after the code, the message,
  or the result that is a guess: `` - `USAGE` (assumed) · `usage: …` (assumed) · exit 2 · stderr ``.
  The merge check leaves the marks out when it compares.
- `errors: none` has nothing after it. The merge check compares the code, the message,
  the result, and the stream of each error, and refuses any other form.
- A new entry ends its first line with ` · proposed`. The `verify` stage removes the
  mark in the scope spec when the change that builds the entry passes.
- When a requirement retires, each entry that only it used gets ` · retiring`. The
  build stage removes that entry with its code.
- Intake writes the entries that the acceptance lines need. Recon writes the entries of
  existing code, with no mark.
- A change spec copies each entry that its checks call, word for word, as it copies
  the requirements, but without the mark. A job change that calls an entry of another
  job lists that job under "Relies on".
- A missing entry goes into its spec first, as `proposed`, and then into the change
  spec. This rule holds for the change stage, and for a missing item that the test
  writer reports.
- Suppose the spec that owns the item is not the scope of this change (at the change
  stage: of a change of this intent). Then the item goes into the scope spec of this
  change, or becomes a question for the user.
- The changes of an intent go in the order of their entries. A change comes after each
  change that builds an entry that its acceptance lines or its Interface use. It also
  comes after the change of each spec under its "Relies on". `bin/check_order.py`
  checks the order at the change stage.

```
- `send(template: TemplateName, to: Email) -> SentId` · function · `src/email.js`
  - in: the name of a template, and an email address
  - out: the ID of the sent email
  - errors:
    - `TEMPLATE_NOT_FOUND` · `no template named <name>` · raises `TemplateNotFound`
    - `INVALID_ADDRESS` · `not a valid email address: <address>` · raises `InvalidAddress`
```

A `<placeholder>` in a message is permitted only in a template. A spec gives the real message.

## Who does what

| Who | Does | Never |
|---|---|---|
| main session (the skills) | plans, runs checks, commits, keeps the records | writes checks or app code for a change itself |
| `pdlc:test-writer` | writes checks from the spec | reads app code |
| `pdlc:builder` | writes app code until the checks pass | changes checks or `pdlc/` files |
| `pdlc:reviewer` | judges one packet for one remit | sees anything other than its packet |
| `pdlc:recon` | maps existing code | writes anything |

A guard in the pdlc plugin keeps the roles in these lanes. For each agent:

- The skill gives absolute paths: the project root, and each file that the agent needs.
- The Agent tool starts the agent with `run_in_background: false`, so that the call
  returns the reply. Agents that work side by side (the reviewers) start in one message.
- No skill waits for an agent with a sleep, a loop, a monitor, or a notification. No skill
  stops an agent because it is slow.
- When the guard or a tool blocks an agent, the skill fixes the path, and runs the agent
  once more from the project root. A second block is one failure of the stage. A blocked
  agent is not a reason to stop.

## Stages and handoffs

The intent stages are intake → ready → change → acceptance. The change stages are tests →
build → `verify` → show. `/pdlc:ship` runs them all. Show records a change only after it
passed `verify`. An independent reviewer judges the recording, and then show proposes the
merge.

- Each stage starts from the latest handoff, and ends with a new one from
  `templates/handoff.md`, which replaces the old one. Git keeps the history.
- An intent stage writes the "Handoff" of the intent, with the template sections as `###`
  headings. A change stage writes `changes/CH-xxxx-name/handoff.md`.
- The title comes from the list in the template. Every section stays, with "- none" under an
  empty one. The time comes from the real clock (`date -Iseconds`).
- A handoff says only what the files show, with real counts of the checks that ran and of
  the acceptance lines shown.

At the end of each stage, and at each stop:

- The statuses that the stage owns are set. The tests stage sets `testing`, then
  `building`. The `verify` stage sets `in review` when everything passed.
  `bin/record_merges.py` sets `merged` and `done`.
- Everything that the stage wrote is committed: specs, the intent, the change folder,
  packets, and results. `git status --porcelain` shows nothing.
- The files that the checks leave behind (caches, build output) are deleted, not
  committed. Init lists their folders in `.gitignore`.
- The tracker port knows each status that changed ("Ports").

## Checks before code

The acceptance stage and the tests stage share these rules. The lock line is
`Acceptance-Locked:` in the intent, or `Tests-Locked:` right under the header of the
change spec.

- Red: before the lock, each check of new behaviour fails. A check that passes goes back
  to the test writer with the reason.
- A check of existing behaviour (only the words changed) can pass. After a send-back from
  build or `verify`, app code exists, so a corrected check can pass. The skill records
  each such result in the progress log, or in the intent "Notes" for acceptance.
- A check that fails because a command, a route, or a function does not exist yet counts
  as failing. The error comes from the missing interface, not from a mistake in the check.
- A run has a time limit of a few minutes. A run that does not finish has a broken check,
  not a red one. The broken check goes back to the test writer before the lock.
- When the test writer reports a missing "Interface" item, the skill adds the item to its
  spec, as `proposed` ("Interfaces"). The skill can see the code. Then the skill copies
  the item into the change spec that builds it. Suppose the spec that owns the item is
  not the scope of this change. Then the item goes into the scope spec of this change,
  or becomes a question for the user. Then the test writer runs again.
- Lock: the commit of the checks. Its hash goes on the lock line, and replaces an older
  hash.
- After the lock, only the test writer changes the checks, and only through the skill of
  the stage. Each change makes a new lock, and each lock gets its own review. The merge
  check refuses a tests review of an older lock.
- Review: `bin/make_packets.py` makes the tests packet, and a fresh `pdlc:reviewer` gets
  only its path. A later packet is a re-review: the earlier problems, and the diff of the
  checks since the earlier lock. The reviewer judges only these two items.
- A failed review sends its problems to the test writer, and red, lock, and review run
  again ("Rounds"). The prompt of the test writer holds each problem as text, copied from
  `result.md`. The test writer cannot read a review, so the prompt does not give a path to
  one.

## Acceptance checks

Each intent has one acceptance file, at the "acceptance file" path in `config.md`. Its
checks prove the acceptance lines through what a user uses. They can use each feature of
the intent, and each feature that exists already.

- The acceptance stage writes, locks, and reviews the file before the first change.
  `Acceptance-File:` and `Acceptance-Locked:` in the intent record the file and the lock.
- A component check (a check of a change) uses only the interface of its change and of
  earlier changes.
- A **stored-data line** is an acceptance line that needs direct access to the stored data.
  The line is about the stored form (how a file or a store holds the data), or it needs a
  state that the interface cannot make (for example an old or a broken data file).
- A stored-data line gets a component check of the change that lists its requirement, and
  no acceptance check. At its top, the acceptance file lists each such line in a comment:
  the requirement ID, the line, and that change. The acceptance checks still prove what a
  user sees of the data, for example that it stays after a restart.
- The "all" command does not run an acceptance file. Thus, the acceptance checks of an
  open intent can fail until its last change, and main stays green.
- The build and `verify` stages run all checks and **run earlier acceptance**, and for the
  last change also **run acceptance**. Each check must pass. The `verify` stage writes the
  commit of that run on `Acceptance-Passed:`.
- For an earlier change, a failure of **run acceptance** is expected, and is not reported.
- After the intent merges, its acceptance checks stay, and each later change keeps them
  green.
- The intent can list one change, with no stored-data line. Then its acceptance checks
  are also the checks of that change. That change has `- none` under
  "Check files", and `Tests-Locked: acceptance`. Its tests stage starts the branch and
  writes the handoff, with no test writer and no review.
- For such a change, the acceptance review is also its tests review, and the merge check
  reads it. A problem with one of its checks goes to the acceptance stage.

## Rounds

A round is one failed tests or acceptance review, one failed `verify`, or one builder
report that a check is wrong. A failed visual review is also a round. A fix of a check
before its lock is not a round. An agent blocked twice is one round. Each change has two rounds, and so does the acceptance stage
of each intent. The third failure of the same stage stops the work, and the skill asks the
user.

## Where pdlc commits

- Init commits on main. So do intake, ready, and change while no pdlc branch is unmerged.
  The records of pdlc are not code, so this is by design, also where the usual rule is to
  branch first.
- The acceptance stage commits on the intent branch, `pdlc/IN-xxxx-<short-name>`, and
  starts it if necessary. Thus, the acceptance checks go to main only with their code.
- A change commits its code, status, lock, and handoff on its own branch. On main, an
  unmerged change still has the status `planned`.
- While any pdlc branch is unmerged, only `bin/record_merges.py` commits on main, and the
  intent stages work on the intent branch. That branch starts from the newest unmerged
  branch: the first line of
  `git branch --no-merged main --list 'pdlc/*' --sort=-committerdate`, with the pattern of
  `DES-pdlc-branches` (the branch names). The `Branch:` of the intent names it.
- Thus, the spec patches come after the work that they change, and every branch merges
  into main in order, with no conflicts.
- Nothing is committed on a branch that merged into main, not even a status or a `Base:`.
  Work found after a change merged is a new change. The merge check refuses the branch of
  a merged change if it has new commits.
- All work stays in the project checkout, not in a git worktree. The agents, the guard,
  and the scripts use the paths of the checkout.
- A skill commits its work before `git switch <branch>`. When `git switch` refuses, the
  skill commits or deletes what `git status` shows, for example `__pycache__/`.
- A skill selects an intent or a change by its status only where it lives. It lists the
  unmerged branches, and reads each `change.md` from its own branch
  (`git show <branch>:pdlc/changes/<folder>/change.md`). It reads each intent from the
  newest branch that has it. A change with no branch is `planned`.

## Stacked changes

A change is built on the branch of the change before it, also before that change merges.
Its `Base:` names that branch, and its pull request targets that branch.

- The base is the branch of the previous change in the intent "Changes". For the first
  change, it is the newest unmerged change of an earlier intent, or else main.
- If the intent has a `Branch:`, the first change starts from that branch, and so carries
  the spec patches and the acceptance checks. When that branch lacks the base
  (`git merge-base --is-ancestor <base> <intent branch>` fails), the tests stage merges the
  base into it first, with the trailer `Intent`.
- In that merge, a requirement that the intent changed keeps the text and status of the
  intent. Each other requirement keeps the text and status of the base.
- An "Interface" entry follows the same rule. If the base removed ` · proposed`, the
  entry keeps the base's line unless this intent changed it.
- The changes of an intent merge together, bottom first. The merge check fails each of
  them until all are `in review`.
- The base can merge into main before `verify` proposes the change
  (`git merge-base --is-ancestor <base> main` succeeds). Then `Base:` becomes main on the
  branch of the change, and the proposal targets main. A merged branch keeps its `Base:`.

## Statuses

- Intent: new → specifying → ready → building → in review → done. Also paused, cancelled.
- Requirement: proposed → ready → built → verified. Also retiring.
- Change: planned → testing → building → in review → merged. Also cancelled.
- Spec file: stub (no requirements written yet) or active.

## Questions

- A question is short, and comes one at a time, with two or three answers. The recommended
  answer has a mark and one line on why. The reply `skip` takes it.
- A decision that a skill makes without an instruction (a name, a limit, a message, an
  order, a default answer) has the mark `(assumed)` where the spec or change spec states
  it. The handoff lists it too. `bin/check_handoff.py` makes sure that the list names each
  new mark. Thus, no guess stays hidden.
- The mark is plain, right after the words that it marks, with any reason outside the
  brackets: "at most 20 items (assumed), to keep the list short". In a change, the merge
  check rejects `(limit assumed)`, `*(assumed)*`, and each mark that does not start with
  `(assumed`.
- With `defaults`, a skill asks nothing, and takes its recommended answer. Each answer goes
  as `- <requirement>: <question> → <answer> (assumed)` in "Decided on defaults" in the
  handoff and in the intent "Notes", so that the user can change it.

## Spec patches

These rules hold each time that a skill writes or changes a spec.

- Where a behaviour belongs:
  - What a user does through a route, a command, or a page, and gets back: a **job**,
    also in a shared file.
  - What the system offers to jobs (a store, an outside service, shared plumbing): a
    **capability**. Its requirements give what it offers to jobs, not the behaviour of one
    job.
  - How the project does something everywhere: a **design** spec.
  - How the output of one job looks (a format, a wording, a layout): that **job**, also
    when a capability makes the value. The job has a line for each place that shows it.
  - A behaviour that many jobs share (a reply format, an error shape, an unreadable store,
    a size limit on each request): one time, in the capability or design spec that those
    jobs use. For example, "every email has an unsubscribe link" goes in `CAP-email`.
  - An existing spec comes first. A new capability has its boundary around a thing that is
    likely to change (a vendor, a set of rules, a store), and is named for it:
    `CAP-payments`, not `CAP-checkout-button`.
- The words of the intent bind. Each example in the intent (an output, a message, a value)
  is an acceptance line, exactly. The plain reading holds for every value, also zero,
  empty, and an integer. No `(assumed)` reading or recommendation narrows the words to
  keep the old behaviour, or changes the result of an example.
- The newest words win. When the intent asks for something that an older requirement or
  an `(assumed)` detail rules out, the older text changes to match. This case is a changed
  requirement, not a contradiction. The intent "Notes" get
  `<ID>: was "<old>", now "<new>"`.
- No old wording. For each changed or retired requirement, a search of `pdlc/specs/` and
  the README finds the old words (a command, a message, a value, a button). No title,
  summary, example, acceptance line, note, "Known gap" line, or "Changes" list in the
  specs shows them. Each cross-reference (`see CAP-x.R4`) points at the rule it means.
- The README is app code, so a spec stage does not edit it. Each README line with old
  behaviour gets `README: "<old line>" → <requirement>` in the intent "Notes". The change
  for that requirement fixes the line.
- A spec stage does not edit a change spec (`changes/*/change.md`). An unmerged change
  keeps what it copied.

## New behaviour needs approval

New behaviour is behaviour that no acceptance line, design spec, or remit rule asks for.
Nobody builds it on the branch of a change. The `verify` stage files it as a `new` intent
whose "Notes" start with `Awaits approval:`. No skill takes up such an intent on its own,
also with `defaults`. Work starts only when the user names it, and then the line goes.

## Bookkeeping on main

Before any work, each skill that names this section switches to main, pulls main if there
is a remote, and runs `python3 pdlc/bin/record_merges.py`. The script sets each change
whose branch merged to `merged`, and each intent whose changes all merged to `done`. Then
it commits those records on main. Nobody does this bookkeeping by hand, or on another
branch.

## pdlc's own files

`README.md`, `ports/`, `adapters/`, `templates/`, `bin/`, and the `reviews/` and
`specs/design/` files that say `Default: yes` come from the pdlc plugin. `/pdlc:upgrade`
refreshes each of these files that the project did not change, and keeps each changed file.
`version.json` records the version and the content that pdlc wrote. A file that the project
changes on purpose says `Default: no`, and belongs to the project.

- The upgrade commits "Upgrade pdlc" on main, or on the newest unmerged pdlc branch, as the
  intent stages do ("Where pdlc commits").
- The upgrade does not write a spec. A spec that needs a newer form goes into one intent that
  waits for approval.

## Ports

- Each port works through its adapter: `ports/<port>.md` says what the port does,
  `config.md` names the adapter, and `adapters/<adapter>.md` says how.
- No skill calls a tool directly when a port covers that tool.
- After each status change of an intent or a change, the tracker port gets it. With the
  tracker `none`, nothing happens.
