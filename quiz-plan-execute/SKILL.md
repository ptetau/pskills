---
name: quiz-plan-execute
description: >
  Executes a `.plan.md` produced by /quiz-plan. It works each step to completion
  through a strict 6-stage TDD gate. The first three stages are (1) understand
  acceptance criteria, (2) red — write a failing test, and (3) green — write impl to
  pass. The last three are (4) refactor, (5) review against acceptance criteria, and
  (6) commit. Every stage must finish before the next begins; every step ends in its
  own commit. Steps that share a `Parallel group` tag run concurrently, one agent per
  step, each in its own git worktree. The skill dispatches them via the harness's
  Workflow tool when available, else with manual worktrees capped at 4 concurrent.
  Then it merges them back in declared step order, one commit per step. At start it
  asks one question: whether to create a new branch for the work. On completion it
  offers to squash-merge locally or open a PR. Use when the user says
  "/quiz-plan-execute", "execute the plan", "run my plan.md", or "build from the
  quiz-plan".
---

# Quiz Plan Execute

## Overview

This skill is the executor twin of [[quiz-plan]]. `/quiz-plan` interviews the user and
writes a `.plan.md`. This skill **reads that plan and does the work**, one step at a
time. It drives each step through a disciplined test-first loop, and each step lands as
its own commit.

It is deliberately strict. The 6-stage process per step is a gate, not a checklist:
a stage must be *complete and verified* before the next begins. You do not write
implementation before a failing test exists. You do not refactor before the test is
green. You do not commit before the step is reviewed against its acceptance criteria.

Steps usually run one at a time, in order. When the plan marks a run of steps with the
same `Parallel group` tag, those steps run concurrently instead. Each gets one agent,
isolated in its own git worktree. Then the skill merges them back onto the plan branch in
declared step order, still one commit per step. See "PARALLEL GROUP DISPATCH" below.

## When to Use This Skill

Use when:
- A `.plan.md` (from `/quiz-plan`) exists and the user wants it executed
- The user says `/quiz-plan-execute`, "execute the plan", "run the plan", "implement my plan.md"
- The user wants disciplined TDD execution with per-step commits

Do **not** use when:
- No plan file exists yet — run `/quiz-plan` first
- The change is a trivial 1-file fix with no test surface
- The user wants exploratory, non-committing work

## Invocation

```
/quiz-plan-execute [path/to/x.plan.md]
```

Omit the path to auto-detect: glob `plans/*.plan.md` (non-recursive, so it excludes
`plans/completed/`) at the project root. If exactly one match, use it. If several,
list them and ask which. If none, tell the user to run `/quiz-plan` first. Then stop.

---

## SETUP: before touching any code

**S-1. Verify prerequisites.**

```bash
git rev-parse --show-toplevel   # must succeed — confirms git repo
git status --porcelain          # working tree should be clean; if dirty, stop and ask
gh --version                    # warn if missing (PR option will be unavailable)
```

If the working tree is dirty, stop and ask the user to commit or stash first. Executing
a plan onto a dirty tree corrupts per-step commit boundaries.

**S-2. Read and parse the plan.**

Read the plan file in full. Extract:
- **Intent, Ground truth, Boundaries** — the rules you must not violate.
- **Build / test / lint commands** — from Ground truth. You run these verbatim; never
  invent them.
- **Steps** — ordered list. For each step, capture:
  - name and gate (AUTO | GATED);
  - the **Do** instructions and the **Done when** criteria;
  - **Out of scope here**, **Touches** and **Depends on**;
  - **Parallel group** (`none` or a group id).
- **Progress log** — the memory of prior sessions. Find the first step not marked done
  and resume there. **Don't** redo completed steps or reopen decisions logged there.

**The `Done when` field of each step IS that step's acceptance criteria.** The 6-stage
loop below consumes it directly. If a step has no falsifiable `Done when`, stop and ask
the user to clarify it before starting. You can't write a red test against a vague
criterion.

**S-3. Ask the one setup question: new branch?**

Ask it the [[quiz]] way. Use the picker (the `AskUserQuestion` tool) when the session has
it. Otherwise, ask a plain-markdown question. No ASCII card or code block. Ask one
question. Give each option three short sentences: what, why and cost, as /quiz's Step 2
(Write each question) says.

