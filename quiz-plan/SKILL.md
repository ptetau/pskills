---
name: quiz-plan
description: Interactive quiz-driven planning. Asks structured questions to gather context. Then generates a comprehensive Change Plan document with Intent, Approach, Ground truth, Boundaries, Steps, Verification, and Progress log. Steps declare a `Touches` file footprint and `Depends on` edges, so [[quiz-plan-execute]] can auto-group independent steps for parallel execution. Steps default to AUTO; a step is GATED (human checkpoint) only when the user explicitly asks. Before presenting the draft, the skill red-teams it against its own Boundaries, riskiest assumption, scope, parallel-group correctness, and a failure premortem. Use for any non-trivial code change that needs a clear plan before implementation.
license: MIT license
metadata:
    skill-author: K-Dense Inc.
---

# Quiz Plan

## Overview

This skill runs a conversational interview (quiz) to surface every assumption, ambiguity, and dependency in a proposed change. Then it generates a formal Change Plan document. The quiz is adaptive: it doesn't stop after a fixed set of questions. It keeps drilling until there's nothing left to clarify.

The output is a `.plan.md` file. It holds the structured template from taste (Intent, Ground truth, Boundaries, gated Steps, Verification and rollback). It also holds a **live progress tracker** that shows humans at a glance how far along the plan is.

## When to Use This Skill

Use this skill when:
- Planning a non-trivial code change (3+ files, architectural decision, refactor, new feature)
- The user says `/quiz-plan`, `/quiz`, or asks to "make a plan" or "plan this change"
- A change involves multiple systems, teams, or deployment steps
- You need to document the reasoning and scope before implementing
- A change has rollback risk or the plan needs human sign-off before execution
- There are unclear requirements, hidden assumptions, or ambiguous scope that you need to pin down

Do **not** use for:
- Simple fixes in 1-2 files where the path is obvious
- Pure exploration / understanding questions
- Changes that `git checkout` can safely roll back

## Workflow

The skill has three phases that flow sequentially: the quiz (gather), the plan (draft),
then a red-team pass on the draft before you present it.

### Phase 1: The Adaptive Quiz

Interview the user one question at a time, with the [[quiz]] question UX (see "The look" below). Drill deeper as answers reveal ambiguity. You have a starter question bank below, but the quiz is **not limited to the starter pool**. Each answer may reveal assumptions, ambiguities, or unknowns that need their own follow-up. Keep asking until you can write a complete, unambiguous plan.

#### Starter Question Pool

These are your opening questions: a pool to draw from, **not a script to recite in order**. Skip any that the user's opening statement already answered. Ask each as a quiz question (the same UX as `/quiz`; see "The look" below), **one per turn**. Expect to ask deeper follow-up drill questions (see the next section). Ask those the same way.

**What's the change?** — "Describe the outcome in one sentence."
Captures: core change in plain language. → **Intent**

**Why?** — "What's wrong today? What specific problem are you solving?"
Captures: concrete pain point. → **Intent**

**What files are involved?** — "Which files or packages do you expect to touch? If you know the paths, list them. Otherwise, describe the area of the codebase."
Captures: file paths, modules. → **Ground truth → Key files**

**What's out of bounds?** — "Anything you explicitly don't want changed? Adjacent work to not do here?"
Captures: scope exclusions. → **Intent → Not doing** and **Boundaries → Must not touch**

**What could go wrong?** — "What's the riskiest part — the thing most likely to break or surprise you?"
Captures: riskiest assumption. → **Boundaries → Riskiest assumption**

**Build and test commands?** — "What commands do you use to build, test, and lint? Any special setup?"
Captures: exact commands. → **Ground truth → Build / test / lint**

**Any conventions?** — "Style guides, naming patterns, ADRs, or existing docs (CLAUDE.md) I should read?"
Captures: conventions and reference docs. → **Ground truth → Conventions**

**How will you verify?** — "What will you check to confirm this is complete and correct? Edge cases?"
Captures: verification criteria. → **Verification and rollback**

