# pdlc: outline

pdlc is a development lifecycle harness for AI-driven work. It is a set of skills and agents
that you drop into any project, new or old, whatever kind of system it is. It turns ideas
into specs, specs into small changes, and changes into verified code. Every line of code can be traced back to the spec
it serves and the intent that asked for it.

This outline is the design. It is written before anything is built, so expect to change it.

---

## 1. The big idea

All work enters through an **inbox**. Each item in the inbox is an **intent**: something
you want to be true that isn't yet.

An intent never goes straight to code. First it becomes a change to the **specs**. There are
three kinds of spec:

- **Job specs** describe what a user is trying to get done. One file per job, for example
  "reset my password" or "pay an invoice".
- **Capability specs** describe what the system can do, independent of any one job. One file
  per capability, for example "email" or "persistence".
- **Design specs** describe how we do things everywhere. These are conventions: how we
  present a list, how we name files, how we write errors, how we test.

Once the specs are clear enough to build from, pdlc writes a **change spec**. A change spec
covers exactly one job or one capability. It lists the requirements it will deliver, the
other specs it relies on, and the files it needs to touch. Nothing else.

The change is built test first, reviewed by an agent that did not write it, and approved by
you. Only then can it merge.

```
 intent ──► spec patches ──► ready check ──► change spec(s) ──► build ──► verify ──► merge
 (inbox)    (job/cap/design)  (quiz, argue)   (one job or cap)   (TDD)    (checks,    (you
                                                                           reviewer)   approve)
```

---

## 2. Core rules

These rules are fixed. Everything else is a default you can change.

1. **All work enters through the inbox.** That includes convention migrations and new
   adapters for pdlc itself.
2. **Specs come before code.** An intent must be specified before any change is written.
3. **One change, one thing.** A change covers exactly one job or one capability, or one
   design spec.
4. **Jobs use capabilities; they never edit them.** If a job needs something a capability
   can't do yet, that becomes its own earlier milestone. Capability milestones always come
   before the job milestone that needs them.
5. **Verified before merge.** Every requirement a change touches must be `verified` before
   the change can merge to main.
6. **pdlc files are the truth.** Boards and trackers show pdlc's state. They don't own it.
7. **Everything is traceable.** Code links to requirements, requirements link to intents,
   intents link to tickets.
8. **Plain prose everywhere.** Every skill, agent, prompt and spec is short, simple and
   clear. If a sentence needs rereading, rewrite it.

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

Everything is markdown. Everything is versioned in git with the code it describes.

---

## 4. IDs and statuses

### IDs

Every item has a short, stable ID. IDs never change once given.

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

- **new**: in the inbox, not looked at yet.
- **specifying**: pdlc is writing spec patches and asking you questions.
- **ready**: every requirement it touches is `ready`. Changes can start.
- **building**: at least one of its changes is being built.
- **in review**: all its changes are built and waiting for review or your approval.
- **done**: all its changes have merged.

### Requirement status

```
proposed ──► ready ──► built ──► verified
```

- **proposed**: written into the spec by intake, not yet checked.
- **ready**: clear, testable and consistent with the rest of the specs.
- **built**: the change and its checks exist on a branch.
- **verified**: its checks pass and review passed. Only now can the change merge.

Spec patches land in the real spec file straight away, with status `proposed`. There is one
source of truth. If two intents touch the same requirement, they collide at spec time, when
it is cheap to sort out, not at merge time.

To remove a requirement, a patch marks it `retiring`. It is deleted from the spec when the
change that removes the code merges. Git keeps the history.

Requirements found by recon in existing code start as `built` with `Source: recon`. They
become `verified` once a change adds checks that prove them.

---

## 5. The documents

Each document has a template shipped with `init`. The templates are short.

### Intent (`pdlc/inbox/IN-0012-password-reset.md`)

- What you want and why, in your own words.
- Status and ticket link.
- Which requirements it added or changed (filled in by intake).
- Which changes deliver it, in order (filled in by change).

### Job, capability and design specs

- A short summary of what this is for.
- **Code map**: the files and folders this spec owns. Used to scope changes, not to trace.
- **Requirements**, each with an ID, a status, the intents that shaped it, and acceptance
  checks written as plain "given / when / then" lines.