- **header:** `Branch`
- **question:** `Create a new branch for <plan-name> (<N> steps)?`
- **A · Yes, use `<branch>`**: It creates `<branch>` off the current HEAD. It keeps
  every step's commit apart from other work in flight. It costs nothing to undo.
- **B · No, use the current branch**: Each step commits straight to the current branch.
  It is the fastest choice on a throwaway branch. It mixes plan commits with anything
  already there.
- **A custom name**: the picker's "Other", or in the fallback, any reply that is a
  branch name.

Recommend on evidence, as /quiz does:

- If you're on the repo's default branch, or the plan has more than one step, recommend
  A.
- If the current branch is already named for this plan, recommend B.
- Otherwise, recommend nothing.

In the picker, `(Recommended)` goes at the end of that option's label. In the fallback,
use /quiz's layout:

- `**Question 1 of 1 · Branch**`;
- the question;
- options A and B as a bulleted list;
- `Reply A or B, or type a branch name.`

Apply the answer:

- **A, or a typed branch name:** `git checkout -b <name>` from the current base, using
  `<branch>` for A. Record the base branch (`git rev-parse --abbrev-ref HEAD` before
  switching); you need it for the finish step. If the plan header already names a
  branch, that is `<branch>`.
- **B:** stay on the current branch.
- **Anything else** (e.g. "not sure"): ask once in plain prose which of the two to do.

By default, every step runs in place, inline, in the main thread. The exception is
automatic, not asked: a run of not-done steps sharing a `Parallel group` tag dispatches
to concurrent worktree-isolated agents (see "PARALLEL GROUP DISPATCH" below). That's a
property of the plan (set by `/quiz-plan`), not a runtime toggle, so it isn't part of
this setup question.

Confirm the chosen option back to the user in one line. Set the plan header
**Status** to `In progress` (from `Draft` / `Agreed`). Then begin at the first
unfinished step.

---

## THE PER-STEP LOOP (6 gated stages)

Run this loop for each step in order. **Each stage must complete before the next
begins.** If a stage can't complete, stop and follow the Boundaries "Stop and ask" rule
from the plan. Don't skip ahead.

Announce the step and stage as you go, e.g. `Step 2 · Stage 2/6 (red)`.

### Stage 1 — Understand acceptance criteria

- Read the step's `Do`, `Done when`, and `Out of scope here`.
- Restate the acceptance criteria in one or two concrete, falsifiable sentences —
  the exact observable behaviour that will prove the step done.
- Cross-check against Intent and Boundaries. If the step conflicts with either, **stop
  and ask**. Don't resolve the conflict yourself.
- Identify the test file and the smallest test that would fail today and pass when done.

**Gate:** you can name the precise test to write and the observable it asserts. Don't
proceed otherwise.

### Stage 2 — Red (write the failing test)

- Write **only the test**. No implementation.
- Run the plan's test command (from Ground truth). The new test **must fail**, and it
  must fail for the right reason (assertion / missing symbol — not a syntax error or
  wrong command).
- If the test passes immediately, the test is wrong or the behaviour already exists.
  Stop and reassess before writing any implementation.

**Gate:** the test runs and fails for the expected reason. Quote the failure. Don't write
implementation until this holds.

### Stage 3 — Green (make it pass)

- Write the **minimum** implementation to satisfy the failing test. No extra features,
  no gold-plating — `Out of scope here` stays out.
- Run the test command. The new test **and all previously passing tests** must be green.
- If an unexpected pre-existing test fails, that is the Boundaries "a test you didn't
  expect fails" trigger. Stop and ask.

**Gate:** full test command is green. Don't refactor until this holds.

### Stage 4 — Refactor

With tests green as a safety net, improve the code without changing behaviour:
- Remove duplication.
- Conform to the conventions named in the plan's Ground truth (read the referenced
  style docs / CLAUDE.md / neighbouring code; don't guess).
- Reduce complexity; improve naming and readability.
- After refactoring, re-run the test command. The tests must stay green.