**Rollback plan?** — "If this goes wrong, how do we undo it? Git revert? Feature flag? DB rollback?"
Captures: rollback strategy. → **Verification and rollback → Rollback**

**Branch name?** — "What branch should this work on? If the branch doesn't exist yet, I can create it."
Captures: branch name. → Document header

**Prior art?** — "Have we built something this shape before — here or elsewhere? Roughly how many steps did it take, and what broke or surprised us last time?"
Captures: closest past change, rough step count, known failure modes. → **Ground truth → Prior art** (and it seeds the Phase 3 premortem)

**More than one way to do this?** — *(ask only when 2+ viable approaches exist)* "Are there competing approaches? Name the front-runners so we pick one deliberately instead of defaulting to the first that came to mind."
Captures: approach options and the reason for the pick. → **Approach**

> The questions are Q1–Q12 in the order listed: Q1 is "What's the change?" and Q12 is "More than one way to do this?". The template below names each one by its number and title, such as "Q4 (What's out of bounds?)". Q12 is conditional: skip it when only one sensible approach exists.

#### Adaptive Follow-up Drill (the key mechanic)

After each answer, **assess whether the answer reveals ambiguity or hidden assumptions.** If it does, keep drilling with follow-up questions. Some examples:

- **If the user says "refactor the auth module"** → "Is this just restructuring internals, or does the public API change too? Are there callers I need to update?"
- **If they say "add a new endpoint"** → "What's the request/response shape? Should it be authenticated? What status codes for success vs error?"
- **If they say "migrate the database"** → "Is this additive (new columns/tables) or destructive (removing/renaming)? Is there a roll-forward-only strategy or do we need a dual-write phase?"
- **If they say "update the config"** → "What's the default value? Is it environment-specific? Will existing deployments need manual migration?"
- **If they say "I'm not sure about X"** → "Let me go look at the current code to find out". Then explore the codebase and report back.

**Signs you need to keep asking:**
- The answer contains words like "probably", "mostly", "should", "I think", "not sure"
- The answer describes an outcome but not the mechanism
- The answer covers the happy path but doesn't address edge cases
- The answer assumes something about the codebase that no one has verified
- You, as the agent, can't yet picture the exact files and changes needed

**Signs you're done asking:**
- Every answer is concrete and unambiguous
- You can describe exactly which files change and how, in implementation detail
- The user has no more "I don't knows" — they're either sure or have explicitly flagged unknowns
- You have followed up and resolved all assumptions from earlier answers
- You can picture a complete, ordered list of implementation steps

#### The look (same as /quiz)

Ask every question, starter and drill follow-up alike, the way [[quiz]] does. Use the
picker (the `AskUserQuestion` tool) when the session has it. Otherwise, ask a
plain-markdown question. No ASCII cards, box-drawing characters or code blocks around
questions or echoes. **One question per message or picker call, always**; never stack
two.

[[quiz]] defines the parts of a question, the recommendation rule, the fallback layout
and the exact echo forms (its Steps 2-5). This skill uses them unchanged, with four
differences:

1. **Adaptive numbering.** The drill is adaptive, so you don't know the total while
   asking. Number questions without a total:
   - the picker question ends with ` (question N)`;
   - the fallback heading reads `**Question N · Label**`;
   - echoes read `✓ N Label → Choice`.

   In the resolved view, once you know the total, number them `N/T`.
2. **No fixed list.** Unlike /quiz's Step 1 (Plan the questions), the list grows: each
   answer can open a follow-up question (see Drill behaviour below).
3. **Open questions** (a sentence, a command, a file path). Ask them in plain prose even
   when the picker exists, in this layout:
   - a heading `**Question N · Label**`;
   - the question;
   - `Reply with <what's needed>.`

   Use the picker only when there are 2-4 real options, such as a branch name you can
   suggest. Never invent options to fill it.
4. **No cap.** Unlike /quiz (about 7, then /squiz), the drill runs until every item in
   "Signs you're done asking" holds.

**Recommendations** follow /quiz's rule, with the codebase counting as evidence. Tag an
option `(recommended)` only when a ground-truth fact, constraint or risk points to it.
Name that fact in the option's why sentence. On a genuine toss-up, recommend nothing.

