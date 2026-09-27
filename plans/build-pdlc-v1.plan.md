# Change Plan: build pdlc v1

**Owner:** `Patrick Te Tau` · **Status:** Draft
**Branch:** `claude/zen-brown-ww7xi3` · **Plan location:** `plans/build-pdlc-v1.plan.md`
**Progress:** ██████████░░ 17/20 steps completed (85%)

## How to use this document (read this first, every session)

You are an agent executing this plan. Assume you have no memory of previous sessions.

1. Read Intent, Ground truth, and Boundaries in full (plus Approach).
2. Read the Progress log to find the current state. Do not redo completed steps or reopen decisions recorded there.
3. Resume at the first step not marked done. Respect its gate. If it carries a `Parallel group` tag shared with other not-done steps, those run together — see [[quiz-plan-execute]].
4. After each step: append to the Progress log, then self-assess against the step's done criteria before moving on.
5. If anything you're about to do conflicts with Intent or Boundaries, stop and ask. Do not resolve the conflict yourself.

## Intent

Build v1 of **pdlc**, the development lifecycle harness described in `plugins/pdlc/OUTLINE.md`.
Today the skeleton skills and agents in `plugins/pdlc/` only describe what they will do. When this
plan is done, pdlc installs as a Claude Code plugin, and one intent can travel from the
inbox to a verified PR in a small test project, with every commit traceable to its
requirement and intent. pdlc must fit any kind of system, and must be able to manage changes
to this repository, including changes to itself.

**Not doing:** inbound tracker commands (board moves that start work). Adapters beyond the
v1 defaults and one tracker adapter. The optional `explore` port. Any change to the existing
skills in this repo (`quiz`, `squiz`, `argue`, `probe`, `quiz-plan`, `quiz-plan-execute`).

## Approach

**Chosen:** a Claude Code plugin in `plugins/pdlc/`, listed in this repo's marketplace
(`.claude-plugin/marketplace.json`). Skills read and write plain markdown files in the
target project's `pdlc/` folder. The plugin lives under `plugins/` so it never collides with
the `pdlc/` state folder when pdlc manages this repo. Templates, port contracts, default adapters and default
design specs ship inside the `init` skill's `references/` folder, and `init` copies them into
the project.

**Considered:** loose skills copied into `~/.claude/skills` like the rest of this repo.
Rejected because pdlc also ships agents, and a plugin installs both and gives the
`/pdlc:` prefix for free. Forking the existing skills was rejected; pdlc writes simplified
versions that borrow their ideas.

## Ground truth

- **Design:** `plugins/pdlc/OUTLINE.md`. It wins over this plan if they disagree; stop and ask.
- **Key files:**
  - `.claude-plugin/marketplace.json` (repo root), `plugins/pdlc/.claude-plugin/plugin.json`
  - `plugins/pdlc/INSTALL.md`
  - `plugins/pdlc/skills/<name>/SKILL.md` for init, intake, ready, change, build, verify,
    conventions, board, trace
  - `plugins/pdlc/agents/recon.md`, `plugins/pdlc/agents/reviewer.md`
  - `plugins/pdlc/skills/init/references/` (to create): templates, ports, adapters, defaults
- **Borrow ideas from:** `quiz/SKILL.md` (question cards), `argue/SKILL.md` (contradiction
  check), `quiz-plan-execute/SKILL.md` (test-first steps and commits), `probe/SKILL.md`.
- **Build / test / lint:** `claude plugin validate .` and `claude plugin validate ./plugins/pdlc`
  must pass. Frontmatter must parse as YAML. The merge-check script (step 8) has its own tests.
  Try a local copy with `claude --plugin-dir ./plugins/pdlc`.
- **Conventions:** every file is short, plain prose. Short sentences. No jargon. A skill
  should fit on one or two screens. If a sentence needs rereading, rewrite it.

**Verification rule:** before relying on any Claude Code plugin, skill or agent feature
(file layout, frontmatter fields, how skills call agents, how plugins install), read the
current Claude Code docs. Never write it from memory. If you can't find it, stop and ask.

## Boundaries

