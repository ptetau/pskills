---
name: quiz-plan
description: Interactive quiz-driven planning. Asks structured questions to get the context. Then writes a full Change Plan document with Intent, Approach, Ground truth, Boundaries, Steps, Verification, and Progress log. Each step declares a `Touches` file footprint and `Depends on` edges. The executor [[quiz-plan-execute]] uses these fields to put independent steps in groups automatically, and to run each group in parallel. Each step is AUTO by default. A step is GATED (a human checkpoint) only when the user explicitly asks for a checkpoint. Before the skill shows the draft, a red-team pass tests the draft against its own Boundaries, riskiest assumption, scope, parallel-group correctness, and a failure premortem. Use for any non-trivial code change that needs a clear plan before the implementation.
license: MIT license
metadata:
    skill-author: K-Dense Inc.
---

# Quiz Plan

## Overview

This skill runs an interview (a quiz) to find each assumption, ambiguity, and dependency
in a proposed change. Then the skill writes a formal Change Plan document. The quiz is
adaptive, so the quiz does not stop after a fixed set of questions. The quiz continues
until nothing remains to clarify.

The output is a `.plan.md` file. The file contains the structured template from taste
(Intent, Ground truth, Boundaries, gated Steps, Verification and rollback). The file also
contains a **live progress tracker**. A human can read the tracker quickly and see how
much of the plan is complete.

## Writing

Write all text to `references/writing-guidelines.md`. This includes the replies to the
user, each question, and each file that this skill writes.

## When to Use This Skill

Use this skill in these conditions:

- You plan a non-trivial code change: 3 or more files, an architectural decision, a
  refactor, or a new feature.
- The user says `/quiz-plan` or `/quiz`, or asks to "make a plan" or "plan this change".
- The change involves more than one system, team, or deployment step.
- You must record the reasons and the scope before you implement the change.
- The change has a rollback risk, or a human must approve the plan before the execution.
- The requirements are not clear, or there are hidden assumptions, or the scope is
  ambiguous. You must make these items exact.

Do **not** use this skill for these items:

- A simple fix in 1-2 files, when the path is obvious.
- Pure exploration, or questions that only ask for understanding.
- A change that you can safely roll back with `git checkout`.

## Workflow

The skill has three phases, in sequence: the quiz (gather), the plan (draft), and a
red-team pass on the draft. The red-team pass occurs before you show the plan.

### Phase 1: The Adaptive Quiz

