---
name: quiz-plan
description: Interactive quiz-driven planning. Asks structured questions to gather context, then generates a comprehensive Change Plan document with Intent, Approach, Ground truth, Boundaries, Steps, Verification, and Progress log. Steps declare a `Touches` file footprint and `Depends on` edges so independent steps can be auto-grouped for parallel execution by [[quiz-plan-execute]]. Steps default to AUTO — a step is only GATED (human checkpoint) when explicitly requested. The draft is red-teamed against its own Boundaries, riskiest assumption, scope, parallel-group correctness, and a failure premortem before being presented. Use for any non-trivial code change that needs a clear plan before implementation.
license: MIT license
metadata:
    skill-author: K-Dense Inc.
---

# Quiz Plan

## Overview

This skill runs a conversational interview (quiz) to surface every assumption, ambiguity, and dependency in a proposed change, then generates a formal Change Plan document. The quiz is adaptive — it doesn't stop after a fixed set of questions. It keeps drilling until there's nothing left to clarify.

The output is a `.plan.md` file containing the structured template from taste (Intent, Ground truth, Boundaries, gated Steps, Verification and rollback) plus a **live progress tracker** that humans can read at a glance to see how far along the plan is.

## When to Use This Skill

Use this skill when:
- Planning a non-trivial code change (3+ files, architectural decision, refactor, new feature)
- The user says `/quiz-plan`, `/quiz`, or asks to "make a plan" or "plan this change"
- A change involves multiple systems, teams, or deployment steps
- You need to document the reasoning and scope before implementing
- A change has rollback risk or the plan needs human sign-off before execution
- There are unclear requirements, hidden assumptions, or ambiguous scope that needs to be pinned down

Do **not** use for:
- Simple fixes in 1-2 files where the path is obvious
- Pure exploration / understanding questions
- Changes that can be safely rolled back with `git checkout`

## Workflow

The skill has three phases that flow sequentially: the quiz (gather), the plan (draft),
then a red-team pass on the draft before it's presented.

### Phase 1: The Adaptive Quiz

Interview the user one question at a time (the [[quiz]] question UX — see "The look" below), drilling deeper as answers reveal ambiguity. You have a starter question bank below, but the quiz is **not limited to the starter pool**. Each answer may reveal assumptions, ambiguities, or unknowns that need their own follow-up. Keep asking until you can write a complete, unambiguous plan.

#### Starter Question Pool

These are your opening questions — a pool to draw from, **not a script to recite in order**. Skip any that the user's opening statement already answered. Ask each as a quiz question (the same UX as `/quiz` — see "The look" below), **one per turn**. Expect to ask follow-up drill questions (see next section) that go deeper — those are asked the same way.

**What's the change?** — "Describe the outcome in one sentence."
Captures: core change in plain language. → **Intent**

**Why?** — "What's wrong today? What specific problem are you solving?"
Captures: concrete pain point. → **Intent**

**What files are involved?** — "Which files or packages do you expect to touch? List paths if you know them, or describe the area of the codebase."
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

**Branch name?** — "What branch should this work on? I can create it if needed."
Captures: branch name. → Document header

**Prior art?** — "Have we built something this shape before — here or elsewhere? Roughly how many steps did it take, and what broke or surprised us last time?"
Captures: closest past change, rough step count, known failure modes. → **Ground truth → Prior art** (and it seeds the Phase 3 premortem)

**More than one way to do this?** — *(ask only when 2+ viable approaches exist)* "Are there competing approaches? Name the front-runners so we pick one deliberately instead of defaulting to the first that came to mind."
Captures: approach options and the reason for the pick. → **Approach**

> Q11 and Q12 are **appended** — Q1–Q10 keep their numbers so the template mapping below stays stable. Q12 is conditional: skip it when only one sensible approach exists.

#### Adaptive Follow-up Drill (the key mechanic)

After each answer, **assess whether the answer reveals ambiguity or hidden assumptions.** If it does, keep drilling with follow-up questions. Some examples:

- **If the user says "refactor the auth module"** → "Is this just restructuring internals, or does the public API change too? Are there callers I need to update?"
- **If they say "add a new endpoint"** → "What's the request/response shape? Should it be authenticated? What status codes for success vs error?"
- **If they say "migrate the database"** → "Is this additive (new columns/tables) or destructive (removing/renaming)? Is there a roll-forward-only strategy or do we need a dual-write phase?"
- **If they say "update the config"** → "What's the default value? Is it environment-specific? Will existing deployments need manual migration?"
- **If they say "I'm not sure about X"** → "Let me go look at the current code to find out" — then explore the codebase and report back.

