# pdlc: outline

pdlc is a development lifecycle harness for AI-driven work. pdlc is a set of skills and
agents that you add to a project. The project can be new or old, and the project can be
any type of system. In pdlc, ideas become specs, specs become small changes, and changes
become verified code. You can trace each line of code back to the spec that it serves, and
to the intent that asked for it.

This outline is the design. We wrote the outline before we built anything. Thus, expect
changes to the outline.

---

## 1. The big idea

All work enters through an **inbox**. Each item in the inbox is an **intent**: something
that you want to be true, but that is not true yet.

An intent does not go directly to code. First, the intent becomes a change to the
**specs**. There are three types of spec:

- **Job specs** tell what a user tries to do. Each job has one file, for example "reset
  my password" or "pay an invoice".
- **Capability specs** tell what the system can do, independently of one specific job.
  Each capability has one file, for example "email" or "persistence".
- **Design specs** tell how we do things in all parts of the system. Design specs are
  conventions: how we show a list, how we name files, how we write errors, and how we
  test.

When the specs are sufficiently clear to build from, pdlc writes a **change spec**. A
change spec covers exactly one job or one capability. The change spec lists only these
items:

- The requirements that the change will deliver.
- The other specs that the change relies on.
- The files that the change must touch.

First, a test writer writes the checks of the change from the spec. The test writer does
not see the code. Then pdlc locks the checks. A builder writes the code, and the builder
cannot touch the checks.

When the code is complete, pdlc records the change as a GIF. Independent reviewers
judge the change: one reviewer for each remit, and each reviewer sees only its packet.
Then you approve the change. Only after these steps can the change merge.

```
 intent ─► spec patches ─► ready ─► change specs ─► tests ─► build ─► show ─► verify ─► merge
 (inbox)   (job/cap/design) (clarify, (one job or    (written  (builder, (GIF)  (checks +   (you
                            contra-   cap each,       first,    can't            6 inde-     approve)
                            dictions) stacked)        locked)   touch tests)     pendent
                                                                                 reviews)
```

---

## 2. Core rules

These rules are fixed. All other items are defaults that you can change.

1. **All work enters through the inbox.** This rule includes convention migrations and
   new adapters for pdlc itself.
2. **Specs come before code.** pdlc must specify an intent before it writes any change.
3. **One change, one thing.** A change covers exactly one job or one capability, or one
   design spec.
4. **Jobs use capabilities, but jobs do not edit capabilities.** If a job needs something
   that a capability cannot do yet, that new work becomes a separate, earlier milestone.
   Capability milestones always come before the job milestone that needs them.
5. **Verified before merge.** Each requirement that a change touches must be `verified`
   before the change can merge to main.
6. **pdlc files are the truth.** Boards and trackers show the state of pdlc. Boards and
   trackers do not own that state.
7. **Everything is traceable.** Code links to requirements. Requirements link to intents.
   Intents link to tickets.
8. **Plain prose everywhere.** Each skill, agent, prompt, and spec is short, simple, and
   clear. If you must read a sentence two times, write the sentence again.

---

## 3. What lives in a project

After `init`, a project has one `pdlc/` folder:

```
pdlc/
  config.md             which adapter fills each port, plus board column names
  ports/                the port contracts (see section 8)
  adapters/             the adapters this project uses
  inbox/                one file per intent
  specs/
    jobs/               one file per job to be done
    capabilities/       one file per capability
    design/             one file per convention, including pdlc's own defaults
  changes/              one change spec per milestone
```

All the files are in markdown. Git keeps the history of the files, together with the code
that the files are about.

---

## 4. IDs and statuses

### IDs

Each item has a short, stable ID. After an item gets its ID, the ID does not change.

| Thing | ID | Example |
|---|---|---|
| Intent | `IN-####` | `IN-0012` |
| Job spec | `JOB-<name>` | `JOB-reset-password` |
| Capability spec | `CAP-<name>` | `CAP-email` |
| Design spec | `DES-<name>` | `DES-forms` |
| Requirement | `<spec>.R<n>` | `CAP-email.R3` |
| Change | `CH-####` | `CH-0031` |

### Intent status

```
new ──► specifying ──► ready ──► building ──► in review ──► done
                                     │
                            paused / cancelled (any time)
```

