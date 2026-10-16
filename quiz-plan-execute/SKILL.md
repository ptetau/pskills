---
name: quiz-plan-execute
description: >
  Executes a `.plan.md` that /quiz-plan wrote. Takes each step to completion through a
  strict TDD gate of 6 stages. The stages are (1) understand the acceptance criteria,
  (2) red (write a failing test), (3) green (write the implementation that makes the test
  pass), (4) refactor, (5) review against the acceptance criteria, and (6) commit. Each
  stage must finish before the next stage starts. Each step ends in its own commit. Steps
  that share a `Parallel group` tag run at the same time, with one agent for each step in
  its own git worktree. The harness's Workflow tool dispatches the agents when the tool is
  available. If not, the skill uses manual worktrees, with a maximum of 4 at the same
  time. Then the skill merges the steps back in the declared step order, with one commit
  for each step. At the start, the skill asks one question: make a new branch for the work
  or not. At the end, the skill offers a local squash-merge or a PR. Use when the user says
  "/quiz-plan-execute", "execute the plan", "run my plan.md", or "build from the
  quiz-plan".
---

# Quiz Plan Execute

## Overview

This skill is the executor twin of [[quiz-plan]]. `/quiz-plan` interviews the user and
writes a `.plan.md`. This skill **reads that plan and does the work**. The skill does one
step at a time, takes each step through a disciplined test-first loop, and makes one
commit for each step.

The skill is deliberately strict. For each step, the 6 stages are a gate, not a checklist.
A stage must be *complete and verified* before the next stage starts. Do not write
implementation before a failing test exists. Do not refactor before the test is green. Do
not commit before you review the step against its acceptance criteria.

Usually, the steps run one at a time, in order. A plan can mark a run of steps with the
same `Parallel group` tag. These steps run at the same time instead, with one agent for
each step, and each agent in its own git worktree. Then the skill merges the steps back
onto the plan branch in the declared step order, still with one commit for each step. See
"PARALLEL GROUP DISPATCH" below.

## Writing

Write all text to `references/writing-guidelines.md`. This includes the replies to the
user, each question, and each file that this skill writes.

## When to Use This Skill

Use this skill in these conditions:

- A `.plan.md` (from `/quiz-plan`) exists, and the user wants to execute the plan.
- The user says `/quiz-plan-execute`, "execute the plan", "run the plan", or "implement my
  plan.md".
- The user wants disciplined TDD execution, with one commit for each step.

Do **not** use this skill in these conditions:

- No plan file exists yet. Run `/quiz-plan` first.
- The change is a trivial fix to 1 file, with no surface to test.
- The user wants exploratory work with no commits.

## Invocation

```
/quiz-plan-execute [path/to/x.plan.md]
```

If the user gives no path, find the plan automatically. Glob `plans/*.plan.md` at the
project root. The glob is not recursive, so the glob excludes `plans/completed/`.

- If exactly one file matches, use that file.
- If more than one file matches, list the files. Then ask the user which file to use.
- If no file matches, tell the user to run `/quiz-plan` first. Then stop.

---

## SETUP: before you change any code

**S-1: Examine the prerequisites.**

```bash
git rev-parse --show-toplevel   # must succeed — confirms git repo
git status --porcelain          # working tree should be clean; if dirty, stop and ask
gh --version                    # warn if missing (PR option will be unavailable)
```

If the working tree is dirty, stop. Ask the user to commit or stash the changes first.
Execution on a dirty tree corrupts the boundaries between the commits of the steps.

**S-2: Read and parse the plan.**

Read the full plan file. Extract these items:

- **Intent, Ground truth, Boundaries**: the rules that you must not break.
- **Build / test / lint commands**: from Ground truth. Run these commands verbatim. Do not
  invent commands.
- **Steps**: an ordered list. For each step, record these items:
  - The name, and the gate (AUTO | GATED).
  - The **Do** instructions and the **Done when** criteria.
  - **Out of scope here**, **Touches**, and **Depends on**.
  - **Parallel group** (`none` or a group id).
- **Progress log**: the memory of earlier sessions. Find the first step that is not
  marked done, and resume at that step. Do **not** do the completed steps again. Do not
  reopen the decisions that the log records.

**The `Done when` field of each step IS the acceptance criteria of that step.** The
6-stage loop below uses this field directly. If a step has no falsifiable `Done when`,
stop. Ask the user to make the criteria clear before you start the step. You cannot
write a red test against a vague criterion.

**S-3: Ask the one setup question: new branch?**

