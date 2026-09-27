# Change Plan: build pdlc v1

**Owner:** `Patrick Te Tau` · **Status:** Draft
**Branch:** `claude/zen-brown-ww7xi3` · **Plan location:** `plans/build-pdlc-v1.plan.md`
**Progress:** ░░░░░░░░░░░░ 0/12 steps completed (0%)

## How to use this document (read this first, every session)

You are an agent executing this plan. Assume you have no memory of previous sessions.

1. Read Intent, Ground truth, and Boundaries in full (plus Approach).
2. Read the Progress log to find the current state. Do not redo completed steps or reopen decisions recorded there.
3. Resume at the first step not marked done. Respect its gate. If it carries a `Parallel group` tag shared with other not-done steps, those run together — see [[quiz-plan-execute]].
4. After each step: append to the Progress log, then self-assess against the step's done criteria before moving on.
5. If anything you're about to do conflicts with Intent or Boundaries, stop and ask. Do not resolve the conflict yourself.

## Intent

Build v1 of **pdlc**, the development lifecycle harness described in `pdlc/OUTLINE.md`.
Today the skeleton skills and agents in `pdlc/` only describe what they will do. When this
plan is done, pdlc installs as a Claude Code plugin, and one intent can travel from the
inbox to a verified PR in a small test project, with every commit traceable to its
requirement and intent.

**Not doing:** inbound tracker commands (board moves that start work). Adapters beyond the
v1 defaults and one tracker adapter. The optional `explore` port. Any change to the existing
skills in this repo (`quiz`, `squiz`, `argue`, `probe`, `quiz-plan`, `quiz-plan-execute`).

## Approach

**Chosen:** a Claude Code plugin in `pdlc/`. Skills read and write plain markdown files in
the target project's `pdlc/` folder. Templates, port contracts, default adapters and default
design specs ship inside the `init` skill's `references/` folder, and `init` copies them into
the project.

**Considered:** loose skills copied into `~/.claude/skills` like the rest of this repo.
Rejected because pdlc also ships agents, and a plugin installs both and gives the
`/pdlc:` prefix for free. Forking the existing skills was rejected; pdlc writes simplified
versions that borrow their ideas.

## Ground truth

- **Design:** `pdlc/OUTLINE.md`. It wins over this plan if they disagree; stop and ask.
- **Key files:**
  - `pdlc/.claude-plugin/plugin.json`
  - `pdlc/skills/<name>/SKILL.md` for init, intake, ready, change, build, verify,
    conventions, board, trace
  - `pdlc/agents/recon.md`, `pdlc/agents/reviewer.md`
  - `pdlc/skills/init/references/` (to create): templates, ports, adapters, defaults
- **Borrow ideas from:** `quiz/SKILL.md` (question cards), `argue/SKILL.md` (contradiction
  check), `quiz-plan-execute/SKILL.md` (test-first steps and commits), `probe/SKILL.md`.
- **Build / test / lint:** none for the markdown. Frontmatter must parse as YAML and
  `plugin.json` as JSON. The merge-check script (step 8) has its own tests.
- **Conventions:** every file is short, plain prose. Short sentences. No jargon. A skill
  should fit on one or two screens. If a sentence needs rereading, rewrite it.

**Verification rule:** before relying on any Claude Code plugin, skill or agent feature
(file layout, frontmatter fields, how skills call agents, how plugins install), read the
current Claude Code docs. Never write it from memory. If you can't find it, stop and ask.

## Boundaries

- **May modify:** `pdlc/**`, `plans/build-pdlc-v1.plan.md`, `README.md` (pdlc section only),
  and a throwaway test project under the scratchpad.
- **Must not touch:** the other skills in this repo, `build-probe-skill.plan.md`.
- **Stop and ask when:** the outline and this plan disagree, a plugin feature doesn't work as
  the outline assumes, a step's instructions are ambiguous, or the same fix has failed twice.
- **Assumptions (re-check every step):**
  - A plugin can ship both skills and agents, and a skill can hand work to a plugin agent.
  - Plain markdown files are enough state. No database, no server.
  - A test runner can select tests by a requirement ID in the test name.

**Riskiest assumption:** that pdlc works as a plugin: it installs from this repo, its skills
show up as `/pdlc:<name>`, and a skill can dispatch the `recon` agent. Tested in step 1.

## Steps

