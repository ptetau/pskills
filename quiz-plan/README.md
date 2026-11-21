# `/quiz-plan`: write a change plan

`/quiz-plan` interviews you about a code change, one question at a time. Then it writes a
Change Plan file, `plans/<name>.plan.md`, that an agent or a person can follow step by
step.

## When to use it

Use `/quiz-plan` for a change that needs a plan before the work starts. Examples are a
change in 3 or more files, an architecture decision, a refactor, a new feature, or a change
with a rollback risk. Use it also when the requirements are vague.

Do not use it in these cases:

- The fix is simple, in 1 or 2 files, and the path is obvious. Make the change directly.
- You only explore or ask a question. Ask the question in the chat.
- Git can undo the change safely with `git checkout`.
- You have a plan and want to run it. Use [`/quiz-plan-execute`](../quiz-plan-execute/README.md).
- You need 1 to 7 quick questions and no plan file. Use [`/quiz`](../quiz/README.md).

## How to start

```
/quiz-plan add rate limiting to the public API routes
```

Say the change in your own words. `/quiz-plan` skips each question that your request
already answers.

## What happens

1. **Quiz.** `/quiz-plan` asks one question per message. It picks from a pool of starter
   questions. They cover the change, the reason, the files, and what is out of bounds. They
   also cover the riskiest part, the build, test, and lint commands, the conventions,
   how you verify, the rollback, and the branch name. It also asks for prior art (a similar past change). It
   asks which approach to use only when 2 or more approaches are viable.
2. **Drill.** When an answer is hedged ("probably", "I think", "not sure"), `/quiz-plan`
   asks a follow-up. If you say "not sure", it reads the code and reports what it finds.
   The quiz has no fixed length. It ends when each answer is concrete.
3. **Confirm.** `/quiz-plan` lists your answers as `✓ N/T Label → Choice`. With the
   picker, you choose `Write the plan` or `Change one`. Without the picker, it writes the
   plan unless you reply `wait`. You can change an earlier answer here.
4. **Write.** `/quiz-plan` creates `plans/` at the project root if it does not exist. It
   writes `plans/<kebab-case-name>.plan.md`, with the name taken from your answer to the
   first question. For example, "Add OAuth login to the API" becomes
   `plans/add-oauth-login.plan.md`.
5. **Red-team.** Before you see the plan, `/quiz-plan` attacks its own draft. It runs a
   premortem and checks the riskiest assumption, the Boundaries, each `Done when`,
   coverage gaps, step order, scope creep, rollback, and the parallel groups. It fixes
   what it can. It asks you about what it cannot fix.
6. **Show.** It shows the file path and one line per step. It adds one line on what the
   red-team pass found. Then it asks "Do you want to execute this plan now?" If you say yes,
   it runs `/quiz-plan-execute <path>`. If you say no, the file stays on disk.

## What the plan looks like

The file starts with a header: Owner, Status (`Draft`, `Agreed`, `In progress`, or
`Done`), Branch, Plan location, and a 12-character Progress bar. A section "How to use this
document" follows. It tells an agent with no memory how to resume the plan. Then these
sections come, in this order:

- **Intent**: the problem, what will differ afterwards, and **Not doing**.
- **Approach**: the chosen approach and the rejected ones. The skill omits it when only one
  approach exists.
- **Ground truth**: Key files, Build / test / lint, Conventions, and Prior art.
- **Boundaries**: May modify, Must not touch, Stop and ask when, Assumptions, and
  Riskiest assumption.
- **Steps**: each step has a heading such as
  `### Step 1: <name> · [ ] AUTO · Parallel group: none`. Fields: Do, Done when, Out of
  scope here, Touches, and Depends on.
- **Verification and rollback**: Human verifies by, Failing looks like, Rollback, and
  Kill criteria.
- **Progress log**: one entry per step, written at execution time.

Step 1 tests the riskiest assumption. Every step is AUTO unless you ask for a checkpoint
on it. A GATED step pauses the executor for your review.

## Hand-over to `/quiz-plan-execute`

`/quiz-plan-execute` reads this file. It uses these fields:

- **Done when** is the acceptance criterion of the step.
- **Touches** lists the files that the step edits. It never lists the plan file.
- **Depends on** lists the steps that must come first, even if their files do not overlap.
- **Parallel group** (`P1`, `P2`, and so on, or `none`) marks AUTO steps that can run at
  the same time. A group needs disjoint `Touches` sets and no dependency between its
  steps. The riskiest-assumption step and each GATED step never join a group.

The executor moves a finished plan to `plans/completed/`.