**Gate:** tests still green, code meets the plan's conventions. Refactor touches only
code in scope for this step.

### Stage 5 — Review against acceptance criteria

- Re-read the step's `Done when`. Verify that the current code actually meets each
  clause: not "should be", *is*. Check each clause by running the relevant command/test.
- Verify that the step modified nothing in `Out of scope here` or Boundaries "Must not
  touch". Use `git diff --stat` to confirm the blast radius.
- If any criterion is unmet, return to the appropriate earlier stage. Don't commit a
  step that fails its own review.

**Gate:** every `Done when` clause verified true; blast radius within "May modify".

### Stage 6 — Commit

- If the plan defines a **lint** command, run it. Fix lint before committing.
- Stage the step's changes and the plan file (with its Progress log / tracker updated;
  see below). One commit per step.
- Commit message (Conventional Commits), body explains the *why*:

```
<type>(<scope>): <step name>

<one line: what changed and why, referencing the plan step>

Plan: <plan-file> · Step <n>
```

**Update the plan file before committing:**

- Mark the step `[x]`.
- Update the header progress bar (12-char `█`/`░` bar) and the `X/N (P%)` count.
- Append a Progress log entry:

```
[date] Step <n>: done
Changed: <files touched>
Decided: <choices made and why>
Surprises: <anything that diverged from ground truth>
```

**Gate:** commit exists (`git log -1 --oneline`), plan tracker reflects the new state.

### After the step

- If the step gate is **GATED** (a human gate), report the step result to the user (step
  name, commit sha, criteria met). Then **stop and wait for review** before starting the
  next step. GATED means a human should look before the plan proceeds; that pause is the
  point, not overhead to skip.
- If the step gate is **AUTO**, report a one-line status. Then continue immediately to
  the next step, with no pause.
- Boundaries "Stop and ask" triggers stop execution regardless of gate, as always. The
  triggers are: an unexpected test failure, a needed out-of-scope change, ambiguous
  instructions, and two failed attempts at the same fix.

---

## PARALLEL GROUP DISPATCH (when the plan declares one)

Before running the next not-done step through the loop above, check its `Parallel group`
field:

- If the field is `none`, run the step exactly as described above. Nothing below applies.
- If other not-done steps share the step's group id, run this section instead of the
  single-step loop. Run it for all of those steps at once.

**PG-1. Detect the group.** Take the contiguous run of not-done steps sharing the same
`Parallel group` id, starting at the resume point. Every step in the run is AUTO, because
GATED steps never carry a group id (see [[quiz-plan]]). So nothing here needs to reconcile
grouping with pausing for review.

**PG-2. Dispatch — prefer the harness's Workflow tool.** If the Workflow tool is available
in this session, use it. Make one `agent()` call per step in the group, with
`isolation: 'worktree'`. Each step gets its own throwaway worktree + branch off the
current HEAD.

Give each agent only that one step's Intent-relevant context. That context is Ground
truth, Boundaries, and the step's own Do / Done when / Out of scope / Touches. Never give
the agent the sibling steps. Tell it to run Stages 1-5 of the loop above (Understand
through Review) inside its worktree. Use `schema` to get back a receipt:
`{step, worktreePath, branch, filesChanged, decided, surprises}`. Stop each agent short of
Stage 6 (Commit): no commit, no plan-file edit. PG-4 (Merge each worktree back) gives the
reason.

Workflow scripts have no filesystem or git access of their own. The script's only job is
spawning the per-step subagents and collecting receipts. Workflow creates the worktrees.
The rest of the git work, reading diffs and merging them back, happens in your main
thread via Bash after the group returns. It doesn't happen inside the workflow script.

If the Workflow tool isn't available in this session, fall back to manual dispatch:

1. For each step, run `git worktree add <path> -b step-<n>` yourself (sibling dirs, e.g.
   `../<repo>-step-<n>`).
2. Call the Agent tool once per step, with the same instructions as above. Batch at most
   4 concurrent calls at a time (one message, up to 4 parallel tool-use blocks).
3. Wait for that batch. If the group has more steps, dispatch the next batch.

