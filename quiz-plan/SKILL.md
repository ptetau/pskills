---
name: quiz-plan
description: Interactive quiz-driven planning. Asks structured questions to gather context, then generates a comprehensive Change Plan document with Intent, Ground truth, Boundaries, Steps, Verification, and Progress log. Use for any non-trivial code change that needs a clear plan before implementation.
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

The skill has two phases that flow sequentially: the quiz (gather), then the plan (document).

### Phase 1: The Adaptive Quiz

Interview the user through a conversational drill-down. You have a starter question bank below, but the quiz is **not limited to these 10 questions**. Each answer may reveal assumptions, ambiguities, or unknowns that need their own follow-up. Keep asking until you can write a complete, unambiguous plan.

#### Starter Question Pool

These are your opening questions — a pool to draw from, **not a script to recite in order**. Skip any that the user's opening statement already answered. Ask them conversationally, woven into the flow, one at a time. Expect to ask follow-up drill questions (see next section) that go deeper.

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

#### Quiz Interaction Rules

1. Ask questions **one at a time** woven into natural conversation. Do not read from a list.
2. Use the user's own terms in follow-ups (mirror their language).
3. **Short answer → drill deeper.** "Probably" or "I think" means a follow-up is needed.
4. Never argue with scope. Record what the user says — if it's risky, Boundaries will flag it.
5. **Drill until clear** (see signs above). Only proceed to confirmation when you have no remaining questions.
6. Once you're satisfied the drill is exhausted, summarise what you heard and ask: *"Does this look right? Anything to add or change?"* This confirmation gates Phase 2.
7. If the user revises a previous answer during confirmation, update your notes and check if the revision opens new questions. Do not re-ask every question.

### Phase 2: Write the Plan

After the quiz is confirmed, generate a `.plan.md` file at the project root.

#### File name

`<kebab-case-name>.plan.md`

Derive the name from the user's description of Q1. For example:
- "Add OAuth login to the API" → `add-oauth-login.plan.md`
- "Refactor the auth middleware" → `refactor-auth-middleware.plan.md`

#### Template

