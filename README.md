# pskills

A collection of Claude Code skills. Install any skill by copying its directory into
`~/.claude/skills/` — Claude Code picks them up automatically.

```
~/.claude/skills/
  argue/
    SKILL.md
  quiz/
    SKILL.md
  quiz-plan/
    SKILL.md
  quiz-plan-execute/
    SKILL.md
  squiz/
    SKILL.md
```

---

## `/argue` — Logical Contradiction Detector

Paste any text (spec, plan, essay, argument) and `/argue` will:

1. Break it into discrete logical claims (C1, C2, …)
2. Encode the claims in propositional logic
3. Run **Z3** as a deterministic SAT solver to prove hard contradictions
4. Use reasoning to flag tensions and ambiguities
5. Return an annotated version of the original text + a tiered summary

Requires `z3-solver`: `pip install z3-solver`

**Example**

```
/argue The API must respond within 50ms. All requests go through the fraud
detection pipeline before returning. The fraud pipeline takes 200ms minimum.
No request may bypass fraud detection.
```

**Output (excerpt)**

```
CONTRADICTIONS  (proven UNSAT by Z3)

  !! C1 × C2 × C3  A synchronous fraud check of 200ms+ makes a 50ms
                   API response impossible for any request
                   logic: api_under_50ms ∧ all_requests_fraud
                          ∧ fraud_takes_200ms_plus → UNSAT

VERDICT   1 contradiction  ·  1 tension  ·  1 ambiguity
```

---

## `/quiz` — Inline Clarifier

Asks clarifying questions one at a time as compact terminal-style cards before
starting work. Use it to lock in decisions (audience, scope, tone, approach)
without a back-and-forth prose conversation.

**Example**

```
/quiz a dashboard that shows real-time API health metrics
```

**Output**

```
┌─ quiz · 01/04 ──────────────────────────────────────┐
│ [?] Who is the primary audience for this dashboard? │
│     why it matters: drives layout and data density  │
└──────────────────────────────────────────────────────┘

  A · engineers     raw metrics, dense, no fluff
  B · managers      trends and status, not raw numbers
  C · both          overview + drill-down toggle

  // reply: A | B | C
```

Reply with a letter (optionally with notes: `B, with notes: include p99 latency`).
After the last question, a resolved summary is shown before work begins.

Cap: ~7 questions. For more, escalate to `/squiz`.

---

## `/quiz-plan` — Quiz-driven Change Plan

Runs an adaptive interview (not a fixed list) to surface every assumption, ambiguity,
and dependency in a proposed change, then writes a structured `<name>.plan.md` at the
project root: Intent, Ground truth, Boundaries, gated Steps, Verification/rollback, and
a live progress tracker. Step 1 always tests the riskiest assumption.

**Example**

```
/quiz-plan add rate limiting to the public API routes
```

The agent drills — configurable or hardcoded limit? which middleware dir? what must not
change? — until it can picture the exact files and changes, confirms, then emits
`add-api-rate-limiting.plan.md` with per-step gates (AUTO / GATED) and a 12-char
progress bar in the header.

---

## `/quiz-plan-execute` — Plan Executor (TDD, per-step commits)

The executor twin of `/quiz-plan`. Reads a `.plan.md` and works each step to completion
through a strict 6-stage gate — each stage must finish before the next:

1. **Understand** the acceptance criteria (the step's `Done when`)
2. **Red** — write the failing test
3. **Green** — minimum impl to pass
4. **Refactor** — remove duplication, meet conventions, cut complexity
5. **Review** against acceptance criteria
6. **Commit** — one commit per step, plan tracker updated in the same commit

At start it asks whether to work in a new branch, a new git worktree, and/or dispatch
each step to a fresh subagent. On completion it offers to squash-merge locally or open
a PR.

**Example**

```
/quiz-plan-execute add-api-rate-limiting.plan.md
```

GATED steps pause for human review; AUTO steps continue. On conflict with Intent or
Boundaries the executor stops and asks rather than resolving it itself.

---

## `/squiz` — Visual Clarifier Document

The document-mode twin of `/quiz`. Instead of one-at-a-time cards, the
[squiz](https://github.com/squiz-cli/squiz) Go binary renders a self-contained
interactive HTML document with all decisions at once, retro Apple //e styling,
and mini-wireframe previews for visual options.

The user fills it in at their own pace and pastes a single JSON payload back.

**Example**

```
/squiz a mobile onboarding flow for a habit-tracking app
```

Squiz renders an HTML doc covering every decision (layout, tone, data model,
progression logic). The user fills in each section and pastes the JSON result
back — Claude reads the payload and begins implementation.

Requires the `squiz` binary: see [squiz releases](https://github.com/squiz-cli/squiz/releases).

Prefer `/quiz` for small sets of textual questions. Use `/squiz` when decisions
are visual, numerous, or benefit from seeing all options side by side.