**PG-3. Wait for every step in the group.** A group is a barrier. Don't merge anything
until every step has either returned a receipt or failed its own Stage 1-5 gate. A step
that fails its gate is blocked. Leave its worktree in place and don't merge it. Follow
Boundaries "Stop and ask" for that step specifically. Steps that succeeded still proceed
to PG-4 (Merge each worktree back).

**PG-4. Merge each worktree back in declared step order, never finish order.** Make one
commit per step. You compose each commit, not the subagent:
- For each step, ascending by step number: apply that step's diff (from its worktree) onto
  the plan branch.
- **You** update the plan file's tracker, checkbox, and Progress log entry for this step.
  The subagent never touched `plan.md`. This is deliberate. Every step's Stage 6 (Commit)
  writes to the same tracker/log region. If two worktree-isolated agents both edited it,
  every group would conflict on the plan file, even with perfectly disjoint code. Doing
  this edit once, serially, in the main thread avoids that.
- Commit (same Conventional Commits format as the single-step Stage 6).
- Remove the worktree and delete its branch.
- **If applying a step's diff conflicts with what an earlier step in this merge already
  landed**, the `Touches` sets weren't disjoint after all. Retry that one step's Stage 1-5
  loop sequentially against the now-current plan branch, exactly once, silently. Log the
  retry under that step's Progress-log "Surprises" line, but don't stop to ask. If the
  retry fails or conflicts again, that's the existing Boundaries "two failed attempts"
  trigger. Stop and ask.

**PG-5. Report and continue.** Report one status line per step in the group. Then continue
to the next step or group, with no pause, since every grouped step is AUTO.

---

## ON COMPLETION — squash-merge or PR

When all steps are done (tracker at 100%), set the plan header **Status** to `Done`. Then
move the plan file into a `completed/` folder inside its parent folder. For example,
`plans/<name>.plan.md` becomes `plans/completed/<name>.plan.md`. If `plans/completed/`
doesn't exist, create it. If the plan file is tracked, use `git mv`, so history follows
the move.

Update the plan's own **Plan location** header field to the new path. Then ask the user:

```
All <N> steps complete on <branch>. Finish how?

  1. Squash-merge locally  — squash the per-step commits into one on <base>,
                             then delete <branch>.
  2. Open a PR             — push <branch> and open a pull request via gh.
```

**Option 1 — squash-merge locally:**
```bash
git checkout <base>
git merge --squash <branch>
git commit          # compose a summary message from the plan Intent + step list
git branch -D <branch>
```
Show the composed squash message and confirm before committing.

**Option 2 — open a PR:**
```bash
git push -u origin <branch>
gh pr create --fill   # title from plan Intent; body = Intent + step summary + plan link
```
If `gh` is missing, fall back to pushing the branch and giving the user the compare URL.

Don't merge or push without the user's explicit choice. When done, report the final
commit / PR URL.

---

## Rules recap (the discipline)

1. **Stages are gates, not steps.** Never advance a stage until the current one is
   verifiably complete. No impl before a red test. No refactor before green. No commit
   before review.
2. **One commit per step.** The commit is stage 6. Update the plan tracker in the same
   commit.
3. **The plan is law.** Intent and Boundaries override your judgement. If there is a
   conflict, stop and ask. Never resolve the conflict yourself.
4. **Two failed attempts = the plan is wrong**, not that you should try harder. Stop and
   surface it (from the plan's Boundaries rule).
5. **Verify, don't assume.** Before writing calls, read real API/source definitions and
   the conventions the plan cites. Run commands to confirm gates. Never mark a gate passed
   from memory.
6. **Respect the gate flag.** GATED steps are a human gate: pause for review after each
   one. AUTO steps report a one-line status and continue without pausing. GATED pausing is
   the intended behaviour.
7. **Parallel groups still land one commit per step, composed by the main thread.**
   Concurrent dispatch changes *who* runs stages 1-5 (a fresh worktree-isolated agent per
   step) and *when* they run (together). It doesn't change the commit discipline. A
   grouped subagent never edits the plan file; only the main thread does, during
   merge-back. A broken independence assumption gets exactly one silent sequential retry
   before it escalates through rule 4 (two failed attempts).