- **new**: the intent is in the inbox, and nobody examined the intent yet.
- **specifying**: pdlc writes spec patches and asks you questions.
- **ready**: each requirement that the intent touches is `ready`. Changes can start.
- **building**: the build of at least one change of the intent is in progress.
- **in review**: all the changes of the intent are built, and they wait for review or for
  your approval.
- **done**: all the changes of the intent are merged.

### Requirement status

```
proposed ──► ready ──► built ──► verified
```

- **proposed**: intake wrote the requirement into the spec. Nobody examined the
  requirement yet.
- **ready**: the requirement is clear, testable, and consistent with the other specs.
- **built**: the change and its checks exist on a branch.
- **verified**: the checks of the requirement pass, and the review passed. Only now can
  the change merge.

Spec patches go into the real spec file immediately, with the status `proposed`. There is
one source of truth. If two intents touch the same requirement, the two intents collide at
spec time, not at merge time. At spec time, the collision is cheap to correct.

To remove a requirement, a patch marks the requirement `retiring`. When the change that
removes the code merges, the requirement is deleted from the spec. Git keeps the history.

When recon finds requirements in existing code, these requirements start as `built`, with
`Source: recon`. Such a requirement becomes `verified` when a change adds checks that
prove the requirement.

---

## 5. The documents

`init` supplies a template for each document. The templates are short.

### Intent (`pdlc/inbox/IN-0012-password-reset.md`)

- What you want and why, in your own words.
- The status, and the link to the ticket.
- The requirements that the intent added or changed (the `intake` skill writes this
  list).
- The changes that deliver the intent, in order (the `change` skill writes this list).

### Job, capability and design specs

- A short summary of the purpose of the spec.
- **Code map**: the files and folders that this spec owns. pdlc uses the code map to set
  the scope of changes, not to trace.
- **Requirements**. Each requirement has an ID, a status, the intents that shaped it, and
  acceptance checks. The acceptance checks are plain "given / when / then" lines.
- Job specs also list the capabilities and design specs that they rely on.

Example requirement:

```
### CAP-email.R3 · Send an email from a template
Status: ready · Intents: IN-0012
The system can send an email that it builds from a named template and a set of values.
- Given a template "reset" and the address of a user, when we send, then the system sends
  one email that contains the values.
- Given a missing template, when we send, then we get a clear error, and the system sends
  no email.
```

### Change spec (`pdlc/changes/CH-0031-email-templates/change.md`)

The change spec is the only document that the builder needs. The change spec is a
simplified form of the `.plan.md` format that `/quiz-plan` uses.

- **Delivers**: the intent, and the one job or capability that this change covers.
- **Requirements**: the IDs of the requirements that the change will build, with a copy
  of their acceptance checks.
- **Relies on**: the IDs of the other specs that the change uses. For a job change, this
  list includes the capabilities that the job calls. The list always includes the design
  specs that apply.
- **Interface**: the items that the checks are permitted to call. Thus, the test writer
  does not need the code.
- **Files**: only the app files that this change is permitted to touch. These files come
  from the code map.
- **Check files**: the checks. Only the test writer is permitted to change these files.
- **Tests-Locked**: the commit that locked the checks.
- **Steps**: small steps. Each step gives the requirement that it serves and the test that
  proves it.
- **Progress log**: a record of what happened. New entries go at the end, as the work
  continues.

---

## 6. Traceability

The trace works in the two directions, and pdlc writes each link only one time.

```
 ticket ◄──► intent ◄──► requirement ◄──► check ◄──► code
 PROJ-88     IN-0012     CAP-email.R3     check name  commit trailers
```

- **Intent → requirements**: the intent file lists the requirements. Each requirement
  lists its intents.
- **Requirement → checks**: each check carries the requirement ID in its name or in its
  tag, for example a test with the name `CAP-email.R3 sends from template`.
- **Code → requirement**: each commit carries trailers:

  ```
  Intent: IN-0012
  Change: CH-0031
  Req: CAP-email.R3
  Ticket: PROJ-88
  ```

  Thus, `git blame` on a line leads to the commit, then to the requirement, then to the
  intent, and then to the ticket. Jira and Linear read the `Ticket` key and show the
  commit on the card.
- **No ID comments in source code.** ID comments become incorrect when code moves, and
  nothing examines them.

The `trace` skill answers questions in the two directions, in plain words: "why does this
line exist?" and "what did IN-0012 change?"

---

## 7. Verification

### Who does what