Gate meanings: **AUTO** means complete and continue. **GATED** means complete, log, then
stop and wait for human review.

### Step 1: Prove the plugin loads · `[ ]` AUTO · Parallel group: none

- **Do:** Read the current Claude Code plugin docs. Fix `pdlc/.claude-plugin/plugin.json` and
  the folder layout to match. Add whatever is needed to install the plugin from this repo
  (for example a marketplace file). Install it into a throwaway project. Run `/pdlc:init`
  (still a skeleton) and have it dispatch the `recon` agent with a trivial task.
- **Done when:** the nine skills are listed as `/pdlc:<name>`, both agents are available,
  and the init skeleton gets a reply from `recon`.
- **Out of scope here:** any real skill behaviour.
- **Touches:** `pdlc/.claude-plugin/**`, repo-root marketplace file if needed
- **Depends on:** none

### Step 2: Templates and port contracts · `[ ]` AUTO · Parallel group: none

- **Do:** In `pdlc/skills/init/references/`, write:
  - `templates/`: intent, job spec, capability spec, design spec, change spec, `config.md`.
  - `ports/`: one contract each for inbox, tests, review, delivery, tracker. Each says what
    goes in, what comes out, what success looks like, and a short conformance check.
  - `adapters/`: `inbox-files`, `tests-command`, `review-agent`, `delivery-github`.
  Match the IDs, statuses and sections in the outline exactly.
- **Done when:** every document type and port in the outline has a file; each template is
  under a screen; each adapter passes its port's conformance check on paper.
- **Out of scope here:** the tracker adapter (step 11).
- **Touches:** `pdlc/skills/init/references/{templates,ports,adapters}/**`
- **Depends on:** Step 1

### Step 3: Default design specs · `[ ]` AUTO · Parallel group: none

- **Do:** Write pdlc's defaults as design specs in `pdlc/skills/init/references/defaults/`:
  ID formats, test tagging, commit trailers, review checklist, board columns, writing style.
  Each has a one-line question and a recommended answer, so `init` can quiz on it.
- **Done when:** each default in outline section 10 has a file that works both as a quiz
  card and as a design spec.
- **Out of scope here:** the quiz itself (step 4).
- **Touches:** `pdlc/skills/init/references/defaults/**`
- **Depends on:** Step 2

### Step 4: `init` and `recon` · `[ ]` AUTO · Parallel group: none

- **Do:** Write `init` and the `recon` agent in full, following the outline. Init copies the
  references, runs recon's thin map on existing code, lets the user adjust the map, quizzes
  the defaults, and picks adapters.
- **Done when:** running `/pdlc:init` on a small existing repo in the scratchpad produces a
  complete `pdlc/` folder with stub specs, confirmed defaults and a filled `config.md`.
- **Out of scope here:** recon's deep look (used from step 5).
- **Touches:** `pdlc/skills/init/SKILL.md`, `pdlc/agents/recon.md`
- **Depends on:** Step 3

### Step 5: `intake` and `ready` · `[ ]` AUTO · Parallel group: none

- **Do:** Write both skills in full. Intake writes `proposed` patches and calls recon's deep
  look for stub specs. Ready asks questions one at a time and checks for contradictions,
  borrowing the simplest parts of `/quiz` and `/argue`.
- **Done when:** a test intent that needs a new job and a capability change ends up with
  `ready` requirements in both specs, and the intent is `ready`.
- **Out of scope here:** writing change specs.
- **Touches:** `pdlc/skills/intake/SKILL.md`, `pdlc/skills/ready/SKILL.md`
- **Depends on:** Step 4

### Step 6: `change` · `[ ]` AUTO · Parallel group: none

- **Do:** Write the skill in full. It splits a ready intent into milestones, one job or
  capability each, capabilities before jobs, and writes a change spec per milestone.
- **Done when:** the step 5 intent produces two change specs in the right order, and the job
  change edits no capability files.
- **Out of scope here:** building them.
- **Touches:** `pdlc/skills/change/SKILL.md`
- **Depends on:** Step 5

### Step 7: `build` · `[ ]` AUTO · Parallel group: none

- **Do:** Write the skill in full, borrowing the test-first loop from `/quiz-plan-execute`
  but dropping worktrees, parallel groups and anything else pdlc doesn't need.
- **Done when:** building the first change spec from step 6 gives one commit per step, each
  with trace trailers, tests named with requirement IDs, and requirements marked `built`.