Ask the question the [[quiz]] way. If the session has the picker (the `AskUserQuestion`
tool), use the picker. If not, ask a plain-markdown question. Do not use an ASCII card or
a code block. Ask one question. Give each option one fluid sentence that tells what the
option does, why the option fits, and its cost:

- **header:** `Branch`
- **question:** `Create a new branch for <plan-name> (<N> steps)?`
- **A · Yes, use `<branch>`**: creates the branch from the current HEAD, so that each
  step's commit stays apart from other work in progress, and costs nothing to undo.
- **B · No, use the current branch**: is the fastest option if you are already on a
  throwaway branch, but it mixes the plan commits with all other commits on that branch.
- **A custom name**: the picker's "Other", or in the fallback, any reply that is a
  branch name.

Recommend on evidence, as /quiz does:

- Recommend A when you are on the default branch of the repository, or when the plan has
  more than one step.
- Recommend B when the name of the current branch already refers to this plan.
- In all other conditions, do not recommend an option.

In the picker, put `(Recommended)` at the end of the label of the recommended option. In
the fallback, use the layout of /quiz: `**Question 1 of 1 · Branch**`, the question,
options A and B as a bulleted list, then `Reply A or B, or type a branch name.`

Apply the answer:

- **A, or a typed branch name:** Run `git checkout -b <name>` from the current base. For
  A, use `<branch>` as the name. Before you change the branch, record the base branch
  (`git rev-parse --abbrev-ref HEAD`). The finish step (ON COMPLETION) needs the base
  branch. If the plan header already names a branch, use that name as `<branch>`.
- **B:** Stay on the current branch.
- **Anything else** (for example, "not sure"): Ask one time, in plain prose, which of the
  two options to do.

By default, each step runs in place, inline, in the main thread. The exception is
automatic. A run of not-done steps that share a `Parallel group` tag goes to concurrent
agents, each agent in its own worktree. See "PARALLEL GROUP DISPATCH" below. Parallel
groups are a property of the plan (`/quiz-plan` sets them), not a runtime toggle. Thus,
the setup question does not include parallel groups.

Tell the user the selected option in one line. Set the plan header **Status** to
`In progress` (from `Draft` or `Agreed`). Then start at the first unfinished step.

---

## THE PER-STEP LOOP (6 gated stages)

Run this loop for each step, in order. **Each stage must be complete before the next
stage starts.** If a stage cannot be complete, stop. Then obey the Boundaries "Stop and
ask" rule of the plan. Do not skip to a later stage.

When you start each stage, tell the user the step and the stage, for example
`Step 2 · Stage 2/6 (red)`.

### Stage 1 — Understand the acceptance criteria

- Read the `Do`, `Done when`, and `Out of scope here` fields of the step.
- Write the acceptance criteria again in one or two concrete, falsifiable sentences. The
  sentences give the exact observable behaviour that proves that the step is done.
- Compare the step with Intent and Boundaries. If the step conflicts with Intent or
  Boundaries, **stop and ask**. Do not resolve the conflict yourself.
- Find the test file. Find the smallest test that fails now and passes when the step is
  done.

**Gate:** You can name the exact test to write and the observable result that the test
asserts. If you cannot, do not continue.

### Stage 2 — Red (write the failing test)

- Write **only the test**. Do not write the implementation.
- Run the test command of the plan (from Ground truth). The new test **must fail**. The
  cause of the failure must be correct: an assertion or a missing symbol. A syntax error
  or an incorrect command is not a correct cause.
- If the test passes immediately, the test is incorrect, or the behaviour already exists.
  Stop and examine the problem again. Do not write implementation until then.

**Gate:** The test runs and fails for the expected cause. Quote the failure. Do not write
implementation until this condition is true.

### Stage 3 — Green (make the test pass)

- Write the **minimum** implementation that makes the failing test pass. Do not add
  features or polish that the test does not need. `Out of scope here` stays out.
- Run the test command. The new test **and all the tests that passed before** must be
  green.
- If a test that existed before fails unexpectedly, that failure is the Boundaries
  trigger "a test you didn't expect fails". Stop and ask.

**Gate:** The full test command is green. Do not refactor until this condition is true.

### Stage 4 — Refactor

The green tests are a safety net. Improve the code, but do not change its behaviour:

- Remove duplication.
- Obey the conventions that the Ground truth of the plan names. Read the style documents,
  CLAUDE.md, and the neighbouring code that the Ground truth refers to. Do not guess.
- Decrease the complexity. Make the names and the code easier to read.
- After the refactor, run the test command again. The tests must stay green.