| Who | Sees | Writes | Never |
|---|---|---|---|
| test writer | the spec, the interface, existing checks | checks | reads app code |
| builder | the spec, app code, the locked checks | app code | changes checks |
| reviewer (one per remit) | only its packet | its result | sees another packet or result |

A guard in the plugin enforces this table for each file tool, by agent. The builder needs
a shell to run checks. Thus, the merge check is the backstop: the merge check fails if a
check changed after the lock.

### Independent reviews

Each remit has one fresh reviewer. Each reviewer gets one packet, which `make_packets.py`
builds:

- **tests**: the spec and the checks, but not the code. This review runs immediately
  after the checks are locked, before the builder writes code.
- **specification, security, quality, compliance, privacy**: the spec and the code, but
  not the checks. These reviews run in parallel after the visual review. The
  specification reviewer also examines the frames of the GIF.

The project can edit each remit in `pdlc/reviews/`. In `config.md`, the project selects
which remits run.

### Visual review

`show` plays each acceptance line in the real app: in a browser for web apps, and in a
terminal for CLIs and libraries. Then `show` saves `review.gif` and its frames in the
change folder. The commit gives the name of the GIF, and the pull request embeds the GIF.

### The gate

A change can merge only when all of these conditions are true. `check_merge.py` confirms
the first three:

1. **Checks pass.** Each requirement in the change has at least one check tagged with its
   ID, and those checks pass. The checks are written before the change. A check is
   usually an automated test. But a check can be anything that proves the requirement
   (see section 14).
2. **Review passes.** A reviewer agent that did not write the code reads the change spec,
   the diff, and the design specs. The reviewer agent examines these items:
   - The diff stays inside the files of the change, and inside its one job or capability.
   - The change meets each acceptance check, and the checks really prove this.
   - The change follows the design specs.
   - Each commit has its trace trailers.
3. **You approve the merge.** You use your time for judgement, not for checklists.

If a requirement that the change touches is not `verified`, the delivery adapter blocks
the merge. A small check script does the same in CI. Thus, the rule also applies outside
pdlc.

If you cannot test an acceptance check automatically, the change spec marks that
acceptance check `manual check`. You confirm the manual check when you approve the merge.

You can run `/probe` as an extra exploratory pass. In v1, `/probe` is optional.

---

## 8. Ports and adapters

pdlc communicates with the outside world only through **ports**.

- A **port** is a job that the core needs. Each port has a short contract in plain prose:
  what goes in, what comes out, and what is a success.
- An **adapter** does the job of a port with one specific tool. An adapter is a short
  markdown file of instructions.
- The core skills call only ports. The core skills do not refer to GitHub, pytest, or
  Linear.
- `config.md` gives the adapter for each port. To use a different tool, you change one
  line.

```
 pdlc skills ──► port contract ──► adapter ──► real tool
```

### v1 ports

| Port | Job | Default adapter | Later |
|---|---|---|---|
| inbox | list, read, and add intents, and set their status | markdown files in `pdlc/inbox/` | GitHub Issues, Linear, Jira |
| checks | run checks, and report pass or fail for each requirement ID | a command that recon finds in the repo | per-stack adapters, `claude plugin eval` |
| review | examine a diff independently against its change spec | the `reviewer` agent | `/code-review`, `/security-review` |
| delivery | branch, commit, open a PR, and block the merge until verified | git and GitHub PRs | local git only |
| tracker | show the state of pdlc on a board | none (pdlc supplies `tracker-github-projects` and `tracker-linear`) | Jira |
| explore | examine the running app for surprises (optional) | `/probe` | none planned |

**Not ports:** the spec files, the IDs, and the statuses. Traceability needs these items
to be the same in each project. Thus, these items are part of the core.

### How pdlc extends itself

A new adapter is only one more intent, for example "add a Linear tracker adapter". The
spec of the adapter is a capability spec. Then pdlc builds the adapter against the port
contract, and verifies the adapter as it verifies each other change. Each port contract
has a short conformance check. Thus, pdlc tests each adapter in the same way.

---

## 9. The tracker (boards like Jira and Linear)

pdlc has priority over the board. The board shows the state of pdlc, but the board does
not own that state.

### v1: projection out

- Each intent gets a card. Each change gets a sub-card.
- When an intent or a change goes to a different stage, pdlc moves its card to the
  matching column. `config.md` maps each pdlc stage to the name of a column on your board.