- **May modify:** `plugins/pdlc/**`, `.claude-plugin/marketplace.json`,
  `plans/build-pdlc-v1.plan.md`, `README.md` (pdlc section only), a throwaway test project
  under the scratchpad, and (step 13 only) a new `pdlc/` state folder at the repo root.
- **Must not touch:** the other skills in this repo, `build-probe-skill.plan.md`.
- **Stop and ask when:** the outline and this plan disagree, a plugin feature doesn't work as
  the outline assumes, a step's instructions are ambiguous, or the same fix has failed twice.
- **Assumptions (re-check every step):**
  - A plugin can ship both skills and agents, and a skill can hand work to a plugin agent.
  - Plain markdown files are enough state. No database, no server.
  - A check runner can select checks by a requirement ID in the check name.
  - The words job, capability and check stretch to fit any kind of system (outline section 14).

**Riskiest assumption:** that pdlc works as a plugin: it installs from this repo, its skills
show up as `/pdlc:<name>`, and a skill can dispatch the `recon` agent. Tested in step 1.

## Steps

Gate meanings: **AUTO** means complete and continue. **GATED** means complete, log, then
stop and wait for human review.

### Step 1: Prove the plugin loads · `[x]` AUTO · Parallel group: none

- **Do:** Read the current Claude Code plugin docs. Fix `plugins/pdlc/.claude-plugin/plugin.json` and
  the folder layout to match. Add whatever is needed to install the plugin from this repo
  (for example a marketplace file). Install it into a throwaway project. Run `/pdlc:init`
  (still a skeleton) and have it dispatch the `recon` agent with a trivial task.
- **Done when:** the nine skills are listed as `/pdlc:<name>`, both agents are available,
  and the init skeleton gets a reply from `recon`.
- **Out of scope here:** any real skill behaviour.
- **Touches:** `plugins/pdlc/.claude-plugin/**`, repo-root marketplace file if needed
- **Depends on:** none

### Step 2: Templates and port contracts · `[x]` AUTO · Parallel group: none

- **Do:** In `plugins/pdlc/skills/init/references/`, write:
  - `templates/`: intent, job spec, capability spec, design spec, change spec, `config.md`.
  - `ports/`: one contract each for inbox, checks, review, delivery, tracker. Each says what
    goes in, what comes out, what success looks like, and a short conformance check.
  - `adapters/`: `inbox-files`, `checks-command`, `review-agent`, `delivery-github`.
  Match the IDs, statuses and sections in the outline exactly.
- **Done when:** every document type and port in the outline has a file; each template is
  under a screen; each adapter passes its port's conformance check on paper.
- **Out of scope here:** the tracker adapter (step 11).
- **Touches:** `plugins/pdlc/skills/init/references/{templates,ports,adapters}/**`
- **Depends on:** Step 1

### Step 3: Default design specs · `[x]` AUTO · Parallel group: none

- **Do:** Write pdlc's defaults as design specs in `plugins/pdlc/skills/init/references/defaults/`:
  ID formats, check tagging, commit trailers, review checklist, board columns, writing style.
  Each has a one-line question and a recommended answer, so `init` can quiz on it.
- **Done when:** each default in outline section 10 has a file that works both as a quiz
  card and as a design spec.
- **Out of scope here:** the quiz itself (step 4).
- **Touches:** `plugins/pdlc/skills/init/references/defaults/**`
- **Depends on:** Step 2

### Step 4: `init` and `recon` · `[x]` AUTO · Parallel group: none

- **Do:** Write `init` and the `recon` agent in full, following the outline. Init copies the
  references, runs recon's thin map on existing code of any kind, lets the user adjust the map, quizzes
  the defaults, and picks adapters.
- **Done when:** running `/pdlc:init` on two small scratch repos of different kinds (for
  example a web app and a CLI library) produces a complete `pdlc/` folder in each, with stub
  specs, confirmed defaults and a filled `config.md`.
- **Out of scope here:** recon's deep look (used from step 5).
- **Touches:** `plugins/pdlc/skills/init/SKILL.md`, `plugins/pdlc/agents/recon.md`
- **Depends on:** Step 3

### Step 5: `intake` and `ready` · `[x]` AUTO · Parallel group: none

