---
name: quiz-plan-execute
description: >
  Executes a `.plan.md` produced by /quiz-plan, working each step to completion
  through a strict 6-stage TDD gate: (1) understand acceptance criteria,
  (2) red — write a failing test, (3) green — write impl to pass, (4) refactor,
  (5) review against acceptance criteria, (6) commit. Every stage must finish
  before the next begins; every step ends in its own commit. At start it asks
  whether to work in a new branch, a new git worktree, and/or dispatch each step
  to a fresh subagent. On completion it offers to squash-merge locally or open a
  PR. Use when the user says "/quiz-plan-execute", "execute the plan", "run my
  plan.md", or "build from the quiz-plan".
---

# Quiz Plan Execute

## Overview

This skill is the executor twin of [[quiz-plan]]. Where `/quiz-plan` interviews the
user and writes a `.plan.md`, this skill **reads that plan and does the work** — one
step at a time, each step driven through a disciplined test-first loop, each step
landing as its own commit.

It is deliberately strict. The 6-stage process per step is a gate, not a checklist:
a stage must be *complete and verified* before the next begins. You do not write
implementation before a failing test exists. You do not refactor before the test is
green. You do not commit before the step is reviewed against its acceptance criteria.

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

Omit the path to auto-detect: glob `**/*.plan.md` at the project root. If exactly one
match, use it. If several, list them and ask which. If none, tell the user to run
`/quiz-plan` first and stop.

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
- **Steps** — ordered list. For each step capture: name, gate (AUTO | GATED),
  the **Do** instructions, the **Done when** criteria, and **Out of scope here**.
- **Progress log** — the memory of prior sessions. Find the first step not marked done
  and resume there. Do **not** redo completed steps or reopen decisions logged there.

**The `Done when` field of each step IS that step's acceptance criteria.** The 6-stage
loop below consumes it directly. If a step has no falsifiable `Done when`, stop and ask
the user to clarify it before starting — you cannot write a red test against a vague
criterion.

**S-3. Ask the runtime options (interactive prompt, one screen).**

Ask the user these three, up front, before any work:

```
Before I start executing <plan-name> (<N> steps):

  1. New branch?   [suggest: <branch from plan header, or feature/<plan-name>>]
     → y (use suggested) / a name / n (work on current branch)

  2. New worktree?  [y/N]
     → if y, I create a linked worktree so your current checkout is untouched

  3. New agent per step?  [y/N]
     → if y, each step is handed to a fresh subagent (isolated context);
       if n, I run every step inline in this thread
```

Apply the answers:

- **New branch (y / name):** `git checkout -b <name>` from the current base. Record the
  base branch (`git rev-parse --abbrev-ref HEAD` before switching) — you need it for the
  finish step. If the plan header already names a branch and the user accepts it, use that.
- **New worktree (y):** `git worktree add <path> -b <branch>` (path: a sibling dir like
  `../<repo>-<branch>`). Announce the worktree path. All subsequent work happens there.
- **New agent per step (y):** for each step, dispatch the entire 6-stage loop to a fresh
  subagent via the Agent tool (see "Subagent dispatch" below). Default (n) = run inline.

Confirm the chosen options back to the user in one line. Set the plan header
**Status** to `In progress` (from `Draft` / `Agreed`), then begin at the first
unfinished step.

---

## THE PER-STEP LOOP (6 gated stages)

Run this loop for each step in order. **Each stage must complete before the next
begins.** If a stage cannot complete, stop and follow the Boundaries "Stop and ask"
rule from the plan — do not skip ahead.

Announce the step and stage as you go, e.g. `Step 2 · Stage 2/6 (red)`.

### Stage 1 — Understand acceptance criteria

- Read the step's `Do`, `Done when`, and `Out of scope here`.
- Restate the acceptance criteria in one or two concrete, falsifiable sentences —
  the exact observable behaviour that will prove the step done.
- Cross-check against Intent and Boundaries. If the step conflicts with either, **stop
  and ask** — do not resolve it yourself.
- Identify the test file and the smallest test that would fail today and pass when done.

**Gate:** you can name the precise test to write and the observable it asserts. Do not
proceed otherwise.

### Stage 2 — Red (write the failing test)

- Write **only the test**. No implementation.
- Run the plan's test command (from Ground truth). The new test **must fail**, and it
  must fail for the right reason (assertion / missing symbol — not a syntax error or
  wrong command).
- If it passes immediately, the test is wrong or the behaviour already exists — stop and
  reassess before writing any implementation.

**Gate:** the test runs and fails for the expected reason. Quote the failure. Do not
write implementation until this holds.

### Stage 3 — Green (make it pass)

- Write the **minimum** implementation to satisfy the failing test. No extra features,
  no gold-plating — `Out of scope here` stays out.