**Options** follow /quiz's Step 2 (Write each question): a short label, then three short
sentences for what, why and cost.

A fallback question looks like this (render it as markdown, never in a code block):

````markdown
**Question 3 · Location**
Where does the rate-limit middleware live?

- **A · internal/api/middleware/ (recommended)**: The limiter sits next to the existing
  logging middleware. Reviewers know that pattern, and no new package needs wiring in.
  It ties the limiter to that folder's conventions.
- **B · a new top-level package**: The limiter gets its own package, such as
  `pkg/ratelimit/`. That pays off if the limiter grows into a reusable module. It adds
  an import path for a first cut.
- **C · not sure**: I read the code and report back before I pick a location. The
  choice then rests on the code, not on memory. It costs one extra round.

Reply A, B or C, optionally with a note.
````

##### The rhythm (between questions)

After each reply, write its echo line. Then ask the next question in the same message:

```
turn 1 · agent: question 1
turn 2 · user:  "Add rate limiting to the public API routes."
turn 3 · agent: "✓ 1 Change → add rate limiting to public API routes", then question 2
turn 4 · user:  "B, with notes: env-configurable, default 100/min"
turn 5 · agent: "✓ 2 Limit → configurable (note: env var, default 100/min)", then question 3
```

##### Final resolved view (after the drill is exhausted)

When no questions remain, list every answer as a bulleted list of echo lines. Number
them `N/T`, now that you know the total. Put no code block around the list:

- ✓ 1/8 Change → add rate limiting to public API routes
- ✓ 2/8 Limit → configurable (note: env var, default 100/min)
- ✓ 3/8 Location → internal/api/middleware/

Then ask for the go-ahead, which gates Phase 2 (Write the Plan):

- In the picker, ask one `Confirm` question with options `Write the plan` and
  `Change one`. Recommend neither.
- In the fallback, write one line, in these words:
  *"Does this look right? If anything is wrong, say `wait`. Otherwise I'll write the plan."*

##### Reply parsing (same as /quiz)

Read replies and write echoes exactly as [[quiz]]'s Step 4 (Echo each answer) says. This
includes deferrals, notes, free prose and several answers at once. The only difference is
the numbering: echoes read `✓ N Label → Choice` until you know the total.

##### Drill behaviour

1. Use the user's own terms in follow-up questions (mirror their language).
2. **Short/hedged answer → drill deeper.** "Probably" or "I think" means the next
   question follows up on that point.
3. Never argue with scope. Record what the user says; Boundaries will flag the risk.
4. **Drill until clear** (see "Signs you're done asking"). Show the resolved view only
   when no questions remain.
5. If the user revises an earlier answer in the resolved view, update your notes. Check
   whether the revision opens a new question; if it does, ask one more. Don't re-ask
   everything.

### Phase 2: Write the Plan

After the user confirms the quiz, generate a `.plan.md` file inside a `plans/` subfolder at the project root. If `plans/` doesn't exist yet, create it.

#### File name

`plans/<kebab-case-name>.plan.md`

Derive the name from the user's answer to Q1 (What's the change?). For example:
- "Add OAuth login to the API" → `plans/add-oauth-login.plan.md`
- "Refactor the auth middleware" → `plans/refactor-auth-middleware.plan.md`

#### Template

````markdown
# Change Plan: [name derived from Q1 (What's the change?)]

**Owner:** `[current user from git config, or "you"]` · **Status:** Draft | Agreed | In progress | Done
**Branch:** `[from Q10 (Branch name?)]` · **Plan location:** `[path to this file]`
**Progress:** [visual bar] `[X]/[N] steps completed ([P]%)`

## How to use this document (read this first, every session)

You are the agent that executes this plan. Assume you remember nothing from earlier sessions.