- Job specs also list the capabilities and design specs they rely on.

Example requirement:

```
### CAP-email.R3 · Send an email from a template
Status: ready · Intents: IN-0012
The system can send an email built from a named template and a set of values.
- Given a template "reset" and a user's address, when we send, then one email goes out
  with the values filled in.
- Given a missing template, when we send, then we get a clear error and nothing is sent.
```

### Change spec (`pdlc/changes/CH-0031-email-templates.md`)

The change spec is the only thing the builder needs to read. It is a simplified form of the
`.plan.md` format used by `/quiz-plan`.

- **Delivers**: the intent, and the one job or capability this change covers.
- **Requirements**: the requirement IDs it will build, with their acceptance checks copied in.
- **Relies on**: the other specs it uses, by ID. For a job change, the capabilities it calls.
  Always the design specs that apply.
- **Files**: only the files this change may touch, drawn from the code map.
- **Steps**: small steps, each naming the requirement it serves and the test that proves it.
- **Progress log**: what happened, appended as work goes.

---

## 6. Traceability

The trace runs both ways, and each link is written down once.

```
 ticket ◄──► intent ◄──► requirement ◄──► check ◄──► code
 PROJ-88     IN-0012     CAP-email.R3     check name  commit trailers
```

- **Intent → requirements**: the intent file lists them. Each requirement lists its intents.
- **Requirement → checks**: every check carries the requirement ID in its name or tag, for
  example a test called `CAP-email.R3 sends from template`.
- **Code → requirement**: every commit carries trailers:

  ```
  Intent: IN-0012
  Change: CH-0031
  Req: CAP-email.R3
  Ticket: PROJ-88
  ```

  So `git blame` on any line leads to the commit, then the requirement, then the intent,
  then the ticket. Jira and Linear pick up the `Ticket` key and show the commit on the card.
- **No ID comments in source code.** They rot as code moves, and nothing checks them.

The `trace` skill answers both directions in plain words: "why does this line exist?" and
"what did IN-0012 change?"

---

## 7. Verification

A requirement becomes `verified` only when all of these are true:

1. **Checks pass.** Each requirement in the change has at least one check tagged with its
   ID, and those checks pass. Checks are written before the change. A check is usually an
   automated test, but can be anything that proves the requirement (see section 14).
2. **Review passes.** A reviewer agent that did not write the code reads the change spec, the
   diff and the design specs. It checks:
   - the diff stays inside the change's files and its one job or capability;
   - each acceptance check is met, and the checks really prove it;
   - the design specs are followed;
   - every commit has its trace trailers.
3. **You approve the merge.** Your time goes on judgment, not checklists.

The delivery adapter blocks the merge if any requirement the change touches is not
`verified`. A small check script does the same in CI, so the rule holds even outside pdlc.

If an acceptance check can't be tested automatically, the change spec marks it
`manual check`. You confirm it when you approve the merge.

`/probe` can be run as an extra exploratory pass. It is optional in v1.

---

## 8. Ports and adapters

pdlc talks to the outside world only through **ports**.

- A **port** is a job the core needs done. Each port has a short contract in plain prose:
  what goes in, what comes out, and what counts as success.
- An **adapter** does that job with one particular tool. It is a short markdown file of
  instructions.
- The core skills only ever call ports. They never mention GitHub, pytest or Linear.
- `config.md` names the adapter for each port. Swapping tools means changing one line.

```
 pdlc skills ──► port contract ──► adapter ──► real tool
```

### v1 ports

| Port | Job | Default adapter | Later |
|---|---|---|---|
| inbox | list, read and add intents; set their status | markdown files in `pdlc/inbox/` | GitHub Issues, Linear, Jira |
| checks | run checks; report pass or fail per requirement ID | a command recon finds in the repo | per-stack adapters, `claude plugin eval` |
| review | independently check a diff against its change spec | the `reviewer` agent | `/code-review`, `/security-review` |
| delivery | branch, commit, open a PR, block merge until verified | git and GitHub PRs | local git only |
| tracker | show pdlc's state on a board | none; ships `tracker-github-projects` and `tracker-linear` | Jira |
| explore | poke at the running app for surprises (optional) | `/probe` | none planned |

