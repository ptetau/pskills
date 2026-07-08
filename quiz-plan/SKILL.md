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

Interview the user one card at a time (the [[quiz]] card UX — see "The look" below), drilling deeper as answers reveal ambiguity. You have a starter question bank below, but the quiz is **not limited to the starter pool**. Each answer may reveal assumptions, ambiguities, or unknowns that need their own follow-up. Keep asking until you can write a complete, unambiguous plan.

#### Starter Question Pool

These are your opening questions — a pool to draw from, **not a script to recite in order**. Skip any that the user's opening statement already answered. Render each as a **quiz card** (identical to `/quiz` — see "The look" below), **one per turn**. Expect to ask follow-up drill questions (see next section) that go deeper — those are rendered as cards too.

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
Captures: closest past change, rough step count, known failure modes. → **Ground truth → Prior art**

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

#### The look (identical to /quiz)

The question UX is **the same terminal-card experience as [[quiz]]** — same Apple //e × IBM Plex aesthetic, same markers, same rhythm. Render every question (starter *and* drill follow-up) as its own fenced code block card. **One question per message, always** — never stack two cards in the same turn.

##### The question card

````
```
┌─ quiz · 03/·· ──────────────────────────────────────┐
│ [?] Where does the rate-limit middleware live?      │
│     why it matters: fixes which files the plan edits │
└──────────────────────────────────────────────────────┘

  A · internal/api/middleware/   next to the logging middleware
  B · a new top-level package     e.g. pkg/ratelimit/
  C · not sure                    I'll go read the code and report

  // reply: A | B | C    (optional: add a note after the letter)
```
````

Then on the next chat line, in plain prose, one sentence: *"Pick A, B, or C — or reply `B, with notes: …` to add detail."*

The counter is `quiz · NN/··`. Because the drill is **adaptive**, the total is unknown while asking, so the denominator stays `··`. Increment the index each turn (`01`, `02`, `03`…). In the final resolved view, backfill the real total (`07/07`).

For **free-text** answers (commands, file paths, branch name) where lettered options don't fit, drop the `A · …` options and end the card with `// reply: <your answer>` instead — the card frame, `[?]` marker, and `why it matters:` line stay identical.

##### The rhythm (between questions)

After each reply, echo a one-line `[✓]` confirmation for the just-answered question, then *immediately* render the next card in the same message:

```
turn 1 — agent: render Q1 card + reply hint
turn 2 — user: "A"
turn 3 — agent: "[✓] 01 change → A · add rate limiting"  then Q2 card + reply hint
turn 4 — user: "B, with notes: env-configurable, default 100/min"
turn 5 — agent: "[✓] 02 limit → B · configurable (note: default 100/min)"  then Q3
…
```

##### Final resolved view (after the drill is exhausted)

When you have no remaining questions, restate the whole set with `[✓]` markers (backfilling the real total) so the user can spot a mistake before Phase 2:

```
[✓] 01 change   → add rate limiting to public API routes
[✓] 02 limit    → configurable   (note: default 100/min)
[✓] 03 location → internal/api/middleware/
…
[✓] 07 branch   → feature/rate-limiting
```

Then in one plain sentence: *"Does this look right? Say `wait` if anything's wrong — otherwise I'll write the plan."* This confirmation gates Phase 2.

##### Rules of the look

1. **Always a fenced code block.** Monospace is the aesthetic — render as a code block, not prose with hyphens.
2. **Top border `quiz · NN/··`.** Lowercase. Box-drawing chars (`┌─┐│└┘`) for the header; plain ASCII for the rest.
3. **`[?]` for open, `[✓]` for resolved.** Match the [[quiz]]/[[squiz]] convention exactly.
4. **Options as `A · short-label   longer-explanation`**, two-space indent, ≤~70 chars wide so it survives mobile.
5. **Optional `why it matters:` line** — one short clause, only when the consequence helps the user answer.
6. **`// reply:` hint at the bottom** of every card.
7. **One question per turn — never stack.** Each card its own message. Wait for the reply before the next.
8. **No emojis** in the cards (except as literal sample content in option text).
9. **No cap.** Unlike `/quiz` (which caps at ~7 and escalates to `/squiz`), the plan drill runs as long as ambiguity remains — keep rendering cards until the "Signs you're done asking" above are all true.