- **Do:** Write both skills in full. Intake writes `proposed` patches and calls recon's deep
  look for stub specs. Ready asks questions one at a time and checks for contradictions,
  borrowing the simplest parts of `/quiz` and `/argue`.
- **Done when:** a test intent that needs a new job and a capability change ends up with
  `ready` requirements in both specs, and the intent is `ready`.
- **Out of scope here:** writing change specs.
- **Touches:** `plugins/pdlc/skills/intake/SKILL.md`, `plugins/pdlc/skills/ready/SKILL.md`
- **Depends on:** Step 4

### Step 6: `change` · `[x]` AUTO · Parallel group: none

- **Do:** Write the skill in full. It splits a ready intent into milestones, one job or
  capability each, capabilities before jobs, and writes a change spec per milestone.
- **Done when:** the step 5 intent produces two change specs in the right order, and the job
  change edits no capability files.
- **Out of scope here:** building them.
- **Touches:** `plugins/pdlc/skills/change/SKILL.md`
- **Depends on:** Step 5

### Step 7: `build` · `[x]` AUTO · Parallel group: none

- **Do:** Write the skill in full, borrowing the test-first loop from `/quiz-plan-execute`
  but dropping worktrees, parallel groups and anything else pdlc doesn't need.
- **Done when:** building the first change spec from step 6 gives one commit per step, each
  with trace trailers, checks named with requirement IDs, and requirements marked `built`.
- **Out of scope here:** verification.
- **Touches:** `plugins/pdlc/skills/build/SKILL.md`
- **Depends on:** Step 6

### Step 8: `verify`, `reviewer` and the merge check · `[x]` AUTO · Parallel group: none

- **Do:** Write `verify` and the `reviewer` agent in full. Write a small merge-check script
  that fails if any requirement a change touches is not `verified`, with its own tests.
- **Done when:** verifying the step 7 change marks its requirements `verified` and opens a
  PR; a deliberately out-of-scope edit makes the reviewer fail it; the merge check fails on
  an unverified requirement and passes once verified.
- **Out of scope here:** CI wiring beyond documenting how to run the check.
- **Touches:** `plugins/pdlc/skills/verify/SKILL.md`, `plugins/pdlc/agents/reviewer.md`, the script and its tests
- **Depends on:** Step 7

### Step 9: `conventions` · `[x]` AUTO · Parallel group: P1

- **Do:** Write the skill in full: agree a convention with the user, write the design spec,
  file one migration intent per affected job or capability.
- **Done when:** changing a default convention in the test project writes the design spec
  and files the right migration intents without starting them.
- **Out of scope here:** running the migrations.
- **Touches:** `plugins/pdlc/skills/conventions/SKILL.md`
- **Depends on:** Step 4

### Step 10: `trace` · `[x]` AUTO · Parallel group: P1

- **Do:** Write the skill in full, for all three directions in the outline.
- **Done when:** in the test project, tracing a built line leads to its requirement, intent
  and ticket, and tracing the intent lists its requirements, commits and checks.
- **Out of scope here:** any UI beyond plain text answers.
- **Touches:** `plugins/pdlc/skills/trace/SKILL.md`
- **Depends on:** Step 8

### Step 11: Tracker port and `board` · `[ ]` GATED · Parallel group: none

- **Do:** The user chose GitHub Projects and Linear. Write both adapters and the `board`
  skill, outbound only. Make every core skill tell the tracker port
  when it changes a status.
- **Done when:** the test project's intent and changes appear as a card and sub-cards in the
  right columns, and move when their status changes.
- **Out of scope here:** acting on board moves.
- **Touches:** `plugins/pdlc/skills/board/SKILL.md`, `plugins/pdlc/skills/init/references/adapters/tracker-*`,
  the "tell the tracker" line in each core skill
- **Depends on:** Step 8

### Step 12: End-to-end run and README · `[x]` AUTO · Parallel group: none

- **Do:** In a fresh scratch project, run one new intent from inbox to merged PR using only
  pdlc skills. Fix anything that breaks. Re-read every pdlc file for plain prose. Add a short
  pdlc section to `README.md`. Check `plugins/pdlc/INSTALL.md` still matches how install
  really works. Run both `claude plugin validate` commands.