- **Out of scope here:** verification.
- **Touches:** `pdlc/skills/build/SKILL.md`
- **Depends on:** Step 6

### Step 8: `verify`, `reviewer` and the merge check · `[ ]` AUTO · Parallel group: none

- **Do:** Write `verify` and the `reviewer` agent in full. Write a small merge-check script
  that fails if any requirement a change touches is not `verified`, with its own tests.
- **Done when:** verifying the step 7 change marks its requirements `verified` and opens a
  PR; a deliberately out-of-scope edit makes the reviewer fail it; the merge check fails on
  an unverified requirement and passes once verified.
- **Out of scope here:** CI wiring beyond documenting how to run the check.
- **Touches:** `pdlc/skills/verify/SKILL.md`, `pdlc/agents/reviewer.md`, the script and its tests
- **Depends on:** Step 7

### Step 9: `conventions` · `[ ]` AUTO · Parallel group: P1

- **Do:** Write the skill in full: agree a convention with the user, write the design spec,
  file one migration intent per affected job or capability.
- **Done when:** changing a default convention in the test project writes the design spec
  and files the right migration intents without starting them.
- **Out of scope here:** running the migrations.
- **Touches:** `pdlc/skills/conventions/SKILL.md`
- **Depends on:** Step 4

### Step 10: `trace` · `[ ]` AUTO · Parallel group: P1

- **Do:** Write the skill in full, for all three directions in the outline.
- **Done when:** in the test project, tracing a built line leads to its requirement, intent
  and ticket, and tracing the intent lists its requirements, commits and tests.
- **Out of scope here:** any UI beyond plain text answers.
- **Touches:** `pdlc/skills/trace/SKILL.md`
- **Depends on:** Step 8

### Step 11: Tracker port and `board` · `[ ]` GATED · Parallel group: none

- **Do:** Ask the user which board comes first (Linear, Jira or GitHub Projects). Write that
  adapter and the `board` skill, outbound only. Make every core skill tell the tracker port
  when it changes a status.
- **Done when:** the test project's intent and changes appear as a card and sub-cards in the
  right columns, and move when their status changes.
- **Out of scope here:** acting on board moves.
- **Touches:** `pdlc/skills/board/SKILL.md`, `pdlc/skills/init/references/adapters/tracker-*`,
  the "tell the tracker" line in each core skill
- **Depends on:** Step 8

### Step 12: End-to-end run and README · `[ ]` AUTO · Parallel group: none

- **Do:** In a fresh scratch project, run one new intent from inbox to merged PR using only
  pdlc skills. Fix anything that breaks. Re-read every pdlc file for plain prose. Add a short
  pdlc section to `README.md`. Check all frontmatter and JSON parse.
- **Done when:** the run completes with no manual file edits, the trace holds from ticket to
  code, and the README explains how to install and start.
- **Out of scope here:** new features found during the run; add them to the outline's open
  questions instead.
- **Touches:** `README.md`, any `pdlc/**` file the run shows is broken
- **Depends on:** Steps 9, 10, 11

## Verification and rollback

- **Human verifies by:** reading `pdlc/OUTLINE.md` and each finished skill, then watching or
  repeating the step 12 run.
- **Failing looks like:** a skill that needs manual file edits to move on; a change that
  crosses two jobs or capabilities; a commit without trailers; a merge allowed with an
  unverified requirement; prose that needs rereading.
- **Rollback:** everything lives in `pdlc/`, `plans/` and one README section. `git revert`
  the commits. Uninstall the plugin from the test project.
- **Kill criteria:** if step 1 shows skills and agents can't ship together as a plugin, stop
  and rethink packaging with the user before writing any skill.

## Progress log

One entry per step, appended at execution time (not written ahead). Newest last.

```
[2026-09-27] Step 0 (plan): done
Changed: pdlc/OUTLINE.md, pdlc skeleton skills and agents, this plan
Decided: from the quiz rounds — jobs use capabilities but never edit them; spec patches land
         at spec time with statuses proposed → ready → built → verified; verified before
         merge; init sets itself up and extends through ports; conventions change via
         migration intents; compose simplified versions of existing skills; markdown inbox;
         trace by commit trailers and test IDs; tests + independent reviewer, then human
         approval; defaults as design specs confirmed by quiz at init; name pdlc; tracker is
         pdlc-wins, outbound projection first.
Surprises: none yet.
```