**Signs you need to keep asking:**
- The answer contains words like "probably", "mostly", "should", "I think", "not sure"
- The answer describes an outcome but not the mechanism
- The answer covers the happy path but doesn't address edge cases
- The answer assumes something about the codebase that hasn't been verified
- You, as the agent, can't yet picture the exact files and changes needed

**Signs you're done asking:**
- Every answer is concrete and unambiguous
- You can describe exactly which files change and how, in implementation detail
- The user has no more "I don't knows" — they're either sure or have explicitly flagged unknowns
- All assumptions from earlier answers have been followed up and resolved
- You can picture a complete, ordered list of implementation steps

#### The look (same as /quiz)

Ask every question, starter and drill follow-up alike, the way [[quiz]] does: through
the picker (the `AskUserQuestion` tool) when the session has it, and as a plain-markdown
question otherwise. No ASCII cards, box-drawing characters or code blocks around
questions or echoes. **One question per message or picker call, always**; never stack
two.

[[quiz]] defines the parts of a question, the recommendation rule, the fallback layout
and the exact echo forms (its Steps 2-5). This skill uses them unchanged, with four
differences:

1. **Adaptive numbering.** The drill is adaptive, so the total isn't known while asking.
   Number questions without a total: the picker question ends with ` (question N)`, the
   fallback heading reads `**Question N · Label**`, and echoes read `✓ N Label → Choice`.
   In the resolved view, number them `N/T` once the total is known.
2. **No fixed list.** Unlike /quiz's Step 1, the list grows: each answer can open a
   follow-up question (see Drill behaviour below).
3. **Open questions** (a sentence, a command, a file path). Ask them in plain prose
   even when the picker exists: a heading `**Question N · Label**`, the question, then
   `Reply with <what's needed>.` Use the picker only when there are 2-4 real options,
   such as a branch name you can suggest; never invent options to fill it.
4. **No cap.** Unlike /quiz (about 7, then /squiz), the drill runs until every item in
   "Signs you're done asking" holds.

**Recommendations** follow /quiz's rule, with the codebase counting as evidence: tag an
option `(recommended)` only when a ground-truth fact, constraint or risk points to it,
and name that fact in its sentence. On a genuine toss-up, recommend nothing.

A fallback question looks like this (render it as markdown, never in a code block):

````markdown
**Question 3 · Location**
Where does the rate-limit middleware live?

- **A · internal/api/middleware/ (recommended)**: sits next to the existing logging
  middleware, so reviewers recognise the pattern and no new package needs wiring in; it
  ties the limiter to that folder's conventions.
- **B · a new top-level package**: e.g. `pkg/ratelimit/`, worth it if this grows into a
  reusable module; it adds an import path for a first cut.
- **C · not sure**: I'll read the code and report back before locking a location; it
  costs one extra round.

Reply A, B or C, optionally with a note.
````

##### The rhythm (between questions)

After each reply, write its echo line, then ask the next question in the same message:

```
turn 1 · agent: question 1
turn 2 · user:  "Add rate limiting to the public API routes."
turn 3 · agent: "✓ 1 Change → add rate limiting to public API routes", then question 2
turn 4 · user:  "B, with notes: env-configurable, default 100/min"
turn 5 · agent: "✓ 2 Limit → configurable (note: env var, default 100/min)", then question 3
```

##### Final resolved view (after the drill is exhausted)

When no questions remain, list every answer as a bulleted list of echo lines, numbered
`N/T` now that the total is known, with no code block around it:

- ✓ 1/8 Change → add rate limiting to public API routes
- ✓ 2/8 Limit → configurable (note: env var, default 100/min)
- ✓ 3/8 Location → internal/api/middleware/

Then ask for the go-ahead, which gates Phase 2: in the picker, one `Confirm` question
with options `Write the plan` and `Change one`, neither recommended; in the fallback,
one sentence:
*"Does this look right? Say `wait` if anything's wrong, otherwise I'll write the plan."*

##### Reply parsing (same as /quiz)

Read replies and write echoes exactly as [[quiz]]'s Step 4 says, including deferrals,
notes, free prose and several answers at once. The only difference is the numbering:
echoes read `✓ N Label → Choice` until the total is known.

##### Drill behaviour

1. Use the user's own terms in follow-up questions (mirror their language).
2. **Short/hedged answer → drill deeper.** "Probably" or "I think" means the next
   question follows up on that point.
3. Never argue with scope. Record what the user says; Boundaries will flag the risk.
4. **Drill until clear** (see "Signs you're done asking"). Show the resolved view only
   when no questions remain.