**Gate:** The tests are still green, and the code obeys the conventions of the plan. The
refactor changes only code that is in scope for this step.

### Stage 5 — Review against the acceptance criteria

- Read the `Done when` of the step again. Make sure that the current code really meets
  each clause. "Should be" is not sufficient. Run the related command or test to prove
  that the clause *is* met.
- Make sure that you did not change anything in `Out of scope here` or in the Boundaries
  "Must not touch". Run `git diff --stat` to see the blast radius (all the changed files).
- If a criterion is not met, go back to the applicable earlier stage. Do not commit a step
  that fails its own review.

**Gate:** You proved that each `Done when` clause is true. All the changed files (the
blast radius) are inside "May modify".

### Stage 6 — Commit

- If the plan defines a **lint** command, run the command. Correct the lint findings
  before you commit.
- Stage the changes of the step and the plan file, with the updated Progress log and
  tracker (see below). Make one commit for each step.
- Write the commit message in the Conventional Commits format. In the body, tell *why*
  the change occurred:

```
<type>(<scope>): <step name>

<one line: what changed and why, with a reference to the plan step>

Plan: <plan-file> · Step <n>
```

**Update the plan file before you commit:**

- Mark the step `[x]`.
- Update the progress bar in the header (a bar of 12 `█`/`░` characters) and the
  `X/N (P%)` count.
- Add a Progress log entry at the end of the log:

```
[date] Step <n>: done
Changed: <the changed files>
Decided: <each decision and its reason>
Surprises: <each difference from the ground truth>
```

**Gate:** The commit exists (`git log -1 --oneline`), and the plan tracker shows the new
state.

### After the step

- If the gate of the step is **GATED** (a human gate), report the result of the step to
  the user. Give the step name, the commit SHA, and the criteria that the step meets.
  Then **stop, and wait for review** before you start the next step. GATED means that a
  person looks at the work before the plan continues. That pause is the purpose of the
  gate, not overhead. Do not skip the pause.
- If the gate of the step is **AUTO**, report a status of one line. Then continue to the
  next step immediately, with no pause.
- The Boundaries "Stop and ask" triggers stop the execution for each gate type, as
  always. These triggers are an unexpected test failure, a necessary change out of scope,
  ambiguous instructions, and two failed attempts at the same fix.

---

## PARALLEL GROUP DISPATCH (when the plan declares one)

Before you run the next not-done step through the loop above, examine the
`Parallel group` field of the step:

- If the value is `none`, run the step exactly as the loop above tells you. This section
  does not apply.
- If the value is a group id that other not-done steps share, run this section. Do not
  use the single-step loop for these steps. Run this section for all the steps of the
  group at the same time.

**PG-1: Find the group.** The group is the contiguous run of not-done steps that share
the same `Parallel group` id, from the resume point. Each step in the run is AUTO, because
GATED steps do not carry a group id (see [[quiz-plan]]). Thus, no pause for review occurs
inside a group.

**PG-2: Dispatch the steps, and prefer the Workflow tool of the harness.** If the Workflow
tool is available in this session, use the Workflow tool:

- Make one `agent()` call for each step in the group, with `isolation: 'worktree'`. Each
  step gets its own throwaway worktree and branch from the current HEAD.
- Give each agent only the Intent-relevant context of its own step. This context is
  Ground truth, Boundaries, and the `Do`, `Done when`, `Out of scope here`, and `Touches`
  of the step. Do not give an agent the sibling steps.
- Tell each agent to run Stages 1-5 of the loop above (Understand to Review) in its
  worktree.
- Use `schema` to get a receipt back:
  `{step, worktreePath, branch, filesChanged, decided, surprises}`.
- Stop each agent before Stage 6: no commit, and no edit to the plan file. PG-4 (merge in
  step order) gives the reason.

A Workflow script has no access of its own to the filesystem or to git. The script only
starts the subagents for the steps and collects their receipts. Workflow makes the
worktrees. Your main thread does the other git work through Bash after the group returns.
The main thread reads the diffs and merges the diffs back. The workflow script does not
do this git work.

If the Workflow tool is not available in this session, use manual dispatch instead:

1. For each step, run `git worktree add <path> -b step-<n>` yourself. Use sibling
   folders, for example `../<repo>-step-<n>`.
2. Use the Agent tool for each step, with the same instructions as above.
3. Start a maximum of 4 concurrent calls at a time: one message with a maximum of 4
   parallel tool-use blocks. Wait for that batch.
4. If the group has more steps, dispatch the next batch.