- The card links to the intent file and the PR. The intent file stores the card key.
- At its end, each core skill tells the tracker port about each status that the skill
  changed. If no tracker adapter is set, this step does nothing.
- The `board` skill re-syncs all intents and changes, in case a card drifted.

### Later: commands in

We design this part now, and we build this part later.

- When you move a card to *Start*, the move asks pdlc to start that change. When you move
  a card to *Paused* or *Cancelled*, the move asks pdlc to stop.
- A new card in the intake column becomes an inbox intent.
- Board moves are **requests**, not facts. pdlc examines each request. If a card goes to
  *Start* but its spec is not ready, pdlc moves the card back. Then pdlc writes a comment
  that gives the reason.
- Nobody can move a card to *Done* from the board. Only verification and your approval can
  move a card to *Done*.
- pdlc uses the text of a card as input to intake. pdlc does not use card text as
  instructions to the agent.
- A scheduled routine examines the board every few minutes. A webhook adapter can come in
  a later version.

---

## 10. Conventions

pdlc always tries to keep the software consistent. To do this, pdlc writes conventions as
design specs, and agrees these design specs with you.

- **A new convention.** A change can need a convention that does not exist yet, for
  example the first time that we build a table. Then pdlc stops and asks you with a short
  quiz. The answer becomes a design spec.
- **Two patterns.** When recon finds two patterns for the same thing, recon asks you
  which pattern wins.
- **A changed convention.** You can change a convention at any time with the
  `conventions` skill. You and pdlc agree the change, and pdlc writes the change to the
  design spec. Then pdlc creates one migration intent for each affected job or
  capability. You select when each migration intent runs.
- **Defaults.** pdlc supplies its own defaults: ID formats, test tagging, commit trailers,
  the review checklist, board columns, and the writing style. At `init`, pdlc shows each
  default as a quiz card, with the default marked as recommended. Thus, `skip` accepts the
  default. pdlc writes your answers into the project as ordinary design specs, marked as
  defaults. After that, you change these design specs as you change all other
  conventions.

---

## 11. Existing software

In an existing codebase, `init` runs **recon** before all other steps. Recon is careful
and read-only. Recon tries to find "just enough", and does not make a full survey.

1. **Thin map of everything.** Recon lists these items:
   - The likely capabilities, from modules, services, and dependencies.
   - The likely jobs, from routes, screens, and commands.
   - The test and build commands.
   - The conventions that recon can see, for example lint configs and repeated patterns.

   Each item becomes a stub spec, with a code map and no requirements yet.
2. **You confirm the map.** pdlc shows the list. pdlc asks you to merge, split, or rename
   each item that looks wrong. The boundaries of capabilities and jobs are important,
   because each change must stay inside one capability or one job.
3. **Deep only when needed.** When an intent touches a stub spec, intake sends recon to
   that area. Recon writes the current requirements of that area, marked
   `Source: recon`. The other areas stay thin.

---

## 12. Skills and agents

pdlc is a Claude Code plugin. You call its skills as `/pdlc:<name>`.

### Skills

| Skill | What it does |
|---|---|
| `init` | Prepares pdlc in a project: folders, templates, recon, default conventions, and adapters. |
| `intake` | Takes an intent from the inbox, and writes spec patches with `proposed` requirements. |
| `ready` | Asks you about each unclear item (like `/quiz`). Looks for contradictions (like `/argue`). Then marks the requirements `ready`. |
| `change` | Divides a ready intent into milestones, with one job or capability in each milestone. Writes a change spec for each milestone. |
| `tests` | Tells the test writer to write the checks from the spec. Makes sure that the checks fail. Locks the checks, and gets a review of the checks. |
| `build` | Tells the builder to write app code until the locked checks pass. Marks the requirements `built`. |
| `show` | Records the change as it works, as `review.gif` and frames. |
| `verify` | Runs all the checks and the independent code reviews. Marks the requirements `verified`, and proposes the merge. |
| `ship` | Runs all the stages from start to end with the recommended answers, and stacks the changes. Continues from the point where it stopped. |
| `conventions` | Establishes or changes a convention with you, and creates migration intents. |
| `board` | Re-syncs each intent and each change to the tracker. |
| `trace` | Answers "why does this code exist?" and "what did this intent change?" |
| `dashboard` | Optional. After it asks you, installs a `dashboard-builder` agent and a CLAUDE.md rule for a live status page. |