5. If the user revises an earlier answer in the resolved view, update your notes and
   check whether the revision opens a new question (ask one more if so). Don't re-ask
   everything.

### Phase 2: Write the Plan

After the quiz is confirmed, generate a `.plan.md` file inside a `plans/` subfolder at the project root (create `plans/` if it doesn't already exist).

#### File name

`plans/<kebab-case-name>.plan.md`

Derive the name from the user's description of Q1. For example:
- "Add OAuth login to the API" → `plans/add-oauth-login.plan.md`
- "Refactor the auth middleware" → `plans/refactor-auth-middleware.plan.md`

#### Template

```markdown
# Change Plan: [name derived from Q1]

**Owner:** `[current user from git config, or "you"]` · **Status:** Draft | Agreed | In progress | Done
**Branch:** `[from Q10]` · **Plan location:** `[path to this file]`
**Progress:** [visual bar] `[X]/[N] steps completed ([P]%)`

## How to use this document (read this first, every session)

You are an agent executing this plan. Assume you have no memory of previous sessions.

1. Read Intent, Ground truth, and Boundaries in full (plus Approach, if present).
2. Read the Progress log to find the current state. Do not redo completed steps or reopen decisions recorded there.
3. Resume at the first step not marked done. Respect its gate. If it carries a `Parallel group` tag shared with other not-done steps, those run together — see [[quiz-plan-execute]].
4. After each step: append to the Progress log, then self-assess against the step's done criteria before moving on.
5. If anything you're about to do conflicts with Intent or Boundaries, stop and ask. Do not resolve the conflict yourself.

## Intent

[From Q2 — what's wrong and what will be observably different]

[From Q4 — scope exclusions]

**Not doing:** [from Q4]

## Approach

**Chosen:** [one line — the approach this plan implements]
**Considered:** [from Q12 — the front-running alternatives and why each was rejected. Omit this whole section if only one sensible approach existed; don't invent alternatives to look thorough.]

## Ground truth

- **Key files:** [from Q3]
- **Build / test / lint:** [from Q6]
- **Conventions:** [from Q7]
- **Prior art:** [from Q11 — the closest past change, its rough step count, and what broke last time. Informs scope and seeds the Phase 3 premortem. "None known" is a valid answer.]

**Verification rule:** before calling any function, API, or library feature not listed above, read its actual definition in the source or installed package. Never write a call from memory of what the API "probably" looks like. If you can't find the definition, stop and ask.

## Boundaries

- **May modify:** [inferred from Q3 and Q4]
- **Must not touch:** [from Q4]
- **Stop and ask when:** a test you didn't expect fails, a change is needed outside "may modify", a step's instructions are ambiguous, or you've attempted the same fix twice without success. Two failed attempts means the plan is wrong, not that you should try harder.
- **Assumptions (re-check every step):** [the novel things this plan takes as true that would invalidate it if false — e.g. "the ORM emits one query per row", "the feature flag defaults off in prod". Distinct from the Verification rule above (read APIs, don't guess) and the single Riskiest assumption below (which drives Step 1). If execution falsifies any item here, stop and ask — do not patch around it.]

**Riskiest assumption:** [from Q5] tested in step [1], which is why it comes first.

## Steps

Sized so each step fits one session. Gate meanings: **AUTO** (default) means complete and
continue unattended. **GATED** means complete, log, then stop and wait for human review —
only used when the human explicitly asked for a checkpoint on that step.

Each step also declares a **Touches** footprint and **Depends on** edges. These aren't
decoration — [[quiz-plan-execute]] diffs them to decide which not-yet-done steps can run
as a **parallel group** (concurrent agents, one per step). Get them right or grouping
does the wrong thing silently.

[Generate steps based on the change. Each step should be concrete enough that two different readers would produce the same change.]

### Step 1: [name] · `[ ]` AUTO | GATED · Parallel group: [none | P1, P2, ...]

- **Do:** [precise instructions]
- **Done when:** [falsifiable criteria]
- **Out of scope here:** [tempting adjacent work to exclude]
- **Touches:** [files/globs this step actually edits — never includes the plan file itself,
  which every step's Stage 6 touches and is deliberately excluded from grouping comparisons]
- **Depends on:** [step numbers this step's correctness relies on, even if `Touches` doesn't
  overlap — e.g. "Step 2" if this step reads a config flag Step 2 introduces. `none` if truly independent]

[Additional steps as needed...]

**Parallel group assignment rule:** two steps may share a group only if their `Touches` sets
are disjoint **and** neither is in the other's (transitive) `Depends on` chain. The step that
tests the **Riskiest assumption** never joins a group — it always runs alone, first. Any step
marked **GATED** never joins a group either — an explicit human checkpoint runs alone so the
pause point stays predictable. Groups are otherwise all-AUTO by construction.

## Verification and rollback

- **Human verifies by:** [from Q8]
- **Failing looks like:** [signals that mean stop and roll back]
- **Rollback:** [from Q9]
- **Kill criteria:** [conditions under which the human abandons this change]

## Progress log

One entry per step, appended at execution time (not written ahead). Newest last. This log is the only memory that survives between sessions, so record decisions, not just actions.

```
[date] Step 1: pending | in progress | done | blocked
Changed: [files touched, one line]
Decided: [choices made and why, so they aren't re-litigated next session]
Surprises: [anything that didn't match ground truth or the plan]
```

#### Progress Tracker Maintenance

When writing the plan, generate the tracker like this:

```markdown
**Progress:** ████░░░░░░░░ 2/6 steps completed (33%)
```

The bar uses exactly 12 characters (█ for done, ░ for remaining). When N is not evenly divisible by 12, round to the nearest char. Examples:

- 0/4 steps completed → `░░░░░░░░░░░░ 0/4 (0%)`
- 1/4 steps completed → `███░░░░░░░░░ 1/4 (25%)`
- 2/4 steps completed → `██████░░░░░░ 2/4 (50%)`
- 3/4 steps completed → `█████████░░░ 3/4 (75%)`
- 4/4 steps completed → `████████████ 4/4 (100%)`

When a step is executed and logged to Progress log, **also update the tracker in the header.** The tracker is human-readable — anyone opening the `.plan.md` file should see immediately how far along the work is.

Each step's checkbox should also be updated: `[ ]` → `[x]` as steps complete.
```

#### Step Generation Guidelines

When generating steps from the quiz answers:

1. **Step 1 should always test the riskiest assumption** (from Q5). This goes first because if this fails, the whole plan is invalid. It never joins a parallel group.
2. Each step should produce a concrete, checkable outcome (a passing test, a rendered route, a working command).
3. **Default every step to AUTO.** Only mark a step **GATED** when the user explicitly asks for a human checkpoint on it (by name, or a general "gate the risky ones" instruction you then apply to the specific steps that match). Don't gate by default "to be safe" — that default was flipped because unattended AUTO execution end-to-end is now the common case, not the exception.
4. If the change involves both infrastructure and code, separate into logical phases (infrastructure first, then code).
5. If the change spans a backend + frontend, order steps by dependency (backend first if the frontend depends on it).
6. A step should fit in one session. If a step would require 20 file changes, split it further.
7. The last step should always include running the build, test, and lint commands from Q6.
8. **Tracker maintenance is part of each step.** Whenever a step is completed, the agent must also update the progress bar and checkboxes in the plan file header.
9. **Pick the approach before the steps.** When Q12 surfaced 2+ viable approaches, choose one deliberately, record the choice and why the alternatives lost in the **Approach** section, then generate steps for the winner only. Don't leave the fork unresolved in the steps.
10. **Assign `Touches` and `Depends on` for every step, then compute parallel groups.** Two AUTO steps that aren't the riskiest-assumption step share a group id (`P1`, `P2`, ...) only if their `Touches` sets are disjoint and neither depends on the other, directly or transitively. Groups need 2+ steps — a step with no groupmate gets `Parallel group: none`. When unsure whether two steps are really independent, default to `none` rather than guessing a group — a missed parallel opportunity costs time, a wrong one costs a broken merge.

### Phase 3: Red-team the Draft

Before showing the plan to the user, turn adversarial on your own draft — you wrote it,
now try to break it. Work through each check; fix anything you can resolve from the
quiz answers or the codebase, and hold anything you can't as one more quiz question rather
than silently patching over it or silently dropping it.

- **Premortem (the outside-in lens):** assume it's a month later and this plan shipped and
  *failed*. Working backwards, list the likely causes (the Q11 prior art is your seed — what
  broke last time?). For each cause, name the step, boundary, or Assumption that already
  defends against it. Any cause with no defender is a coverage gap — add a mitigation step
  (after Step 1, never displacing it) or a stop-condition. This differs from the mechanical
  checks below: they ask "does a step break a rule?", the premortem asks "what failure isn't
  represented as a step at all?"
- **Riskiest assumption:** does Step 1 actually *test* it (falsifiable, would fail if the
  assumption is wrong), or does it just touch the same area?
- **Boundaries:** does any step's `Do` reach outside `May modify`? Does any step conflict
  with `Must not touch`?
- **Done when:** is each criterion checkable by running a command/test, or is it vague
  ("works correctly", "handles it properly")? Rewrite vague ones concretely.
- **Coverage gaps:** do the quiz answers imply work no step covers — a migration, a doc
  update the Q7 conventions require, a config change for existing deployments?
- **Ordering:** does any step depend on output/state a *later* step creates?
- **Scope creep:** does any step's `Do` include work Q4 explicitly excluded?
- **Rollback reachability:** if Verification's "Failing looks like" triggers mid-plan (not
  just at the end), is the Rollback from Q9 still executable at that point?
- **Parallel groups:** for every declared group, are the `Touches` sets *actually* disjoint,
  or does file-set diffing miss a real logical dependency between two steps (one reads a
  flag/schema/contract the other introduces, even in a different file)? Add the missing
  `Depends on` edge and split the group if so. Confirm the riskiest-assumption step and every
  GATED step carry `Parallel group: none` — if either got swept into a group by mistake, fix it.

Only once this pass is clean does the plan move to `Draft` and get presented. When
presenting, add one line noting the red-team pass ran and naming anything it caught and
fixed (or "no issues found") — this must be visible, not a silent internal step.

#### Output

After generating the plan and completing the red-team pass, present to the user:
1. The file path of the created plan
2. A one-line summary of each step
3. One line on what the red-team pass caught (or "no issues found")
4. Ask: *"Do you want to start executing this plan?"*

If yes, hand off to [[quiz-plan-execute]] — run `/quiz-plan-execute <path>`, which drives each
step through a strict 6-stage TDD gate (understand → red → green → refactor → review → commit),
one commit per step, with an optional new branch. Steps sharing a `Parallel group` run
concurrently, one agent per step, each in its own worktree. If no, the plan file exists
on disk for later use — the user can run `/quiz-plan-execute` against it any time.

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
> - **A · internal/api/middleware/ (recommended)**: sits next to the existing logging
>   middleware, so reviewers recognise the pattern; it ties the limiter to that folder's
>   conventions.
> - **B · a new package**: e.g. `pkg/ratelimit/`, reusable later; it adds an import path
>   for a first cut.
> - **C · not sure**: I'll read the code and report back; it costs one extra round.
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

**Agent:** *"Does this look right? Say `wait` if anything's wrong — otherwise I'll write the plan."*
**User:** "Looks good."

*(Agent drafts the plan, then red-teams it — the premortem lens surfaces "limiter counts
requests per-replica, so the real limit is N×replicas in prod" with no step defending it,
so a new Assumption "rate state is per-instance, not shared" is added for the executor to
re-check; and it catches that Step 3's `Done when` said "routes work correctly", rewriting it
as "integration test hits a public route 101 times, gets 429 on the 101st, and a whitelisted
internal-IP route stays 200 the whole time.")*

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

- This skill uses the **same question UX as [[quiz]]**: the picker when there is one, plain markdown otherwise, one question per turn, `✓` echoes, never all questions at once. The differences: the drill is adaptive (no total until it's resolved, and no fixed list up front) and there's no ~7-question cap.
- If the user gives minimal answers, keep the plan short. If they give detailed answers, include all details.
- If the user already has a clear idea of the steps, skip to step generation — capture their steps directly.
- The plan file should be committed to the repository alongside the code changes so the plan stays with the branch.
- **Robustness additions** (Approach / Prior art / Assumptions, plus the premortem lens in Phase 3) come from evidence-backed planning practice: deliberate approach selection (multi-plan beats first-draft), the outside view (anchor scope to the closest past change), and Klein's premortem (imagining failure already happened surfaces ~30% more failure causes than "what might go wrong"). They stay non-redundant by design: the premortem is **folded into the Phase 3 red-team** as one lens (it hunts failures no step represents, where the other checks hunt rule violations), not a separate section. Everything is compatible with [[quiz-plan-execute]], which parses Intent, Ground truth, Boundaries, Steps (`Done when`, `Touches`, `Depends on`, `Parallel group`), and the Progress log — the new **Approach** and **Prior art** are read-only context, while **Assumptions** live inside Boundaries specifically so the executor re-checks them every step (it re-reads Boundaries per step; Ground truth only once).
- **Parallel groups** (`Touches` / `Depends on` / `Parallel group`) exist purely so [[quiz-plan-execute]] can safely run independent steps concurrently. `Touches` never lists the plan file itself — every step's Stage 6 writes to it, so including it would make every step look dependent on every other. When in doubt about a dependency that file-overlap alone wouldn't reveal, write it into `Depends on` rather than leaving the group assignment to guesswork.