**PG-3: Wait for each step in the group.** A group is a barrier. Do not merge any step
until each step returns a receipt or fails its own Stage 1-5 gate.

A step that fails its gate is blocked. Leave the worktree of that step in place. Do not
merge that step. Obey the Boundaries "Stop and ask" for that step only. The steps that
succeeded still go to PG-4 (merge in step order).

**PG-4: Merge each worktree back in the declared step order.** Do not use the order in
which the steps finish. Make one commit for each step. You compose each commit, not the
subagent. For each step, in ascending step number:

- Apply the diff of the step (from its worktree) onto the plan branch.
- **You** update the tracker, the checkbox, and the Progress log entry of this step in the
  plan file. The subagent did not touch `plan.md`. This division of work is deliberate.
  Stage 6 of each step writes to the same tracker and log region of the plan file. If two
  worktree agents both edit that region, each group gets a conflict on the plan file,
  also when the code is fully disjoint. One serial edit in the main thread prevents that
  conflict.
- Commit with the same Conventional Commits format as Stage 6 of a single step.
- Remove the worktree, and delete its branch.
- **If the diff of a step conflicts with an earlier step in this merge**, the `Touches`
  sets were not disjoint. Do the Stage 1-5 loop of that one step again, sequentially, on
  the current plan branch. Do this retry exactly one time, silently. Log the retry in the
  "Surprises" line of the Progress log entry of that step, but do not stop to ask. If the
  retry fails or conflicts again, that is the Boundaries trigger "two failed attempts".
  Stop and ask.

**PG-5: Report and continue.** Report one status line for each step in the group. Then
continue to the next step or group, with no pause, because each grouped step is AUTO.

---

## ON COMPLETION — squash-merge or PR

When all steps are done (the tracker is at 100%), do these actions:

1. Set the plan header **Status** to `Done`.
2. Move the plan file into a `completed/` folder in its parent folder. For example,
   `plans/<name>.plan.md` becomes `plans/completed/<name>.plan.md`.
3. If `plans/completed/` does not exist, create the folder.
4. If git tracks the plan file, use `git mv`, so that the history follows the move.
5. Update the **Plan location** header field of the plan to the new path.
6. Ask the user:

```
All <N> steps are complete on <branch>. How do you want to finish?

  1. Squash-merge locally  — squash the per-step commits into one on <base>,
                             then delete <branch>.
  2. Open a PR             — push <branch> and open a pull request through gh.
```

**Option 1 — squash-merge locally:**
```bash
git checkout <base>
git merge --squash <branch>
git commit          # compose a summary message from the plan Intent + step list
git branch -D <branch>
```
Show the squash message that you composed. Get a confirmation from the user before you
commit.

**Option 2 — open a PR:**
```bash
git push -u origin <branch>
gh pr create --fill   # title from plan Intent; body = Intent + step summary + plan link
```
If `gh` is missing, push the branch only. Then give the user the compare URL.

Do not merge or push until the user explicitly selects an option. At the end, report the
last commit or the PR URL.

---

## Rules recap (the discipline)

1. **Stages are gates, not steps.** Do not go to the next stage until you can prove that
   the current stage is complete. Do not write implementation before a red test. Do not
   refactor before green. Do not commit before the review.
2. **One commit for each step.** The commit is Stage 6. Update the plan tracker in the
   same commit.
3. **The plan is law.** Intent and Boundaries have priority over your judgement. If there
   is a conflict, stop and ask. Do not resolve the conflict yourself.
4. **Two failed attempts mean that the plan is incorrect**, not that you must try
   harder. Stop and tell the user about the problem (from the Boundaries rule of the
   plan).
5. **Examine, do not assume.** Before you write calls, read the real API and source
   definitions, and the conventions that the plan cites. Run commands to confirm each
   gate. Do not mark a gate as passed from memory.
6. **Obey the gate flag.** GATED steps are a human gate: pause for review after each
   GATED step. AUTO steps report a status of one line and continue with no pause. (On
   2026-07-07, an edit removed the GATED pause, and a correction on the same day put the
   pause back. The GATED pause is the intended behaviour.)
7. **Parallel groups still make one commit for each step, composed by the main thread.**
   Concurrent dispatch changes *who* runs Stages 1-5 (a new agent in its own worktree for
   each step) and *when* the stages run (at the same time). Concurrent dispatch does not
   change the commit discipline. A grouped subagent does not edit the plan file. Only the
   main thread edits the plan file, during the merge-back. A broken independence
   assumption gets exactly one silent sequential retry before it escalates through rule 4
   (two failed attempts).