- Run the test command. The new test **and all previously passing tests** must be green.
- If an unexpected pre-existing test fails, that is the Boundaries "a test you didn't
  expect fails" trigger — stop and ask.

**Gate:** full test command is green. Do not refactor until this holds.

### Stage 4 — Refactor

With tests green as a safety net, improve the code without changing behaviour:
- Remove duplication.
- Conform to the conventions named in the plan's Ground truth (read the referenced
  style docs / CLAUDE.md / neighbouring code — do not guess).
- Reduce complexity; improve naming and readability.
- Re-run the test command after refactoring — must stay green.

**Gate:** tests still green, code meets the plan's conventions. Refactor touches only
code in scope for this step.

### Stage 5 — Review against acceptance criteria

- Re-read the step's `Done when`. Verify each clause is actually met by the current code
  — not "should be", *is*, checked by running the relevant command/test.
- Verify nothing in `Out of scope here` or Boundaries "Must not touch" was modified
  (`git diff --stat` to confirm the blast radius).
- If any criterion is unmet, return to the appropriate earlier stage. Do not commit a
  step that fails its own review.

**Gate:** every `Done when` clause verified true; blast radius within "May modify".

### Stage 6 — Commit

- Run the plan's **lint** command if defined; fix lint before committing.
- Stage the step's changes and the plan file (with its Progress log / tracker updated —
  see below). One commit per step.
- Commit message (Conventional Commits), body explains the *why*:

```
<type>(<scope>): <step name>

<one line: what changed and why, referencing the plan step>

Plan: <plan-file> · Step <n>
```

**Update the plan file before committing:** mark the step `[x]`, update the header
progress bar (12-char `█`/`░` bar) and the `X/N (P%)` count, and append a Progress log
entry:

```
[date] Step <n>: done
Changed: <files touched>
Decided: <choices made and why>
Surprises: <anything that diverged from ground truth>
```

**Gate:** commit exists (`git log -1 --oneline`), plan tracker reflects the new state.

### After the step

- If the step gate is **GATED**: stop, report the step result to the user, and wait for
  review before starting the next step.
- If the step gate is **AUTO**: continue to the next step.
- If running subagents (see below): collect the subagent's result, verify a commit
  landed, then continue.

---

## Subagent dispatch (only when "new agent per step" = y)

When the user opted into a fresh agent per step, dispatch each step like this:

- Use the Agent tool with a general-purpose (or `lead-engineer`) subagent.
- Hand it: the plan's Intent, Ground truth, Boundaries, and **just that one step**
  (Do / Done when / Out of scope), plus the full 6-stage loop as its instructions.
- Instruct it to run all 6 stages, land exactly one commit, update the plan tracker, and
  return a short receipt (commit sha, files changed, criteria verified).
- If the subagent reports it could not complete a stage's gate, do not let it continue —
  treat as blocked, surface to the user.
- Steps run **sequentially**, not in parallel — later steps depend on earlier commits and
  the shared plan file. One subagent at a time.

Inline mode (default) runs the identical loop in the main thread.

---

## ON COMPLETION — squash-merge or PR

When all steps are done (tracker at 100%), set the plan header **Status** to `Done`,
then ask the user:

```
All <N> steps complete on <branch>. Finish how?

  1. Squash-merge locally  — squash the per-step commits into one on <base>,
                             then delete <branch> (and worktree if used).
  2. Open a PR             — push <branch> and open a pull request via gh.
```

**Option 1 — squash-merge locally:**
```bash
git checkout <base>
git merge --squash <branch>
git commit          # compose a summary message from the plan Intent + step list
git branch -D <branch>
git worktree remove <path>   # only if a worktree was created
```
Show the composed squash message and confirm before committing.

**Option 2 — open a PR:**
```bash
git push -u origin <branch>
gh pr create --fill   # title from plan Intent; body = Intent + step summary + plan link
```
If `gh` is missing, fall back to pushing the branch and giving the user the compare URL.

Do not merge or push without the user's explicit choice. Report the final commit / PR
URL when done.

---

## Rules recap (the discipline)

1. **Stages are gates, not steps.** Never advance a stage until the current one is
   verifiably complete. No impl before a red test. No refactor before green. No commit
   before review.
2. **One commit per step.** The commit is stage 6; the plan tracker is updated in the
   same commit.
3. **The plan is law.** Intent and Boundaries override your judgement. On conflict, stop
   and ask — never resolve it yourself.
4. **Two failed attempts = the plan is wrong**, not that you should try harder. Stop and
   surface it (from the plan's Boundaries rule).
5. **Verify, don't assume.** Read real API/source definitions and the conventions the
   plan cites before writing calls. Run commands to confirm gates — never mark a gate
   passed from memory.
6. **Respect the gate flag.** GATED steps pause for human review; AUTO steps continue.
