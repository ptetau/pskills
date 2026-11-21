# `/quiz-plan-execute`: run a change plan

`/quiz-plan-execute` runs a `.plan.md` file that [`/quiz-plan`](../quiz-plan/README.md)
wrote. It takes each step through a test-first gate of 6 stages, and it makes one commit
per step.

## When to use it

Use it when a `.plan.md` exists and you want disciplined, test-first execution with one
commit per step.

Do not use it in these cases:

- No plan file exists. Run `/quiz-plan` first.
- The change is a trivial fix in 1 file, with nothing to test. Make the change directly.
- You want exploratory work with no commits.

## How to start

```
/quiz-plan-execute plans/add-api-rate-limiting.plan.md
```

The path is optional. Without a path, the skill looks for `plans/*.plan.md` at the project
root. It does not look in `plans/completed/`. With one match, it uses that file. With
several matches, it asks which one. With none, it tells you to run `/quiz-plan` first.

## What happens

1. **Checks.** The skill needs a git repository and a clean working tree. If the tree is
   dirty, it stops and asks you to commit or stash. If `gh` is missing, it warns you that
   the PR option is unavailable.
2. **Read.** It reads the whole plan. It resumes at the first step that the Progress log
   does not mark done. A step with no falsifiable `Done when` makes it stop and ask you to
   fix the criteria.
3. **One question.** It asks whether to create a new branch (`Branch`). Option A creates a
   branch from the current HEAD. Option B stays on the current branch. You can also type
   a branch name. It sets the plan Status to `In progress`.
4. **Each step.** It reports the step and stage, such as `Step 2 · Stage 2/6 (red)`. The
   stages are:
   1. Understand the acceptance criteria (`Done when`).
   2. Red: write a failing test. The test must fail for the right reason.
   3. Green: write the minimum code that passes. All earlier tests must pass too.
   4. Refactor: keep the tests green.
   5. Review: prove that each `Done when` clause is true and that the changed files stay
      inside "May modify".
   6. Commit: run the lint command, update the plan, and commit with the plan file.
5. **After each step.** An AUTO step prints one status line and the skill continues. A
   GATED step stops and waits for your review.
6. **Stop and ask.** The skill stops and asks in these cases:
   - A test you did not expect fails.
   - A change outside "May modify" is needed.
   - A step is ambiguous, or it conflicts with Intent or Boundaries.
   - Two attempts at the same fix fail.
7. **Finish.** See "What it writes" below.

## What it writes

Each step ends in one Conventional Commits commit. Its subject is
`<type>(<scope>): <step name>`, and its last line is `Plan: <plan-file> · Step <n>`. The
same commit updates the plan file:

- The step heading changes from `[ ]` to `[x]`.
- The Progress bar and the `X/N (P%)` count in the header change.
- The Progress log gets an entry with `Changed:`, `Decided:`, and `Surprises:` lines.

When all steps are done, the skill sets Status to `Done`. It moves the plan to
`plans/completed/<name>.plan.md` and updates the Plan location field. Then it asks how to
finish. Option 1 squashes the step commits into one commit on the base branch, after you
confirm the message, and deletes the work branch. Option 2 pushes the branch and runs
`gh pr create --fill`. The skill does not merge or push until you choose.

## Parallel groups

Steps that share a `Parallel group` id (`P1`, `P2`, and so on) run at the same time. Each
step gets one agent in its own git worktree. The skill uses the Workflow tool when the
session has it. Otherwise it creates the worktrees itself and starts at most 4 agents at
once. The agents run stages 1 to 5 only. The main thread then merges the steps in
step order, with one commit per step, and it alone edits the plan file. If two steps
conflict, it runs the second step again once, in order. A second failure stops the run.

## Hand-over from `/quiz-plan`

`/quiz-plan` writes the fields that this skill reads: Do, Done when, Out of scope here,
Touches, Depends on, and Parallel group. The skill never changes Intent or Boundaries.