**Not ports:** the spec files, IDs and statuses. Traceability depends on them being the same
in every project, so they are core.

### How pdlc extends itself

A new adapter is just another intent, for example "add a Linear tracker adapter". pdlc specs
it as a capability, builds it against the port contract, and verifies it like any other
change. Each port contract comes with a short conformance check, so every adapter is tested
the same way.

---

## 9. The tracker (boards like Jira and Linear)

pdlc wins. The board shows pdlc's state and never owns it.

### v1: projection out

- Each intent gets a card. Each change gets a sub-card.
- When an intent or change moves stage, pdlc moves its card to the matching column.
  `config.md` maps each pdlc stage to a column name on your board.
- The card links to the intent file and the PR. The intent file stores the card key.
- Each core skill ends by telling the tracker port about any status it changed. If no
  tracker adapter is set, this step does nothing.
- The `board` skill re-syncs everything, in case a card drifted.

### Later: commands in

Designed now, built later.

- Moving a card to *Start* asks pdlc to begin that change. Moving it to *Paused* or
  *Cancelled* asks pdlc to stop.
- A new card in the intake column becomes an inbox intent.
- Board moves are **requests**, not facts. pdlc checks each one. If a card is moved to
  *Start* but its spec isn't ready, pdlc moves it back and comments with the reason.
- Nobody can move a card to *Done* from the board. Only verification and your approval can.
- Card text is treated as input to intake, never as instructions to the agent.
- A scheduled routine checks the board every few minutes. A webhook adapter can come later.

---

## 10. Conventions

pdlc always tries to keep the software consistent. It does this by writing conventions down
as design specs and agreeing them with you.

- **Establishing.** When a change needs a convention that doesn't exist yet (for example, the
  first time we build a table), pdlc stops and asks you with a short quiz. The answer
  becomes a design spec.
- **Spotting.** When recon finds two patterns for the same thing, it asks you which one wins.
- **Changing.** You can change a convention at any time through the `conventions` skill.
  The change is agreed with you and written to the design spec. Then pdlc files one
  migration intent per affected job or capability. You choose when each one runs.
- **Defaults.** pdlc ships its own defaults (ID formats, test tagging, commit trailers,
  review checklist, board columns, writing style). At `init` it shows each one as a quiz
  card with the default marked recommended, so `skip` accepts it. Your answers are written
  into the project as ordinary design specs, marked as defaults. After that, you change
  them like any other convention.

---

## 11. Working with existing software

`init` runs **recon** before anything else in an existing codebase. Recon is careful and
read-only. It aims for "just enough", not a full survey.

1. **Thin map of everything.** Recon lists the likely capabilities (from modules, services
   and dependencies), the likely jobs (from routes, screens and commands), the test and build
   commands, and the conventions it can see (lint configs, repeated patterns). Each becomes a
   stub spec with a code map and no requirements yet.
2. **You confirm the map.** pdlc shows the list and asks you to merge, split or rename
   anything that looks wrong. The capability and job boundaries matter, because every change
   must stay inside one.
3. **Deep only when needed.** When an intent touches a stub spec, intake sends recon to that
   area to write out its current requirements, marked `Source: recon`. The rest stays thin.

---

## 12. Skills and agents

pdlc is a Claude Code plugin. Its skills are called as `/pdlc:<name>`.

### Skills

| Skill | What it does |
|---|---|
| `init` | Sets pdlc up in a project: folders, templates, recon, default conventions, adapters. |
| `intake` | Takes an intent from the inbox and writes spec patches with `proposed` requirements. |
| `ready` | Asks you about anything unclear (like `/quiz`), checks for contradictions (like `/argue`), then marks requirements `ready`. |
| `change` | Splits a ready intent into milestones, one job or capability each, and writes a change spec for each. |
| `build` | Builds one change spec, test first, one commit per step with trace trailers. Marks requirements `built`. |
| `verify` | Runs the checks port and the review port. Marks requirements `verified` and opens the PR. |
| `conventions` | Establishes or changes a convention with you, and files migration intents. |
| `board` | Re-syncs every intent and change to the tracker. |
| `trace` | Answers "why does this code exist?" and "what did this intent change?" |