##### Reply parsing (same as /quiz)

Be permissive. Accept `A` / `a` / `Option A`; `B, with notes: …`; `B (…)`; `skip` / `you decide` / `n/a` (explicit skip, you choose). If the user types free prose ("the middleware one"), match to the closest option and confirm in your echo. If they answer several at once (`1a2b3c`), parse the run, echo all `[✓]` lines in order, and move to the next unanswered question.

##### Drill behaviour within the card UX

1. Use the user's own terms in follow-up cards (mirror their language).
2. **Short/hedged answer → drill deeper.** "Probably" or "I think" means the next card is a follow-up on that point.
3. Never argue with scope. Record what the user says — Boundaries will flag risk.
4. **Drill until clear** (see "Signs you're done asking"). Only render the resolved view when no questions remain.
5. If the user revises an earlier answer in the resolved view, update your notes, check whether the revision opens a new question (render one more card if so). Don't re-ask everything.

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

1. Read Intent, Ground truth, and Boundaries in full (plus Approach, if present), then skim the Premortem so you know the failure modes this plan already accounts for.
2. Read the Progress log to find the current state. Do not redo completed steps or reopen decisions recorded there.
3. Resume at the first step not marked done. Respect its gate.
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
- **Prior art:** [from Q11 — the closest past change, its rough step count, and what broke last time. Informs scope and seeds the Premortem. "None known" is a valid answer.]

**Verification rule:** before calling any function, API, or library feature not listed above, read its actual definition in the source or installed package. Never write a call from memory of what the API "probably" looks like. If you can't find the definition, stop and ask.

## Boundaries

- **May modify:** [inferred from Q3 and Q4]
- **Must not touch:** [from Q4]
- **Stop and ask when:** a test you didn't expect fails, a change is needed outside "may modify", a step's instructions are ambiguous, or you've attempted the same fix twice without success. Two failed attempts means the plan is wrong, not that you should try harder.
- **Assumptions (re-check every step):** [the novel things this plan takes as true that would invalidate it if false — e.g. "the ORM emits one query per row", "the feature flag defaults off in prod". This is a *different* list from the Verification rule above (which is about reading APIs, not from memory) and the single Riskiest assumption below (which drives Step 1). If execution falsifies any item here, stop and ask — do not patch around it.]

**Riskiest assumption:** [from Q5] tested in step [1], which is why it comes first.

## Premortem

Written *after* the Steps below are drafted (it operates on the whole plan, not a single guess). Assume this plan shipped and failed. List the likely causes; each points to the step or boundary that already defends against it — **not** a restated fix:

- **[cause of failure]** → defended by step [N] / Boundaries "[rule]" / Assumption "[item]"
- **[cause of failure]** → …

Any cause with no defending step, boundary, or assumption is a gap: add a mitigation step or a stop-condition before finalizing the plan. Do **not** displace Step 1 — it stays the Riskiest-assumption test; premortem mitigations are inserted after it or folded into an existing step's *Done when*.

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
9. **Pick the approach before the steps.** When Q12 surfaced 2+ viable approaches, choose one deliberately, record the choice and why the alternatives lost in the **Approach** section, then generate steps for the winner only. Don't leave the fork unresolved in the steps.
10. **Run a premortem after the steps are drafted, before presenting.** With the ordered steps in hand, assume the plan shipped and failed and list the likely causes. Fold each cause into: an existing step's *Done when*, a new mitigation step inserted **after** Step 1, or a Boundaries stop-condition / Assumption. Populate the **Premortem** section with cause → defender lines. This is a check on the drafted plan, not a rehash of Q5 — Q5 named the single riskiest thing (Step 1); the premortem sweeps for the rest.

#### Output

After generating the plan, present to the user:
1. The file path of the created plan
2. A one-line summary of each step
3. The top 2–3 premortem causes and which step/boundary defends each (so the user sees the failure analysis before agreeing)
4. Ask: *"Do you want to start executing this plan?"*