- **Done when:** the run completes with no manual file edits, the trace holds from ticket to
  code, and the README explains how to install and start.
- **Out of scope here:** new features found during the run; add them to the outline's open
  questions instead.
- **Touches:** `README.md`, any `plugins/pdlc/**` file the run shows is broken
- **Depends on:** Steps 9, 10, 11

### Step 13: pdlc on this repository · `[ ]` GATED · Parallel group: none

- **Do:** Install the released pdlc from the marketplace. Run `/pdlc:init` at the root of
  `pskills`. Confirm the map with the user: each skill a job, shared parts as capabilities,
  the writing style as a design spec. Then run one small real intent through it, chosen with
  the user (for example "add evals for `/quiz`"), using `claude plugin eval` as the check.
- **Done when:** `pskills` has a `pdlc/` state folder beside `plugins/pdlc/`; the intent
  reaches a verified PR built by the installed pdlc, not the working copy; the trace holds.
- **Out of scope here:** changing pdlc itself through pdlc. That is the next intent, once
  this works.
- **Touches:** `pdlc/**` (new, repo root), the files the chosen intent changes
- **Depends on:** Step 12

### Step 14: Folder per change, and handoffs · `[x]` AUTO · Parallel group: none

- **Do:** Each change lives in `pdlc/changes/CH-xxxx-name/` with `change.md`, `handoff.md`,
  `review/`, `review.gif` and `frames/`. Every stage reads the latest handoff first and
  writes one at the end (intent stages in the intent's "Handoff" section). Update the merge
  check, templates, skills and README template.
- **Done when:** unit tests pass on the new layout, and a live run writes a handoff at each stage.
- **Touches:** `plugins/pdlc/**`
- **Depends on:** Step 12

### Step 15: Stacked changes · `[x]` AUTO · Parallel group: none

- **Do:** A change branches from the change before it (recorded as `Base:`), its PR targets
  that branch, and PRs are retargeted when the one below merges. Fixes to a lower change
  are merged up the stack.
- **Done when:** a live run builds the second change on the first's unmerged branch.
- **Touches:** build, verify, delivery adapter, README template, reviewer packets
- **Depends on:** Step 14

### Step 16: Test writer, locked tests, plugin guard · `[x]` AUTO · Parallel group: none

- **Do:** Add `test-writer` and `builder` agents and a `tests` skill. The change spec gains
  "Interface" and "Check files". The test writer writes checks from the spec alone, they
  must fail, and they are locked (`Tests-Locked: <sha>`). A plugin hook stops the test
  writer reading app code and the builder editing checks; the merge check fails if checks
  changed after the lock.
- **Done when:** unit tests cover the guard and the lock; live, the hook blocks both.
- **Touches:** `plugins/pdlc/**`
- **Depends on:** Step 14

### Step 17: Independent reviewers with remits and packets · `[x]` AUTO · Parallel group: none

- **Do:** Remits (tests, specification, security, quality, compliance, privacy) as project
  files. A script builds one packet per remit: tests packets get spec and tests only, code
  packets get spec and code only. One fresh reviewer per packet, reading only its packet.
  The merge check requires every configured remit to pass.
- **Done when:** unit tests cover packets and the merge check; live, six reviews run.
- **Touches:** `plugins/pdlc/**`
- **Depends on:** Step 16

### Step 18: Visual review and GIFs · `[x]` AUTO · Parallel group: none

- **Do:** A `show` skill and `record_gif.mjs` record each acceptance check being performed,
  in a browser (web) or a terminal-style page (CLI), as `review.gif` plus key frames. The
  specification reviewer sees the frames. The commit names the GIF; the PR embeds it.
- **Done when:** real GIFs are produced for a web app and a CLI.
- **Touches:** `plugins/pdlc/**`
- **Depends on:** Step 17

### Step 19: `/pdlc:ship` · `[x]` AUTO · Parallel group: none

- **Do:** One skill runs intake → ready → change → per change: tests → build → show →
  verify → propose, stacking changes, defaulting questions, and stopping only for
  contradictions, out-of-scope files, repeated failure, or the end of the stack.
- **Done when:** one `/pdlc:ship` call takes an intent to stacked, verified PRs.
- **Touches:** `plugins/pdlc/skills/ship/`
- **Depends on:** Step 18

### Step 20: End-to-end on a web app and a CLI · `[ ]` AUTO · Parallel group: none

- **Do:** Run `/pdlc:ship` on a fresh small web app and on the Node CLI. Fix what breaks.
- **Done when:** both reach verified, stacked PRs with GIFs, locked tests and six passing
  reviews, with no manual file edits.
- **Touches:** anything in `plugins/pdlc/` the runs show is broken
- **Depends on:** Step 19

## Verification and rollback

- **Human verifies by:** reading `plugins/pdlc/OUTLINE.md` and each finished skill, then watching or
  repeating the step 12 run.
- **Failing looks like:** a skill that needs manual file edits to move on; a change that
  crosses two jobs or capabilities; a commit without trailers; a merge allowed with an
  unverified requirement; prose that needs rereading.
- **Rollback:** everything lives in `plugins/pdlc/`, the marketplace file, `plans/`, one
  README section and, after step 13, the root `pdlc/` folder. `git revert`
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

[2026-09-27] Step 1: done
Changed: moved the plugin to plugins/pdlc/; added .claude-plugin/marketplace.json (name
         "pskills"); added author to plugin.json; added plugins/pdlc/INSTALL.md
Decided: plugin lives under plugins/ so it can't collide with a root pdlc/ state folder
         when pdlc manages this repo. The "tests" port is now "checks", so pdlc fits any
         system (a check can be a test, script, lint rule, eval or query).
Proven: `claude plugin validate` passes for the plugin and the marketplace. Installing
        pdlc@pskills --scope project into a scratch repo works and lists the plugin as
        enabled. A headless session dispatched the pdlc:recon agent and got a reply.
Surprises: project settings store enabledPlugins as an object ({"pdlc@pskills": true}),
           not an array. INSTALL.md uses the object form.

[2026-09-27] Step 2: done
Changed: plugins/pdlc/skills/init/references/{templates,ports,adapters}/
Decided: six templates (intent, job, capability, design, change, config); five port
         contracts with conformance checks; four default adapters. Spec files carry
         "Status: stub|active"; changes go planned → building → in review → merged |
         cancelled. The change spec header is one line
         (Intent · Scope · Status · Ticket · Branch) so a script can read it. The merge
         check lives at pdlc/bin/check_merge.py in the project (built in step 8).
Surprises: none.

[2026-09-27] Step 3: done
Changed: plugins/pdlc/skills/init/references/defaults/ (six design specs)
Decided: defaults = ids, check tagging, commit trailers, review checklist, branches,
         writing style. Each says "Ask at init: yes|no" — this answers the outline's open
         question: ask about check tagging, branches and writing style; apply ids,
         trailers and the review checklist without asking (they are near-core). Board
         columns live in config.md, not a design spec, and are only asked about when a
         tracker is set.
Surprises: none.

[2026-09-27] Step 4: done
Changed: init/SKILL.md, agents/recon.md, init references (README template, check_merge.py
         added to bin/), check-tagging default, checks-command adapter, config template
Decided: init takes "defaults" to run without questions (needed for headless runs and
         quick starts). Each file belongs to at most one code map; mixed files go to the
         job. Check names may carry the ID with underscores (CAP_email_R3) where the runner
         forbids dots and dashes. A pdlc/README.md in each project holds the shared rules
         so each skill stays short.
Proven: /pdlc:init defaults ran headless on a Python unittest CLI (pyapp) and a Node
        node:test CLI (nodecli). Both got a full pdlc/ folder, one job and one capability
        from recon, six design specs, filled checks commands, and a "Set up pdlc" commit.
Surprises: first pyapp run stopped to ask about the map despite "defaults", and recon put
           one file in two code maps — both fixed above. The unittest naming limit was
           spotted by the init run itself.

[2026-09-27] Step 5: done
Changed: intake/ready/conventions SKILL.md, README template ("Asking questions"),
         agents/recon.md
Decided: every skill that asks follows one shared rule in pdlc/README.md; with
         "defaults" it takes its recommendation and notes it. Contradictions are never
         defaulted: ready leaves both requirements proposed and asks. Recon must describe
         observable behaviour, never implementation.
Proven: on pyapp, IN-0001 ("remove <n>" + crash-safe saving) went new → specifying →
        ready. Intake deepened both stub specs through recon, then wrote JOB.R9, JOB.R10
        and CAP-task-storage.R5 as proposed. Ready found a real contradiction between the
        new R5 (crash-safe) and recon's R4 (which pinned write_text), asked, and after the
        answer rewrote R4 as an outcome and marked all four ready.
Surprises: ready first ignored "defaults" (the skill's own step said "ask"); and recon's
           implementation-shaped requirement caused the contradiction. Both fixed.

[2026-09-27] Step 6: done
Changed: none (skill worked as written)
Proven: on pyapp, IN-0001 split into CH-0001 (CAP-task-storage, crash-safe save; files
        tasks/store.py, tests/test_store.py) then CH-0002 (JOB-manage-tasks, remove;
        files tasks/cli.py, tests/test_cli.py). Capability first; the job change lists no
        capability files.
Surprises: none.

[2026-09-27] Step 7: done
Changed: build/SKILL.md (red-first nuance), commit-trailers default and delivery-github
         adapter (one trailer block)
Decided: a check for behaviour that already exists may pass at once; red-first applies to
         new behaviour. pdlc trailers share one final block with any other trailers.
Proven: on pyapp, /pdlc:build built CH-0001 on pdlc/CH-0001-crash-safe-save: the R5 check
        failed first against in-place write_text, then passed after write-to-temp and
        os.replace. One commit per step with Intent/Change/Req; both requirements set to
        built; all checks pass.
Surprises: the building session's own co-author trailers landed in a second block, which
           hid pdlc's trailers from `git log --format=%(trailers)` (grep still found them).

[2026-09-27] Step 8: done
Changed: verify/SKILL.md, agents/reviewer.md, init/references/bin/check_merge.py,
         tests/test_check_merge.py (8 unit tests), README template ("pdlc's own files"),
         commit-trailers default, delivery-github adapter (merged? without a PR)
Decided: the trace check needs only the Intent/Change/Req lines in each message, not a
         perfect trailer block. pdlc's own files change only by a pdlc upgrade on main,
         never on a change branch.
Proven: the merge check unit tests pass and catch a broken version. On pyapp, verify
        failed CH-0001 twice for real reasons (first the trailer blocks under the strict
        rule; then out-of-scope edits to pdlc files and .pyc files that I, the tester,
        had put on the branch), and the merge check printed FAIL while requirements were
        built. After a clean redo, verify passed: checks pass, reviewer pass, both
        requirements verified, gate ok. With no remote, it stopped and gave the branch
        and PR body, as the adapter says.
Surprises: the reviewer caught me loosening a rule on the change branch to excuse its
           own finding. That is exactly the behaviour we want.

[2026-09-27] Step 9: done
Changed: conventions/SKILL.md (migrations also for new conventions the code doesn't
         follow), README template (DES-pdlc-* belong to the project once changed)
Proven: on pyapp, /pdlc:conventions agreed DES-json-formatting (indent 2, sorted keys),
        found the one writer that doesn't sort keys (CAP-task-storage), and filed IN-0002
        "Migrate CAP-task-storage to DES-json-formatting" as new, without starting it.
Surprises: the "pdlc's own files" rule clashed with changing DES-pdlc-* defaults; fixed.

[2026-09-27] Step 10: done
Changed: every writing skill now starts with the README's "Before any work" catch-up
Proven: on pyapp, /pdlc:trace went from tasks/store.py:24 (os.replace) to commit 4078f47,
        CAP-task-storage.R5, CH-0001 and IN-0001; and from IN-0001 to its four
        requirements, two changes and their checks. It stayed read-only and pointed out
        that CH-0002's merge hadn't been recorded yet. The next intake then ran the
        catch-up: both changes set to merged and IN-0001 to done.
Surprises: skills weren't running the catch-up until told to in their own first line.

[2026-09-27] Step 11: in progress (blocked on board access)
Changed: adapters tracker-github-projects and tracker-linear; board/SKILL.md written in
         full with a dry-run mode; config template gains "Tracker settings"; outline
Decided: user chose GitHub Projects and Linear. A card's key is stored in the intent's or
         change's existing Ticket field. GitHub Projects has no sub-items for drafts, so
         change cards carry the intent ID in their title; Linear uses sub-issues.
Proven: /pdlc:board dry-run on pyapp (tracker set to a GitHub project) listed 3 intents
        and 2 changes with the right target columns and said 5 cards would be created,
        touching nothing.
Not yet proven: real cards on a board. This session has no GitHub Projects tools (no gh
        CLI, no project tools in the GitHub connector) and no Linear connection.

[2026-09-27] Extra (user request): optional live dashboard
Changed: skills/dashboard/ (SKILL.md, references/dashboard-builder.md,
         dashboard-builder-guard.py, claude-md-rule.md); init offers it (step 6);
         tests/test_dashboard_guard.py (6 tests); README, INSTALL, OUTLINE
Decided: opt-in only, default no even with "defaults", because it writes to ~/.claude.
         The agent (opus, effort medium, memory user, preloads dataviz and
         artifact-design) may only use .dashboard/ and its memory; a PreToolUse guard in
         its frontmatter enforces this and it has no shell. The style question goes
         through the main session, since a subagent can't ask the user directly.
Proven: live run in a scratch project built .dashboard/index.html with real times, the
        default action on each question, a 10-second reload, and the style question; the
        guard blocked a request to read notes.txt. Passing the answer (dark, dense,
        #e11d48) saved style.md to ~/.claude/agent-memory/dashboard-builder/ and rebuilt
        the page in that style without the question.

[2026-09-27] Step 12: done (tracker none; board part waits on step 11 access)
Changed across three runs: Req trailer only for commits touching files outside pdlc/;
         merge check finds the change for the branch being merged (it had passed
         vacuously); retired requirements need no check; INSTALL explains making the merge
         check a required CI check. README and INSTALL updated earlier.
Proven: third run on a fresh copy of the Node CLI, only pdlc skills with "defaults", no
        manual file edits; my only actions were approving merges after the merge check
        printed ok. IN-0001 "greet in Spanish" → CH-0001 (CAP-greeting) and CH-0002
        (JOB-greet-cli), each built check-first, verified, gate ok, merged.
        `greet Ana --lang es` prints "Hola, Ana!", English stays default, 3/3 checks pass.
        All 13 non-merge commits name their intent; both code commits name their
        requirement. trace answered "what did IN-0001 change?".
Surprises: run 1 — my test script merged despite a FAIL (script bug; the lesson is that
           only CI can enforce the gate) and the branch-start commit had no Req. Run 2 —
           the vacuous merge-check pass, and review asking for a check on a retired
           requirement. All fixed with tests before run 3.

[2026-09-27] Steps 14-19: done
Changed: change folders and handoffs; stacked changes (Base:); test-writer and builder
         agents, tests skill, Tests-Locked; plugin guard hook by agent_type; six remit
         files, make_packets.py, parallel reviewers; record_gif.mjs, show skill, visual
         port and adapters; ship skill. 44 unit tests, each failing first.
Proven: the guard blocked pdlc:test-writer reading src/greet.js and pdlc:builder editing
        test/greet.test.js (live, logged). GIFs recorded in terminal mode (Node CLI) and
        browser mode (web app). One `/pdlc:ship defaults` call on a fresh tip-calculator
        web app turned "split the bill" into three stacked changes (CAP-tip-calculation,
        HTTP serving, JOB-calculate-a-tip), each with locked, independently reviewed
        tests, a GIF, five passing code reviews and a green merge check on its branch.
Surprises: subagents can't start subagents, so ship runs stages in the main session and
           the stages start the role agents. A code review then found five bugs (guard
           misread the template's check-folder line, which ship worked around mid-run; an
           unwritable guard log turned blocks into allows; missing base branch gave empty
           packets; recorder left the app running on errors and kept stale frames). All
           fixed, three with new failing-first tests. The page change had no automated
           checks (no browser check runner), so change now files an intent to add one.
Known limit: the builder has a shell, which the file guard can't watch; the merge check's
           lock comparison catches any change to check files.
```