`ready`, `build` and `verify` are simplified versions of `/quiz` and `/argue`,
`/quiz-plan-execute`, and `/probe`. They keep the ideas and drop everything pdlc doesn't need.

### Agents

| Agent | What it does |
|---|---|
| `recon` | Read-only scout. Maps a codebase, or one area of it, into draft specs. |
| `reviewer` | Independent reviewer. Checks a diff against its change spec and the design specs. Never sees how the code was written. |

---

## 13. A walk through

You drop "let users reset their password" into the inbox as `IN-0012`.

1. **intake** sees this needs a new job, `JOB-reset-password`, and a new requirement on
   `CAP-email` to send from templates. It writes both as `proposed`.
2. **ready** asks you how long a reset link should last. It checks the new requirements
   don't contradict `CAP-auth`. Both are marked `ready`.
3. **change** writes two milestones. `CH-0031` adds templates to `CAP-email`. `CH-0032`
   builds `JOB-reset-password`, using email without editing it.
4. **build** works through `CH-0031`, test first. Each commit carries its trailers.
5. **verify** runs the checks and the reviewer. Both pass, so `CAP-email.R3` is `verified`
   and a PR opens. You approve and it merges.
6. The same happens for `CH-0032`. When it merges, `IN-0012` is `done`, and the card on your
   board moves to Done.

---

## 14. Any system

pdlc assumes only two things: the project is in git, and you work in Claude Code. Everything
else is learned by recon or plugged in through a port.

The words stretch to fit:

- A **user** is whoever the system serves. A person clicking a screen, a developer calling an
  API, an operator running a command, or someone typing a slash command in Claude Code.
- A **job** is what that user is trying to get done.
- A **capability** is something the system can do that jobs rely on.
- A **check** is anything that proves a requirement and gives a pass or fail. Usually an
  automated test. It can also be a script, a lint rule, an eval run, or a query against real
  infrastructure. Checks that truly can't be automated are `manual check` items (section 7).

| System | A job | A capability | A check |
|---|---|---|---|
| Web app | "pay an invoice" | payments, email | end-to-end test |
| Library or API | "parse a config file" | tokenizer, error reporting | unit test |
| Infrastructure | "deploy a new service" | networking, secrets | plan check, policy test |
| Skill collection (this repo) | "clarify a task before starting" | question cards, plan format | `claude plugin eval`, frontmatter check |

Recon learns which of these a project has. The checks port runs whatever the project uses.
If a project has no way to run checks yet, the first intent `init` suggests is to add one.

## 15. pdlc on itself

pdlc can manage changes to this repository, `pskills`, including changes to pdlc.

- **Two folders, two jobs.** `plugins/pdlc/` is the plugin's source. `pdlc/` at the repo root
  is pdlc's state for this repo: its inbox, specs and change specs. They never mix.
- **The installed version does the work.** Changes are always built by the pdlc installed
  from the marketplace, never by the working copy being changed. A new version only takes
  effect after it merges and you update the plugin. This stops a half-built change from
  running itself.
- **This repo's specs.** Each skill is a job, for example `JOB-clarify-task` for `/quiz` or
  `JOB-run-lifecycle` for pdlc. Shared parts are capabilities, for example
  `CAP-question-cards` or `CAP-plan-format`. The writing style is a design spec.
- **This repo's checks.** Frontmatter and JSON must parse, `claude plugin validate` must
  pass, and each skill gets evals that `claude plugin eval` can run. Where no eval exists
  yet, the check is a `manual check`.
- **Changing pdlc through pdlc.** A change to pdlc is an intent like any other. For example,
  "add a Linear tracker adapter" becomes a capability change to pdlc, built and verified by
  the installed pdlc.

## 16. Open questions

- Should the CI check script ship in v1, or should the delivery adapter's check be enough to
  start with?
- How much of pskills should `init` map at first: every skill, or only the ones the first
  intent touches?