If yes, hand off to [[quiz-plan-execute]] — run `/quiz-plan-execute <path>`, which drives each
step through a strict 6-stage TDD gate (understand → red → green → refactor → review → commit),
one commit per step, with optional new branch / worktree / subagent. If no, the plan file exists
on disk for later use — the user can run `/quiz-plan-execute` against it any time.

## Example

**User:** "/quiz-plan I want to add rate limiting to the API"

### Quiz interaction (card UX, showing adaptive drilling)

Every question is a card — one per turn, `[✓]` echo before the next — exactly like `/quiz`.

```
┌─ quiz · 01/·· ──────────────────────────────────────┐
│ [?] One sentence — what are we changing?            │
└──────────────────────────────────────────────────────┘

  // reply: <your answer>
```
**User:** "Add rate limiting to the public API routes."

```
[✓] 01 change → add rate limiting to public API routes

┌─ quiz · 02/·· ──────────────────────────────────────┐
│ [?] What's the riskiest part — most likely to break?│
│     why it matters: step 1 of the plan tests it     │
└──────────────────────────────────────────────────────┘

  // reply: <your answer>
```
**User:** "We accidentally rate-limit our own internal services if they share an IP pool."

```
[✓] 02 risk → internal services throttled if they share an IP pool

┌─ quiz · 03/·· ──────────────────────────────────────┐
│ [?] Where does the middleware live?                 │
│     why it matters: fixes which files the plan edits │
└──────────────────────────────────────────────────────┘

  A · internal/api/middleware/   next to logging middleware
  B · a new package               e.g. pkg/ratelimit/
  C · not sure                    I'll go read the code

  // reply: A | B | C
```
**User:** "A — there's already a logging-middleware pattern there."

*(Drill continues as cards: limit configurable-or-hardcoded, must-not-touch, verification, build/test commands, branch — one card each, until no ambiguity remains.)*

```
[✓] 01 change    → add rate limiting to public API routes
[✓] 02 risk      → internal services throttled if IP pool shared
[✓] 03 location  → internal/api/middleware/   (note: mirror logging mw)
[✓] 04 limit     → configurable   (note: env var, default 100/min)
[✓] 05 must-not  → auth middleware, private/internal routes
[✓] 06 verify    → integration test: 101st rapid req → 429
[✓] 07 commands  → go build ./...  ·  go test ./...
[✓] 08 branch    → feature/rate-limiting
```
**Agent:** *"Does this look right? Say `wait` if anything's wrong — otherwise I'll write the plan."*
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

**Premortem excerpt** (run after the steps were drafted):
> - **Internal services throttled** → defended by step 2 (whitelist internal IPs) + Boundaries "must not touch private/internal routes"
> - **Limit hard-coded, can't tune in prod** → defended by step 2 (env-configurable, default 100/min)
> - **Limiter counts across replicas inconsistently** → gap → added Assumption "rate state is per-instance, not shared" for the executor to re-check

*After step 1 completes, the header updates to:*
> **Progress:** ██░░░░░░░░░░ 1/5 steps completed (20%)

## Notes

- This skill uses the **same terminal-card quiz UX as [[quiz]]** — one card per turn, `[✓]` echoes, never dump all questions at once. The only differences: the drill is adaptive (denominator `··` until resolved) and there's no ~7-question cap.
- If the user gives minimal answers, keep the plan short. If they give detailed answers, include all details.
- If the user already has a clear idea of the steps, skip to step generation — capture their steps directly.
- The plan file should be committed to the repository alongside the code changes so the plan stays with the branch.
- **Robustness additions** (Approach / Prior art / Assumptions / Premortem) come from evidence-backed planning practice: deliberate approach selection (multi-plan beats first-draft), the outside view (anchor scope to the closest past change), and Klein's premortem (imagining failure already happened surfaces ~30% more failure causes than "what might go wrong"). They are all **additive sections** — [[quiz-plan-execute]] parses only Intent, Ground truth, Boundaries, Steps (`Done when`), and the Progress log, so nothing here changes what the executor consumes. Two design choices keep the new material *live* rather than decorative: Assumptions sit in **Boundaries** (which the executor re-checks every step), and every Premortem cause resolves to a real step, boundary, or assumption the executor already runs — never a free-floating note.