`ready`, `build`, and `verify` are simplified versions of `/quiz` and `/argue`,
`/quiz-plan-execute`, and `/probe`, in that order. These three skills keep the ideas, and
remove all the parts that pdlc does not need.

### Agents

| Agent | What it does |
|---|---|
| `recon` | Read-only scout. Maps a codebase, or one area of a codebase, into draft specs. |
| `test-writer` | Writes checks from the spec only. Does not read app code. |
| `builder` | Writes app code until the locked checks pass. Does not change checks. |
| `reviewer` | Judges one packet for one remit. Sees nothing else. |

---

## 13. A walk through

You put "let users reset their password" into the inbox as `IN-0012`.

1. **intake** sees that this intent needs a new job, `JOB-reset-password`, and a new
   requirement on `CAP-email` to send from templates. Then **intake** writes the two
   items as `proposed`.
2. **ready** asks you how long a reset link stays valid. **ready** also makes sure that
   the new requirements do not contradict `CAP-auth`. Then **ready** marks the new
   requirements `ready`.
3. **change** writes two milestones. `CH-0031` adds templates to `CAP-email`. `CH-0032`
   builds `JOB-reset-password`, and uses email but does not edit email.
4. **build** completes `CH-0031` (email templates), test first. Each commit carries its
   trailers.
5. **verify** runs the checks and the reviewer. The checks and the review pass. Thus,
   `CAP-email.R3` (send from a template) is `verified`, and a PR opens. You approve the
   PR, and the PR merges.
6. The same steps occur for `CH-0032` (the password reset job). When that change merges,
   `IN-0012` (the password reset intent) is `done`, and the card on your board moves to
   Done.

---

## 14. Any system

pdlc assumes only two things: the project is in git, and you work in Claude Code. Recon
learns all the other items, or you connect them through a port.

These words apply to all types of system:

- A **user** is anyone that the system serves, for example these persons:
  - A person who clicks on a screen.
  - A developer who calls an API.
  - An operator who runs a command.
  - A person who types a slash command in Claude Code.
- A **job** is what that user tries to do.
- A **capability** is something that the system can do, and that jobs rely on.
- A **check** is anything that proves a requirement and gives a pass or a fail. A check
  is usually an automated test. A check can also be a script, a lint rule, an eval run, or
  a query against real infrastructure. If you really cannot automate a check, the check
  is a `manual check` item (section 7).

| System | A job | A capability | A check |
|---|---|---|---|
| Web app | "pay an invoice" | payments, email | end-to-end test |
| Library or API | "parse a config file" | tokenizer, error reporting | unit test |
| Infrastructure | "deploy a new service" | networking, secrets | plan check, policy test |
| Skill collection (this repo) | "clarify a task before starting" | question cards, plan format | `claude plugin eval`, frontmatter check |

Recon learns which of these items a project has. The checks port runs the type of check
that the project uses. If a project cannot run checks yet, the first intent that `init`
suggests is to add a way to run checks.

## 15. pdlc on itself

pdlc can manage changes to this repository, `pskills`. These changes include changes to
pdlc.

- **Two folders, two jobs.** `plugins/pdlc/` is the source of the plugin. `pdlc/` at the
  root of the repo is the state of pdlc for this repo: its inbox, specs, and change specs.
  The two folders are always separate.
- **The installed version does the work.** The pdlc that you installed from the
  marketplace always builds the changes. The working copy that a change edits does not
  build changes. A new version starts to work only after it merges and you update the
  plugin. This rule prevents a half-built change from running itself.
- **This repo's specs.** Each skill is a job, for example `JOB-clarify-task` for `/quiz`
  or `JOB-run-lifecycle` for pdlc. Shared parts are capabilities, for example
  `CAP-question-cards` or `CAP-plan-format`. The writing style is a design spec.
- **This repo's checks.** Frontmatter and JSON must parse. `claude plugin validate` must
  pass. Each skill gets evals that `claude plugin eval` can run. If no eval exists
  yet, the check is a `manual check`.
- **pdlc manages changes to pdlc.** A change to pdlc is an intent like all other
  intents. For example, "add a Linear tracker adapter" becomes a capability change to
  pdlc. The installed pdlc builds and verifies that change.

## 16. Open questions

- Do we ship the CI check script in v1? Or is the check of the delivery adapter
  sufficient at the start?
- How much of pskills does `init` map at first: each skill, or only the skills that the
  first intent touches?