Interview the user one question at a time, with the question UX of [[quiz]] (see "The
look" below). When an answer shows an ambiguity, drill deeper. The starter question pool
below gives your first questions, but the quiz is **not limited to the starter pool**. An
answer can show assumptions, ambiguities, or unknowns. Each of these items gets its own
follow-up. Continue to ask until you can write a complete plan that is not ambiguous.

#### Starter Question Pool

The questions below are your opening questions. The list is a pool to select from, **not
a script to recite in order**. Skip each question that the opening statement of the user
already answers. Ask each question as a quiz question (the same UX as `/quiz`, see "The
look" below), **one question in each turn**. You will also ask follow-up drill questions
that go deeper (see the next section). Ask the follow-up questions in the same way.

**What is the change?** (Q1) "Describe the outcome in one sentence."
Captures: the core change, in plain language. → **Intent**

**Why?** (Q2) "What is wrong now? Which specific problem does the change solve?"
Captures: the concrete pain point. → **Intent**

**What files are involved?** (Q3) "Which files or packages do you expect to touch? If you
know the paths, list the paths. If not, tell me the area of the codebase."
Captures: the file paths and the modules. → **Ground truth → Key files**

**What is out of bounds?** (Q4) "Is there anything that you explicitly do not want to
change? Is there adjacent work that this change must not do?"
Captures: the scope exclusions. → **Intent → Not doing** and **Boundaries → Must not
touch**

**What could go wrong?** (Q5) "What is the riskiest part: the part that is most likely to
break or to surprise you?"
Captures: the riskiest assumption. → **Boundaries → Riskiest assumption**

**Build and test commands?** (Q6) "Which commands do you use to build, test, and lint? Is
a special setup necessary?"
Captures: the exact commands. → **Ground truth → Build / test / lint**

**Any conventions?** (Q7) "Are there style guides, naming patterns, ADRs, or existing docs
(CLAUDE.md) that you recommend that I read?"
Captures: the conventions and the reference docs. → **Ground truth → Conventions**

**How will you verify?** (Q8) "What will you check to make sure that the
change is complete and correct? Which edge cases are there?"
Captures: the verification criteria. → **Verification and rollback**

**Rollback plan?** (Q9) "If the change fails, how do we undo the change? With a git
revert, a feature flag, or a DB rollback?"
Captures: the rollback strategy. → **Verification and rollback → Rollback**

**Branch name?** (Q10) "Which branch does this work go on? I can create the branch if
necessary."
Captures: the branch name. → Document header

**Prior art?** (Q11) "Did we build something with this shape before, here or in a
different place? About how many steps did it take? What broke or surprised us the last
time?"
Captures: the closest past change, its approximate number of steps, and the known failure
modes. → **Ground truth → Prior art** (the answer also seeds the Phase 3 premortem)

**More than one way to do this?** (Q12) *(ask only when 2 or more viable approaches
exist)* "Are there competing approaches? Name the front-runners, so that we select one
deliberately and do not simply use the first idea that we had."
Captures: the options for the approach, and the reason for the selection. → **Approach**

> Q11 (prior art) and Q12 (other approaches) are **appended**. Thus, Q1 to Q10 (the first
> ten questions) keep their numbers, and the template mapping below stays stable. Q12
> (other approaches) is conditional: skip this question when only one sensible approach
> exists.

#### Adaptive Follow-up Drill (the key mechanic)

After each answer, **examine if the answer shows an ambiguity or a hidden
assumption.** If the answer shows one, continue to drill with follow-up questions. Some
examples:

- **If the user says "refactor the auth module"** → "Is the change only a restructure of
  the internals, or does the public API also change? Are there callers that I must
  update?"
- **If the user says "add a new endpoint"** → "What is the shape of the request and of the
  response? Must the endpoint have authentication? Which status codes are for success,
  and which are for an error?"
- **If the user says "migrate the database"** → "Is the migration additive (new columns
  or tables) or destructive (removed or renamed columns or tables)? Is there a
  roll-forward-only strategy, or must we have a dual-write phase?"
- **If the user says "update the config"** → "What is the default value? Is the value
  specific to an environment? Do the existing deployments need a manual migration?"
- **If the user says "I'm not sure about X"** → "I will read the current code to find the
  answer." Then explore the codebase and report what you find.

**Signs you need to keep asking:**

- The answer contains words like "probably", "mostly", "should", "I think", or "not sure".
- The answer gives an outcome, but not the mechanism.
- The answer covers the happy path, but not the edge cases.
- The answer assumes something about the codebase that you did not confirm.
- You, the agent, cannot see the exact files and the exact changes that are necessary.

**Signs you're done asking:**

- Each answer is concrete and not ambiguous.
- You can say exactly which files change and how they change, at the level of the
  implementation detail.
- The user has no more "I don't knows". The user is sure, or the user explicitly marked
  each unknown.
- You asked a follow-up about each assumption from the earlier answers, and you resolved
  each assumption.
- You can see a complete, ordered list of the implementation steps.

#### The look (same as /quiz)

Ask each question the way that [[quiz]] asks a question. This applies to the starter
questions and to the drill follow-ups. If the session has the picker (the
`AskUserQuestion` tool), use the picker. If not, ask a plain-markdown question. Do not use
ASCII cards, box-drawing characters, or code blocks around the questions or the echoes.

**Ask one question in each message or picker call, always.** Do not put two questions
together.

[[quiz]] gives the parts of a question, the recommendation rule, the fallback layout, and
the exact echo forms (Steps 2-5 of /quiz). This skill uses these items without a change,
with four differences:

1. **Adaptive numbering.** The drill is adaptive, so you do not know the total when you
   ask. Number the questions without a total. The picker question ends with
   ` (question N)`, the fallback heading is `**Question N · Label**`, and each echo is
   `✓ N Label → Choice`. In the resolved view, number the questions `N/T` when you know
   the total.
2. **No fixed list.** Step 1 of /quiz makes a fixed list, but in this skill the list
   becomes longer. Each answer can open a follow-up question (see "Drill behaviour"
   below).
3. **Open questions** (a sentence, a command, or a file path). Ask an open question in
   plain prose, also when the session has the picker. Write a heading
   `**Question N · Label**`, then the question. Then write `Reply with <what's needed>.`
   on the last line. Use the picker only when there are 2-4 real options, for example a
   branch name that you can suggest. Do not invent options to fill the picker.
4. **No cap.** /quiz stops at about 7 questions, and then offers /squiz. In this skill, the
   drill continues until each item in "Signs you're done asking" is true.

**Recommendations** follow the rule of /quiz, and the codebase also counts as evidence.
Tag an option `(recommended)` only when a fact from the ground truth, a constraint, or a
risk points to the option. Name that fact in the sentence of the option. If the options
are equally good, do not recommend an option.

The example below shows a fallback question. Show the question as markdown, not in a
code block:

````markdown
**Question 3 · Location**
Where does the rate-limit middleware live?

- **A · internal/api/middleware/ (recommended)**: sits next to the existing logging
  middleware, so reviewers recognise the pattern and no new package is necessary, but it
  ties the limiter to that folder's conventions.
- **B · a new top-level package**: for example `pkg/ratelimit/`, which is good if the
  limiter becomes a reusable module, but it adds an import path for a first version.
- **C · not sure**: I will read the code and tell you what I find before I select a
  location, but this costs one more round.

Reply A, B, or C. You can add a note.
````

##### The rhythm (between questions)

After each reply, write the echo line of the reply. Then ask the next question in the same
message:

```
turn 1 · agent: question 1
turn 2 · user:  "Add rate limiting to the public API routes."
turn 3 · agent: "✓ 1 Change → add rate limiting to public API routes", then question 2
turn 4 · user:  "B, with notes: env-configurable, default 100/min"
turn 5 · agent: "✓ 2 Limit → configurable (note: env var, default 100/min)", then question 3
```

##### Final resolved view (after the drill is exhausted)

When no questions remain, show each answer as an echo line in a bulleted list. Number the
echo lines `N/T`, because you now know the total. Do not put a code block around the
list:

- ✓ 1/8 Change → add rate limiting to public API routes
- ✓ 2/8 Limit → configurable (note: env var, default 100/min)
- ✓ 3/8 Location → internal/api/middleware/

Then ask the user to confirm. The confirmation is the gate to Phase 2:

- **Picker:** ask one `Confirm` question with the options `Write the plan` and
  `Change one`. Do not recommend an option.
- **Fallback:** write one sentence:
  *"I will write the plan unless you say `wait`."*

##### Reply parsing (same as /quiz)

Read the replies and write the echoes exactly as Step 4 of [[quiz]] tells you. This
includes deferrals, notes, free prose, and more than one answer in a reply. The only
difference is the numbering: each echo is `✓ N Label → Choice` until you know the total.

##### Drill behaviour

1. Use the terms of the user in the follow-up questions (use the same language as the
   user).
2. **If an answer is short or hedged, drill deeper.** If the user says "Probably" or "I
   think", ask the next question about that point.
3. Do not argue about the scope. Record what the user says. The Boundaries section will
   flag the risk.
4. **Drill until the answers are clear** (see "Signs you're done asking"). Show
   the resolved view only when no questions remain.
5. If the user changes an earlier answer in the resolved view, update your notes. Then
   examine if the change opens a new question. If it opens one, ask one more
   question. Do not ask all the questions again.

### Phase 2: Write the Plan

After the user confirms the quiz, write a `.plan.md` file in a `plans/` subfolder at the
project root. If `plans/` does not exist, create it.

#### File name

`plans/<kebab-case-name>.plan.md`

Make the name from the answer of the user to Q1 (the change). For example:

- "Add OAuth login to the API" → `plans/add-oauth-login.plan.md`
- "Refactor the auth middleware" → `plans/refactor-auth-middleware.plan.md`

#### Template

````markdown
# Change Plan: [a name from Q1 (the change)]

**Owner:** `[current user from git config, or "you"]` · **Status:** Draft | Agreed | In progress | Done
**Branch:** `[from Q10]` · **Plan location:** `[path to this file]`
**Progress:** [visual bar] `[X]/[N] steps completed ([P]%)`

## How to use this document (read this first, every session)

You are an agent that executes this plan. Assume that you have no memory of earlier sessions.

1. Read Intent, Ground truth, and Boundaries in full (and Approach, if the plan has it).
2. Read the Progress log to find the current state. Do not do a completed step again. Do not reopen a decision that the log records.
3. Resume at the first step that is not marked done. Obey the gate of that step. If the step has a `Parallel group` tag that other not-done steps share, those steps run together (see [[quiz-plan-execute]]).
4. After each step, add an entry to the Progress log. Then, before you continue, examine the step against its done criteria.
5. If an action that you plan conflicts with Intent or Boundaries, stop and ask. Do not resolve the conflict yourself.

## Intent

[From Q2 (the problem): what is wrong now, and what will be different that a person can observe]

[From Q4 (out of bounds): the scope exclusions]

**Not doing:** [from Q4 (out of bounds)]

## Approach

**Chosen:** [one line: the approach that this plan implements]
**Considered:** [from Q12 (other approaches): the front-running alternatives, and why you rejected each one. If only one sensible approach existed, omit this full section. Do not invent alternatives to look thorough.]

## Ground truth

- **Key files:** [from Q3 (the files)]
- **Build / test / lint:** [from Q6 (the commands)]
- **Conventions:** [from Q7 (the conventions)]
- **Prior art:** [from Q11 (prior art): the closest past change, its approximate number of steps, and what broke the last time. This item helps to set the scope, and it seeds the Phase 3 premortem. "None known" is a valid answer.]

**Verification rule:** before you call a function, an API, or a library feature that is not listed above, find its actual definition. Read the definition in the source or in the installed package. Do not write a call from your memory of what the API "probably" looks like. If you cannot find the definition, stop and ask.

## Boundaries

- **May modify:** [inferred from Q3 (the files) and Q4 (out of bounds)]
- **Must not touch:** [from Q4 (out of bounds)]
- **Stop and ask when:** a test you didn't expect fails, a change is necessary outside "may modify", or the instructions of a step are ambiguous. Also stop and ask when you tried the same fix two times without success. Two failed attempts mean that the plan is wrong, not that more effort is necessary.
- **Assumptions (re-check every step):** [the novel things that this plan takes as true. If one of these things is false, the plan is not valid. For example: "the ORM emits one query per row", or "the feature flag defaults off in prod". These items are different from the Verification rule above (read the APIs, do not guess), and from the single Riskiest assumption below (which drives Step 1). If the execution shows that an item here is false, stop and ask. Do not add a workaround.]

**Riskiest assumption:** [from Q5 (the riskiest part)]. Step [1] tests this assumption, so step [1] comes first.

## Steps

Each step has a size that fits in one session. The gates have these meanings. **AUTO**
(the default) means complete the step and continue without a human. **GATED** means
complete the step, log it, then stop and wait for a human review. Use GATED only when the
human explicitly asked for a checkpoint on that step.

Each step also declares a **Touches** footprint and **Depends on** edges. These fields are
not decoration. [[quiz-plan-execute]] diffs these fields to decide which not-done steps can
run as a **parallel group** (concurrent agents, one for each step). If the fields are
incorrect, the grouping does the wrong thing, and nothing shows the error.

[Make the steps for the change. Try to make each step concrete enough that two different readers produce the same change.]

### Step 1: [name] · `[ ]` AUTO | GATED · Parallel group: [none | P1, P2, ...]

- **Do:** [precise instructions]
- **Done when:** [falsifiable criteria]
- **Out of scope here:** [tempting adjacent work to exclude]
- **Touches:** [the files or globs that this step actually edits. Do not include the plan
  file. Stage 6 of each step touches the plan file, so the grouping comparisons exclude
  the plan file on purpose.]
- **Depends on:** [the numbers of the steps that the correctness of this step relies on,
  also when the `Touches` sets do not overlap. For example, "Step 2" if this step reads a
  config flag that Step 2 adds. Write `none` if the step is really independent.]

[Add more steps as necessary...]

**Parallel group assignment rule:** two steps are permitted to share a group only if
their `Touches` sets are disjoint **and** neither step depends on the other, directly or
transitively. The step that tests the **Riskiest assumption** does not join a group. That step
always runs alone, first. Any step marked **GATED** also does not join a group. An explicit
human checkpoint runs alone, so that the pause point stays predictable. Thus, each group
contains only AUTO steps.

## Verification and rollback

- **Human verifies by:** [from Q8 (the verification)]
- **Failing looks like:** [the signals that mean stop and roll back]
- **Rollback:** [from Q9 (the rollback)]
- **Kill criteria:** [the conditions in which the human abandons this change]

## Progress log

The log has one entry for each step. Add each entry at execution time, not before. The newest entry is last. This log is the only memory that survives between sessions, so record the decisions, not only the actions.

```
[date] Step 1: pending | in progress | done | blocked
Changed: [the files that you touched, in one line]
Decided: [the choices that you made and why, so that the next session does not argue them again]
Surprises: [each thing that did not match the ground truth or the plan]
```

#### Progress Tracker Maintenance

When you write the plan, make the tracker like this:

```markdown
**Progress:** ████░░░░░░░░ 2/6 steps completed (33%)
```

The bar has exactly 12 characters (█ for done, ░ for remaining). When N is not evenly
divisible by 12, round to the nearest character. Examples:

- 0/4 steps completed → `░░░░░░░░░░░░ 0/4 (0%)`
- 1/4 steps completed → `███░░░░░░░░░ 1/4 (25%)`
- 2/4 steps completed → `██████░░░░░░ 2/4 (50%)`
- 3/4 steps completed → `█████████░░░ 3/4 (75%)`
- 4/4 steps completed → `████████████ 4/4 (100%)`

When you execute a step and log the step in the Progress log, **also update the tracker in
the header.** The tracker is for humans. Thus, a person who opens the `.plan.md` file sees
immediately how much of the work is complete.

Try to also update the checkbox of each step from `[ ]` to `[x]` when the step is complete.
````

#### Step Generation Guidelines

When you make the steps from the quiz answers, obey these rules:

1. **Always try to make Step 1 test the riskiest assumption**, from Q5 (the riskiest
   part). This step goes first, because if this step fails, the full plan is not valid.
   Step 1 does not join a parallel group.
2. Try to give each step a concrete outcome that you can check. Examples are a passing
   test, a rendered route, and a working command.
3. **Default every step to AUTO.** Mark a step **GATED** only when the user explicitly
   asks for a human checkpoint on that step. The user can name the step, or give a general
   instruction, for example "gate the risky ones". Apply that instruction to the steps
   that match. Do not gate a step by default "to be safe". The default changed because
   unattended AUTO execution from start to end is now the common case, not the exception.
4. If the change involves infrastructure and code, divide the steps into logical phases:
   infrastructure first, then code.
5. If the change involves a backend and a frontend, put the steps in the order of their
   dependencies. For example, put the backend first if the frontend depends on the
   backend.
6. Try to make each step fit in one session. If a step needs 20 file changes, split the
   step again.
7. Always try to include a run of the build, test, and lint commands from Q6 (the
   commands) in the last step.
8. **Tracker maintenance is part of each step.** When a step is complete, the agent must
   also update the progress bar and checkboxes in the plan file header.
9. **Select the approach before the steps.** If Q12 (other approaches) found 2 or more
   viable approaches, select one deliberately. In the **Approach** section, record the
   selection and why the alternatives lost. Then make steps only for the selected
   approach. Do not leave the fork unresolved in the steps.
10. **Give `Touches` and `Depends on` to each step, then calculate the parallel groups.**
    Two AUTO steps share a group id (`P1`, `P2`, ...) only if these conditions are
    true:
    - The riskiest-assumption step is not one of the two steps.
    - The `Touches` sets of the two steps are disjoint.
    - The two steps do not depend on each other, directly or transitively.

    A group contains 2 or more steps. A step with no groupmate gets `Parallel group: none`.
    If you are not sure that two steps are independent, use `none`, and do not guess a
    group. A missed parallel opportunity costs time, but an incorrect group costs a broken
    merge.

### Phase 3: Red-team the Draft

Before you show the plan to the user, attack your own draft. You wrote the draft, so now
try to break the draft. Do each check below. If the quiz answers or the codebase can
resolve a problem, correct the problem. If you cannot resolve a problem, keep the problem
as one more quiz question. Do not hide the problem with a silent patch, and do not
silently drop the problem.

- **Premortem (the outside-in lens):** assume that it is one month later, and that this
  plan shipped and *failed*. Work backwards and list the likely causes. Use the Q11 (prior
  art) answer as your seed: what broke the last time? For each cause, name the step, the
  boundary, or the Assumption that already defends against the cause. A cause with no
  defender is a coverage gap. For each gap, add a mitigation step (after Step 1, not in
  place of Step 1) or a stop-condition.

  This lens is different from the mechanical checks below. The mechanical checks ask
  "does a step break a rule?". The premortem asks "what failure is not represented as a
  step at all?"
- **Riskiest assumption:** does Step 1 actually *test* the assumption with a falsifiable
  test (the test fails if the assumption is incorrect)? Or does Step 1 only touch the same
  area?
- **Boundaries:** does the `Do` of any step go outside `May modify`? Does any step conflict
  with `Must not touch`?
- **Done when:** can you check each criterion with a command or a test? Or is the
  criterion vague ("works correctly", "handles it properly")? Write each vague criterion
  again in concrete terms.
- **Coverage gaps:** do the quiz answers imply work that no step covers? Examples are a
  migration, a doc update that Q7 (the conventions) makes necessary, or a config change
  for the existing deployments.
- **Ordering:** does any step depend on an output or a state that a *later* step creates?
- **Scope creep:** does the `Do` of any step include work that Q4 (out of bounds) explicitly
  excluded?
- **Rollback reachability:** the "Failing looks like" signals of Verification can occur
  in the middle of the plan, not only at the end. At that point, can you still execute the
  Rollback from Q9 (the rollback)?
- **Parallel groups:** for each declared group, are the `Touches` sets *actually*
  disjoint? Or does the comparison of file sets miss a real logical dependency between two
  steps? For example, one step reads a flag, a schema, or a contract that the other step
  adds, also in a different file. If so, add the missing `Depends on` edge and split the
  group. Make sure that the riskiest-assumption step and each GATED step have
  `Parallel group: none`. If a group includes one of these steps by mistake, correct the
  group.

The plan moves to `Draft`, and you show the plan, only when this pass is clean. When you
show the plan, add one line that says that the red-team pass ran. The line names each
problem that the pass found and corrected, or says "no issues found". The user must see
this line, because the red-team pass is not a silent internal step.

#### Output

After you write the plan and complete the red-team pass, show these items to the user:

1. The file path of the plan.
2. A summary of one line for each step.
3. One line about what the red-team pass found (or "no issues found").
4. Ask: *"Do you want to execute this plan now?"*

If the user says yes, give the plan to [[quiz-plan-execute]]: run
`/quiz-plan-execute <path>`. That skill moves each step through a strict 6-stage TDD gate
(understand → red → green → refactor → review → commit). The executor makes one commit
for each step, and it can create a new branch. Steps that share a `Parallel group` run
concurrently, with one agent for each step, and each agent in its own worktree. If the
user says no, the plan file stays on the disk for later use. The user can run
`/quiz-plan-execute` on the plan file later.

## Example

**User:** "/quiz-plan I want to add rate limiting to the API"

### Quiz interaction (adaptive drilling)

The agent asks one question in each turn, and writes an echo before the next question,
exactly like `/quiz`. This example uses the fallback layout. With a picker, the same
questions show as options that the user clicks.

**Agent:**

> **Question 1 · Change**
> In one sentence, what is the change?
>
> Reply with a sentence.

**User:** "Add rate limiting to the public API routes."

**Agent:**

> ✓ 1 Change → add rate limiting to public API routes
>
> **Question 2 · Risk**
> What is the riskiest part: the part that is most likely to break?
>
> Reply with a sentence.

**User:** "We accidentally rate-limit our own internal services if they share an IP pool."

**Agent:**

> ✓ 2 Risk → internal services throttled if they share an IP pool
>
> **Question 3 · Location**
> Where does the rate-limit middleware live?
>
> - **A · internal/api/middleware/ (recommended)**: sits next to the existing logging
>   middleware, so reviewers recognise the pattern, but it ties the limiter to that
>   folder's conventions.
> - **B · a new package**: for example `pkg/ratelimit/`, which you can use again later,
>   but it adds an import path for a first version.
> - **C · not sure**: I will read the code and tell you what I find, but this costs one
>   more round.
>
> Reply A, B, or C. You can add a note.

**User:** "A — there's already a logging-middleware pattern there."

*(The drill continues with one question at a time until no ambiguity remains: a
configurable or a hardcoded limit, must-not-touch, verification, the build and test
commands, and the branch.)*

**Agent:**

> - ✓ 1/8 Change → add rate limiting to public API routes
> - ✓ 2/8 Risk → internal services throttled if the IP pool is shared
> - ✓ 3/8 Location → internal/api/middleware/ (note: there's already a logging-middleware pattern there)
> - ✓ 4/8 Limit → configurable (note: env var, default 100/min)
> - ✓ 5/8 Must-not → auth middleware, private/internal routes
> - ✓ 6/8 Verify → integration test: the 101st rapid request gets 429
> - ✓ 7/8 Commands → `go build ./...` and `go test ./...`
> - ✓ 8/8 Branch → feature/rate-limiting

**Agent:** *"I will write the plan unless you say `wait`."*
**User:** "Looks good."

*(The agent drafts the plan, and then does the red-team pass. The premortem lens finds a
cause that no step defends against: "the limiter counts requests per replica, so the real
limit in prod is N×replicas". Thus, the agent adds a new Assumption, "the rate state is
per instance, not shared", for the executor to re-check. The pass also finds that the
`Done when` of Step 4 said "routes work correctly". The agent writes that criterion again
as "an integration test sends 101 requests to a public route and gets 429 on the 101st,
and a whitelisted internal-IP route stays 200 for the full test.")*

### Generated plan

**File:** `plans/add-api-rate-limiting.plan.md`

**Header excerpt:**
> **Status:** Draft · **Branch:** `feature/rate-limiting`
> **Progress:** ░░░░░░░░░░░░ 0/5 steps completed (0%)

**Steps:**
1. `[ ]` Add the rate-limiting library, and test whether internal services on a shared IP pool get throttled (AUTO: tests the riskiest assumption)
2. `[ ]` Create the middleware with IP extraction and configurable limits (AUTO: must whitelist internal IPs)
3. `[ ]` Connect the middleware to the public routes only, and exclude the auth middleware (AUTO)
4. `[ ]` Add an integration test: 100 rapid requests → 429 on the 101st (AUTO)
5. `[ ]` Run the full test suite and lint (AUTO)

*After step 1 is complete, the header changes to:*
> **Progress:** ██░░░░░░░░░░ 1/5 steps completed (20%)

## Notes

- This skill uses the **same question UX as [[quiz]]**. The skill uses the picker if the
  session has one, and plain markdown if not. The skill asks one question in each turn,
  and writes `✓` echoes. The skill does not show all the questions at the same time.
  There are two differences: the drill is adaptive (no total until the drill is resolved,
  and no fixed list at the start), and there is no cap of about 7 questions.
- If the user gives minimal answers, keep the plan short. If the user gives detailed
  answers, include all the details.
- If the user already has a clear idea of the steps, go directly to the step generation.
  Capture the steps of the user directly.
- Try to commit the plan file to the repository together with the code changes. Thus,
  the plan stays with the branch.
- **Robustness additions** (Approach, Prior art, Assumptions, and the premortem lens in
  Phase 3) come from evidence-backed planning practice. The practices are a deliberate
  selection of the approach (multi-plan beats first-draft), the outside view (set the
  scope from the closest past change), and Klein's premortem. The premortem imagines that
  the failure already occurred, and so finds about 30% more failure causes than "what
  might go wrong". By design, the additions do not overlap. The premortem is
  **folded into the Phase 3 red-team** as one lens, not a separate section. The premortem
  looks for failures that no step represents, and the other checks look for rule
  violations.
- All of these additions are compatible with [[quiz-plan-execute]]. That skill parses
  Intent, Ground truth, Boundaries, Steps (`Done when`, `Touches`, `Depends on`,
  `Parallel group`), and the Progress log. The new **Approach** and **Prior art** are
  read-only context. The **Assumptions** are in Boundaries on purpose, so that the
  executor re-checks them at each step. The executor reads Boundaries again for each
  step, but reads Ground truth only one time.
- **Parallel groups** (`Touches` / `Depends on` / `Parallel group`) exist only so that
  [[quiz-plan-execute]] can safely run independent steps concurrently. `Touches` does not
  list the plan file. Stage 6 of each step writes to the plan file. Thus, if `Touches`
  included the plan file, each step would look dependent on each other step. If you are
  not sure about a dependency that file overlap alone does not show, write the dependency
  in `Depends on`. Do not guess the group assignment.