```markdown
# Change Plan: [name derived from Q1]

**Owner:** `[current user from git config, or "you"]` · **Status:** Draft | Agreed | In progress | Done
**Branch:** `[from Q10]` · **Plan location:** `[path to this file]`
**Progress:** [visual bar] `[X]/[N] steps completed ([P]%)`

## How to use this document (read this first, every session)

You are an agent executing this plan. Assume you have no memory of previous sessions.

1. Read Intent, Ground truth, and Boundaries in full.
2. Read the Progress log to find the current state. Do not redo completed steps or reopen decisions recorded there.
3. Resume at the first step not marked done. Respect its gate.
4. After each step: append to the Progress log, then self-assess against the step's done criteria before moving on.
5. If anything you're about to do conflicts with Intent or Boundaries, stop and ask. Do not resolve the conflict yourself.

## Intent

[From Q2 — what's wrong and what will be observably different]

[From Q4 — scope exclusions]

**Not doing:** [from Q4]

## Ground truth

- **Key files:** [from Q3]
- **Build / test / lint:** [from Q6]
- **Conventions:** [from Q7]

**Verification rule:** before calling any function, API, or library feature not listed above, read its actual definition in the source or installed package. Never write a call from memory of what the API "probably" looks like. If you can't find the definition, stop and ask.

## Boundaries

- **May modify:** [inferred from Q3 and Q4]
- **Must not touch:** [from Q4]
- **Stop and ask when:** a test you didn't expect fails, a change is needed outside "may modify", a step's instructions are ambiguous, or you've attempted the same fix twice without success. Two failed attempts means the plan is wrong, not that you should try harder.

**Riskiest assumption:** [from Q5] tested in step [1], which is why it comes first.

## Steps

Sized so each step fits one session. Gate meanings: **AUTO** means complete and continue. **GATED** means complete, log, then stop and wait for human review.

[Generate steps based on the change. Each step should be concrete enough that two different readers would produce the same change.]

### Step 1: [name] · `[ ]` AUTO | GATED

- **Do:** [precise instructions]
- **Done when:** [falsifiable criteria]
- **Out of scope here:** [tempting adjacent work to exclude]

[Additional steps as needed...]

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

1. **Step 1 should always test the riskiest assumption** (from Q5). This goes first because if this fails, the whole plan is invalid.
2. Each step should produce a concrete, checkable outcome (a passing test, a rendered route, a working command).
3. Default to **GATED** steps unless the user explicitly says they want auto-execution. GATED means the agent pauses and waits for human review after each step.
4. If the change involves both infrastructure and code, separate into logical phases (infrastructure first, then code).
5. If the change spans a backend + frontend, order steps by dependency (backend first if the frontend depends on it).
6. A step should fit in one session. If a step would require 20 file changes, split it further.
7. The last step should always include running the build, test, and lint commands from Q6.
8. **Tracker maintenance is part of each step.** Whenever a step is completed, the agent must also update the progress bar and checkboxes in the plan file header.

#### Output

After generating the plan, present to the user:
1. The file path of the created plan
2. A one-line summary of each step
3. Ask: *"Do you want to start executing this plan?"*

If yes, hand off to [[quiz-plan-execute]] — run `/quiz-plan-execute <path>`, which drives each
step through a strict 6-stage TDD gate (understand → red → green → refactor → review → commit),
one commit per step, with optional new branch / worktree / subagent. If no, the plan file exists
on disk for later use — the user can run `/quiz-plan-execute` against it any time.

## Example

**User:** "/quiz-plan I want to add rate limiting to the API"

### Quiz interaction (showing adaptive drilling)

**Agent:** "One sentence — what are we changing?"
**User:** "Add rate limiting to the public API routes."

**Agent:** "What problem does this solve?"
**User:** "One client hammers us and degrades service for everyone. No rate limiting exists today."

*Drill: the answer says "public API routes" — what about internal services that might share an IP pool?*

**Agent:** "What's the riskiest part — the thing most likely to break?"
**User:** "We accidentally rate-limit our own internal services if they share an IP pool with a bad client."

*Drill noted. Move to files.*

**Agent:** "What files are we touching?"
**User:** "The router, and I'll add a middleware package. Plus go.mod for the library."

*Drill: "middleware package" is vague — where exactly?*

**Agent:** "Where does the middleware live — `internal/api/middleware/` or somewhere else?"
**User:** "Yeah, `internal/api/middleware/` — there's already a pattern there for logging middleware."

*Drill: existing pattern means we need to inspect it. Capture as convention.*

**Agent:** "Anything we must not touch?"
**User:** "Don't touch the auth middleware. Don't change private/internal routes."

**Agent:** "How will we verify this is done?"
**User:** "Integration test — 100 rapid requests from the same IP, expect 429 on the 101st."

*Drill: does the user want a configurable limit, or is 100 hardcoded?*

**Agent:** "What's the rate limit — configurable or hardcoded?"
**User:** "Configurable via env var, default 100 requests per minute."

**Agent:** "Rollback if this goes wrong?"
**User:** "git revert."

**Agent:** "Build and test commands?"
**User:** "`go build ./...` and `go test ./...`"

*Drill: conventions check — user mentioned the logging middleware pattern. Verify.*

**Agent:** "Before I write the plan — any existing docs (CLAUDE.md, ADRs) I should read? Or a branch name?"
**User:** "Branch is `feature/rate-limiting`. No other docs needed."

*Drill exhausted. No more ambiguous answers. Confirm:*

**Agent:** "Here's what I captured: [summary]. Does this look right?"
**User:** "Looks good."

### Generated plan

**File:** `add-api-rate-limiting.plan.md`

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

- This skill is designed for a conversational, quiz-style interaction. Do not dump all questions at once.
- If the user gives minimal answers, keep the plan short. If they give detailed answers, include all details.
- If the user already has a clear idea of the steps, skip to step generation — capture their steps directly.
- The plan file should be committed to the repository alongside the code changes so the plan stays with the branch.
