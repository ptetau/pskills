# pskills

A collection of Claude Code skills. Install any skill by copying its directory into
`~/.claude/skills/` — Claude Code picks them up automatically.

```
~/.claude/skills/
  argue/
    SKILL.md
  blueprint/
    SKILL.md
    references/
      blueprint-template.md
      conventions.md
      notifications.blueprint.md
      sources.md
    scripts/
      check_blueprint.py
  decompose/
    SKILL.md
    references/
      bricks.md
      brownfield.md
      design-template.md
      examples.md
      sources.md
      walls.md
    scripts/
      volatility.py
  probe/
    SKILL.md
    references/
      findings.schema.json
      report-template.md
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

## `/blueprint` — Agent-Ready Spec from a Design

The companion to `/decompose`. A design document explains *why* the system is shaped the
way it is; a coding agent needs *what exactly* to build. `/blueprint` rewrites a design
(a `name.design.md`, or any architecture doc) into an **Agent System Design Document** that
a person can skim and an agent can implement without guessing:

1. **Header and boundary box**: purpose, target mode, in scope, out of scope
2. **System invariants**: 4–7 enforceable rules, each with where it is enforced and its
   error code
3. **Core data contracts**: exact types (TypeScript, Go, or Rust)
4. **State machines**: every lifecycle, with guards, terminal states, and illegal moves
5. **Module boundaries and signatures**: typed methods, constraints, and failure and
   retry behavior per component
6. **Verification suite**: 3–5 Gherkin scenarios that exercise every invariant

Every detail the design leaves open (a retry count, a key format, a storage engine) is
decided once, marked *(assumed)*, and listed for review, so no agent has to guess.
`blueprint/scripts/check_blueprint.py` checks the result: structure, that every invariant
has an enforcement point and an error code, that every error code is exercised by a
scenario, that every state type has a state machine, and that no design IDs such as `V1`
remain. With `--compile` it also type-checks the TypeScript.

**Example**

```
/blueprint notifications.design.md
```

**Output (excerpt)**

```
BLUEPRINT: notifications · TypeScript · modular monolith
══════════════════════════════════════════════════
SCOPE        8 in · 4 out
INVARIANTS   6 · codes: IDEMPOTENCY_CONFLICT, QUIET_HOURS_DEFERRED, …
CONTRACTS    19 types · 2 state machines
MODULES      9 components: 3 Clients · 1 Manager · 2 Engines · 3 ResourceAccess
SCENARIOS    5 · every invariant exercised
DECISIONS    9 listed for review · 0 open questions
CHECK        PASS
```

Hand the blueprint to `/quiz-plan` for a change plan, then `/quiz-plan-execute`, which uses
the Gherkin scenarios as its failing tests.

---

## `/decompose` — Software Design by Volatility and Primitives

Designs a new system (inception) or a new subsystem inside an existing codebase in
two passes, then proves the result:

1. **Walls** — volatility-based decomposition. Find what is likely to change and put
   each thing behind one component: Managers for changing workflows, Engines for
   changing rules, ResourceAccess for changing storage and third parties. A change
   then lands in one place.
2. **Bricks** — orthogonal primitives. Inside each wall, build a small set of
   independent parts (inputs, transforms, transports, stores, state machines) that
   share one contract, and assemble features as compositions of them.
3. **Proof** — walk the core use cases through the walls, simulate each likely change
   (target: one component touched), and assemble current and future features from
   existing bricks (target: at most one new brick).

In an existing codebase it measures volatility from git history instead of guessing:
`decompose/scripts/volatility.py` reports component churn, change coupling, and
hotspots (standard-library Python, works on Windows). The output is a
`<name>.design.md` with the volatility register, walls, bricks, feature assembly,
validation results, and (for subsystems) the seam and migration steps.

**Example**

```
/decompose a notifications service: welcome emails, password-reset SMS, daily
digests, Slack alerts, channel preferences, quiet hours, retries, localization
```

**Output (excerpt)**

```
DECOMPOSE: notifications · inception
══════════════════════════════════════════════════
VOLATILITIES  5 contained · 3 rejected
WALLS         9 components: 3 Clients · 1 Manager · 2 Engines · 3 ResourceAccess · plus 3 Utilities
BRICKS        12 across 7 components · contracts: Envelope
──────────────────────────────────────────────────
USE CASES     3/3 walk through cleanly
CHANGE SIM    5/5 volatilities touch one component
FEATURES      8 current assembled · 3 future with ≤1 new brick
VERDICT       ready
```

Hand the design to `/argue` to check it for contradictions, to `/blueprint` to make it
agent-ready, or to `/quiz-plan` to turn it into a change plan.

---

## `/probe` — Exploratory Tester

Autonomous exploratory bug hunting for a running app. `probe` reads docs/specs,
commit history, and code to build an app map and derive user-facing feature flows,
then fans out a **flow × dimension** matrix of read-only probe agents (via a
`Workflow`) that statically reason about the code and then live-drive the app
non-destructively — recording surprises and bugs with repro + evidence. An
adversarial verify pass drops false positives before `probe` writes a
severity-ranked Markdown report plus a machine-readable JSON findings file.
Every probe agent is strictly read-only; nothing it does may mutate the target app.

**Example**

```
/probe the staging checkout flow at https://staging.example.com
```

`probe` maps `checkout`, `sign-up`, and `apply-discount-code` as feature flows,
fans out one read-only agent per (flow, quality-dimension) cell — functional,
robustness, security, perf, a11y, ux — verifies the raw findings adversarially, and
writes `probe-report.md` (ranked findings with repro + evidence) and
`probe-findings.json` (validating against `probe/references/findings.schema.json`).

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