1. Read Intent, Ground truth and Boundaries in full. If the plan has an Approach section, read it too.
2. Read the Progress log to find the current state. Don't redo a completed step. Don't reopen a decision that the log records.
3. Resume at the first step not marked done. Respect its gate. If other not-done steps share its `Parallel group` tag, those steps run together. [[quiz-plan-execute]] says how.
4. After each step, append an entry to the Progress log. Then check the step against its `Done when` criteria before you start the next step.
5. If an action would conflict with Intent or Boundaries, stop and ask. Don't resolve the conflict yourself.

## Intent

[From Q2 (Why?): what is wrong today, and what will be different that someone can see]

[From Q4 (What's out of bounds?): what this change leaves out]

**Not doing:** [from Q4 (What's out of bounds?)]

## Approach

**Chosen:** [one line: the approach this plan uses]
**Considered:** [from Q12 (More than one way to do this?): each front-running alternative, and why the plan rejects it. If only one sensible approach exists, leave out this whole section. Don't invent alternatives to look thorough.]

## Ground truth

- **Key files:** [from Q3 (What files are involved?)]
- **Build / test / lint:** [from Q6 (Build and test commands?)]
- **Conventions:** [from Q7 (Any conventions?)]
- **Prior art:** [from Q11 (Prior art?): the closest past change, its rough step count, and what broke last time. Prior art helps set the scope and seeds the Phase 3 premortem. "None known" is a valid answer.]

**Verification rule:** before you call a function, API or library feature not listed above, read its definition. Find the definition in the source or the installed package. Never write a call from memory of how the API "probably" looks. If you can't find the definition, stop and ask.

## Boundaries

- **May modify:** [inferred from Q3 (What files are involved?) and Q4 (What's out of bounds?)]
- **Must not touch:** [from Q4 (What's out of bounds?)]
- **Stop and ask when:**
  - a test you didn't expect fails;
  - a step needs a change outside "May modify";
  - a step's instructions are ambiguous;
  - the same fix has failed twice.

  Two failed attempts mean the plan is wrong. They don't mean you should try harder.
- **Assumptions (re-check every step):** [the new things this plan takes as true. If one of them is false, the plan is invalid. Examples: "the ORM emits one query per row", "the feature flag defaults to off in prod". This list differs from the Verification rule above, which says to read APIs, not guess. It also differs from the single Riskiest assumption below, which drives Step 1. If execution proves an item false, stop and ask. Don't patch around it.]

**Riskiest assumption:** [from Q5 (What could go wrong?)]. Step [1] tests it, so that step comes first.

## Steps

Each step fits in one session. The gates mean:

- **AUTO** (the default): complete the step, then continue unattended.
- **GATED**: complete the step and log it. Then stop and wait for a human review. Use GATED only when the human explicitly asked for a checkpoint on that step.

Each step also declares a **Touches** footprint and **Depends on** edges. [[quiz-plan-execute]] compares them to decide which not-done steps can run together as a **parallel group**, one agent per step. Get them right. If they are wrong, grouping does the wrong thing, and nothing warns you.

[Write the steps for this change. Make each step concrete enough that two readers would make the same change.]

### Step 1: [name] · `[ ]` AUTO | GATED · Parallel group: [none | P1, P2, ...]

- **Do:** [precise instructions]
- **Done when:** [falsifiable criteria]
- **Out of scope here:** [tempting nearby work to leave out]
- **Touches:** [the files or globs this step edits. Never list the plan file itself. Every step's Stage 6 (Commit) edits the plan file, so grouping leaves it out.]
- **Depends on:** [the steps this step needs in order to be correct, even when the `Touches` sets don't overlap. Example: "Step 2", when this step reads a config flag that Step 2 adds. If the step is truly independent, write `none`.]

[Additional steps as needed...]

**Parallel group assignment rule:** two steps may share a group only if both of these hold:

- their `Touches` sets are disjoint;
- neither step is in the other's `Depends on` chain, directly or through other steps.

The step that tests the **Riskiest assumption** never joins a group. That step always runs first, alone. A **GATED** step never joins a group either. A human checkpoint runs alone, so the pause point stays predictable. So every group holds only AUTO steps.

## Verification and rollback

- **Human verifies by:** [from Q8 (How will you verify?)]
- **Failing looks like:** [the signals that mean stop and roll back]
- **Rollback:** [from Q9 (Rollback plan?)]
- **Kill criteria:** [the conditions that make the human abandon this change]

## Progress log

Append one entry per step when the step runs. Don't write entries ahead. Put the newest entry last. This log is the only memory that survives between sessions, so record decisions, not just actions.

```
[date] Step 1: pending | in progress | done | blocked
Changed: [files touched, one line]
Decided: [choices made and why, so the next session doesn't reopen them]
Surprises: [anything that didn't match ground truth or the plan]
```

#### Progress Tracker Maintenance

When you write the plan, make the tracker like this:

```markdown
**Progress:** ████░░░░░░░░ 2/6 steps completed (33%)
```

The bar has exactly 12 characters: █ for done, ░ for remaining. Round the number of █ characters to the nearest whole number. Examples:

- 0/4 steps completed → `░░░░░░░░░░░░ 0/4 (0%)`
- 1/4 steps completed → `███░░░░░░░░░ 1/4 (25%)`
- 2/4 steps completed → `██████░░░░░░ 2/4 (50%)`
- 3/4 steps completed → `█████████░░░ 3/4 (75%)`
- 4/4 steps completed → `████████████ 4/4 (100%)`

When a step runs and gets its Progress log entry, **also update the tracker in the header.** The tracker is for humans. Anyone who opens the `.plan.md` file sees at once how far along the work is.

Also update each step's checkbox: `[ ]` becomes `[x]` when the step is done.
````

#### Step Generation Guidelines

When generating steps from the quiz answers:

1. **Step 1 should always test the riskiest assumption** (from Q5, What could go wrong?). It goes first because, if the assumption fails, the whole plan is invalid. Step 1 never joins a parallel group.
2. Each step should produce a concrete, checkable outcome (a passing test, a rendered route, a working command).
3. **Default every step to AUTO.** Mark a step **GATED** only when the user explicitly asks for a human checkpoint on it. The user may name the step, or give a general instruction such as "gate the risky ones". Apply a general instruction to the specific steps that match. Don't gate by default "to be safe". Unattended AUTO execution end-to-end is the common case, not the exception.
4. If the change involves both infrastructure and code, separate it into logical phases (infrastructure first, then code).
5. If the change spans a backend + frontend, order steps by dependency (backend first if the frontend depends on it).
6. A step should fit in one session. If a step would require 20 file changes, split it further.
7. The last step should always include running the build, test, and lint commands from Q6 (Build and test commands?).
8. **Tracker maintenance is part of each step.** Whenever the agent completes a step, it must also update the progress bar and checkboxes in the plan file header.
9. **Pick the approach before the steps.** If Q12 (More than one way to do this?) surfaced 2+ viable approaches, choose one deliberately. Record the choice, and why the alternatives lost, in the **Approach** section. Then generate steps for the winner only. Don't leave the fork unresolved in the steps.
10. **Assign `Touches` and `Depends on` for every step, then compute parallel groups.** Two AUTO steps may share a group id (`P1`, `P2`, ...) only if all of these hold:
    - neither is the riskiest-assumption step;
    - their `Touches` sets are disjoint;
    - neither depends on the other, directly or transitively.

    Groups need 2+ steps. A step with no groupmate gets `Parallel group: none`. If you're unsure whether two steps are really independent, default to `none` rather than guessing a group. A missed parallel opportunity costs time; a wrong one costs a broken merge.

### Phase 3: Red-team the Draft

Before showing the plan to the user, turn adversarial on your own draft: you wrote it,
now try to break it. Work through each check below. Fix anything you can resolve from the
quiz answers or the codebase. Hold anything you can't resolve as one more quiz question.
Don't silently patch over it or silently drop it.

- **Premortem (the outside-in lens):** assume it's a month later and this plan shipped and
  *failed*. Working backwards, list the likely causes. The Q11 (Prior art?) answer is your
  seed: what broke last time? For each cause, name the step, boundary, or Assumption that
  already defends against it.

  Any cause with no defender is a coverage gap. Add a mitigation step (after Step 1, never
  displacing it) or a stop-condition. The premortem differs from the mechanical checks
  below. They ask "does a step break a rule?"; the premortem asks "what failure isn't
  represented as a step at all?"
- **Riskiest assumption:** does Step 1 actually *test* it (falsifiable, would fail if the
  assumption is wrong), or does it just touch the same area?
- **Boundaries:** does any step's `Do` reach outside `May modify`? Does any step conflict
  with `Must not touch`?
- **Done when:** is each criterion checkable by running a command/test, or is it vague
  ("works correctly", "handles it properly")? Rewrite vague ones concretely.
- **Coverage gaps:** do the quiz answers imply work that no step covers? Examples: a
  migration, a doc update that the Q7 (Any conventions?) answers require, a config change
  for existing deployments.
- **Ordering:** does any step depend on output/state a *later* step creates?
- **Scope creep:** does any step's `Do` include work that Q4 (What's out of bounds?)
  explicitly excluded?
- **Rollback reachability:** if Verification's "Failing looks like" triggers mid-plan (not
  just at the end), is the Rollback from Q9 (Rollback plan?) still executable at that
  point?
- **Parallel groups:** for every declared group, are the `Touches` sets *actually*
  disjoint? Or does file-set diffing miss a real logical dependency between two steps? For
  example, one step reads a flag/schema/contract the other introduces, even in a different
  file. If so, add the missing `Depends on` edge and split the group. Confirm that the
  riskiest-assumption step and every GATED step carry `Parallel group: none`. If either got
  swept into a group by mistake, fix it.

Only once this pass is clean does the plan move to `Draft`, and only then do you present
it. When you present it, add one line that says the red-team pass ran. Name anything it
caught and fixed (or "no issues found"). This line must be visible, not a silent internal
step.

#### Output

After generating the plan and completing the red-team pass, present to the user:
1. The file path of the created plan
2. A one-line summary of each step
3. One line on what the red-team pass caught (or "no issues found")
4. Ask: *"Do you want to start executing this plan?"*

If yes, hand off to [[quiz-plan-execute]]: run `/quiz-plan-execute <path>`. It drives each
step through a strict 6-stage TDD gate (understand → red → green → refactor → review →
commit). It makes one commit per step, with an optional new branch. Steps sharing a
`Parallel group` run concurrently, one agent per step, each in its own worktree. If no, the
plan file stays on disk for later use. The user can run `/quiz-plan-execute` against it any
time.

## Example

**User:** "/quiz-plan I want to add rate limiting to the API"

### Quiz interaction (showing adaptive drilling)

One question per turn, with an echo before the next, exactly like `/quiz`. Shown here in
the fallback layout; with a picker, the same questions arrive as clickable options.

**Agent:**

> **Question 1 · Change**
> In one sentence, what are we changing?
>
> Reply with a sentence.

**User:** "Add rate limiting to the public API routes."

**Agent:**

> ✓ 1 Change → add rate limiting to public API routes
>
> **Question 2 · Risk**
> What's the riskiest part, the one most likely to break?
>
> Reply with a sentence.

**User:** "We accidentally rate-limit our own internal services if they share an IP pool."

**Agent:**

> ✓ 2 Risk → internal services throttled if they share an IP pool
>
> **Question 3 · Location**
> Where does the rate-limit middleware live?
>
> - **A · internal/api/middleware/ (recommended)**: The limiter sits next to the
>   existing logging middleware. Reviewers know that pattern. It ties the limiter to that
>   folder's conventions.
> - **B · a new package**: The limiter gets its own package, such as `pkg/ratelimit/`.
>   Other services can reuse the package later. It adds an import path for a first cut.
> - **C · not sure**: I read the code and report back. The choice then rests on the
>   code, not on memory. It costs one extra round.
>
> Reply A, B or C, optionally with a note.

**User:** "A — there's already a logging-middleware pattern there."

*(The drill continues one question at a time: limit configurable or hardcoded,
must-not-touch, verification, build/test commands, branch, until no ambiguity remains.)*

**Agent:**

> - ✓ 1/8 Change → add rate limiting to public API routes
> - ✓ 2/8 Risk → internal services throttled if the IP pool is shared
> - ✓ 3/8 Location → internal/api/middleware/ (note: there's already a logging-middleware pattern there)
> - ✓ 4/8 Limit → configurable (note: env var, default 100/min)
> - ✓ 5/8 Must-not → auth middleware, private/internal routes
> - ✓ 6/8 Verify → integration test: the 101st rapid request gets 429
> - ✓ 7/8 Commands → `go build ./...` and `go test ./...`
> - ✓ 8/8 Branch → feature/rate-limiting

**Agent:** *"Does this look right? If anything is wrong, say `wait`. Otherwise I'll write the plan."*
**User:** "Looks good."

*(The agent drafts the plan, then red-teams it. The premortem lens surfaces "limiter counts
requests per-replica, so the real limit is N×replicas in prod", and no step defends against
it. So the agent adds a new Assumption, "rate state is per-instance, not shared", for the
executor to re-check. The red-team pass also catches that Step 3's `Done when` said "routes
work correctly". The agent rewrites it. It becomes: "integration test hits a public route
101 times, gets 429 on the 101st, and a whitelisted internal-IP route stays 200 the whole
time.")*

### Generated plan

**File:** `plans/add-api-rate-limiting.plan.md`

**Header excerpt:**
> **Status:** Draft · **Branch:** `feature/rate-limiting`
> **Progress:** ░░░░░░░░░░░░ 0/5 steps completed (0%)

**Steps:**
1. `[ ]` Add rate-limiting library dependency (GATED — verify it builds)
2. `[ ]` Create middleware with IP extraction and configurable limits (GATED — must whitelist internal IPs)
3. `[ ]` Wire middleware into public routes only, exclude auth middleware (GATED)
4. `[ ]` Add integration test: 100 rapid requests → 429 on 101st (GATED)
5. `[ ]` Run full test suite and lint (AUTO)

*After step 1 completes, the header updates to:*
> **Progress:** ██░░░░░░░░░░ 1/5 steps completed (20%)

## Notes

- This skill uses the **same question UX as [[quiz]]**:
  - the picker when there is one, plain markdown otherwise;
  - one question per turn;
  - `✓` echoes;
  - never all questions at once.

  The differences: the drill is adaptive (no total until it's resolved, and no fixed list up front), and there's no ~7-question cap.
- If the user gives minimal answers, keep the plan short. If they give detailed answers, include all details.
- If the user already has a clear idea of the steps, skip to step generation — capture their steps directly.
- Commit the plan file to the repository alongside the code changes, so the plan stays with the branch.
- **Robustness features** (Approach / Prior art / Assumptions, plus the premortem lens in Phase 3) come from evidence-backed planning practice:
  - deliberate approach selection (multi-plan beats first-draft);
  - the outside view (anchor scope to the closest past change);
  - Klein's premortem (imagining failure already happened surfaces ~30% more failure causes than "what might go wrong").

  These features don't overlap, by design. The premortem is **folded into the Phase 3 red-team** as one lens, not a separate section. It hunts failures no step represents, where the other checks hunt rule violations.

  Everything is compatible with [[quiz-plan-execute]]. It parses Intent, Ground truth, Boundaries, Steps (`Done when`, `Touches`, `Depends on`, `Parallel group`), and the Progress log. **Approach** and **Prior art** are read-only context. **Assumptions** live inside Boundaries so that the executor re-checks them every step. The executor re-reads Boundaries per step, but Ground truth only once.
- **Parallel groups** (`Touches` / `Depends on` / `Parallel group`) exist purely so [[quiz-plan-execute]] can safely run independent steps concurrently. `Touches` never lists the plan file itself. Every step's Stage 6 (Commit) writes to the plan file, so listing it would make every step look dependent on every other. If you're in doubt about a dependency that file overlap alone wouldn't reveal, write it into `Depends on`. Don't leave the group assignment to guesswork.
