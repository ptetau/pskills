# pskills

A collection of Claude Code skills. To install a skill, copy its directory into
`~/.claude/skills/`. Claude Code then finds the skill automatically.

```
~/.claude/skills/
  argue/
    SKILL.md
  blueprint/
    SKILL.md
    references/
      blueprint-template.md
      c4.md
      conventions.md
      notifications.blueprint.md
      plain-language.md
      sources.md
    scripts/
      check_blueprint.py
      readability.py
  decompose/
    SKILL.md
    references/
      bricks.md
      brownfield.md
      c4.md
      design-template.md
      examples.md
      plain-language.md
      sources.md
      walls.md
    scripts/
      readability.py
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
  vet/
    SKILL.md
    references/
      vet.workflow.js
      agents.schema.json
      suite.schema.json
      results.schema.json
      report-template.md
```

---

## `/argue` — Logical Contradiction Detector

Paste any text (spec, plan, essay, argument). `/argue` then does these steps:

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

The companion to `/decompose`. A design document explains *why* the system has its shape.
A coding agent needs *what exactly* to build. `/blueprint` rewrites a design (a
`name.design.md`, or any architecture doc) into an **Agent System Design Document**. A
person can skim this document, and an agent can implement it without guessing. It has six
sections:

1. **Header and boundary box**: purpose, target mode, in scope, out of scope
2. **System invariants**: 4–7 enforceable rules, each with the place that enforces it and
   its error code
3. **Core data contracts**: exact types (TypeScript, Go, or Rust)
4. **State machines**: every lifecycle, with guards, terminal states, and illegal moves
5. **Module boundaries and signatures**: typed methods, constraints, and failure and
   retry behaviour per component
6. **Verification suite**: 3–5 Gherkin scenarios that exercise every invariant

`/blueprint` decides every detail the design leaves open (a retry count, a key format, a
storage engine) once. It marks each decision *(assumed)* and lists it for review, so no
agent has to guess. `blueprint/scripts/check_blueprint.py` checks the result:

- the structure;
- every invariant has an enforcement point and an error code;
- a scenario exercises every error code;
- every state type has a state machine;
- no design IDs such as `V1` remain.

With `--compile`, the checker also type-checks the TypeScript.

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
DECISIONS    11 added for review + 0 carried from the design · 0 open questions
CHECK        PASS
```

`/blueprint` draws a C4 container diagram (what runs, and which parts each container
holds) and a C4 component diagram (who calls whom). The checker confirms that both
diagrams match the text.
`--render` renders every diagram with Mermaid.

Hand the blueprint to `/quiz-plan` for a change plan. Then run `/quiz-plan-execute` on the
plan. For each step, `/quiz-plan-execute` writes a failing test from the step's acceptance
criteria before it writes any code.

**Both skills write in plain English**, for a bright 10-year-old: short sentences, common
words, and every technical word explained in a "Words used here" list. Names, types, and
error codes stay exact. `readability.py` (shipped with both) measures sentence length and
reading grade, and lists unexplained technical words.

---

## `/decompose` — Software Design by Volatility and Primitives

Designs a new system (inception) or a new subsystem inside an existing codebase in
two passes, then proves the result:

1. **Walls** — volatility-based decomposition. Find what is likely to change. Put each
   thing behind one component. Managers hold changing workflows, Engines hold changing
   rules, and ResourceAccess holds changing storage and third parties. A change then
   lands in one place.
2. **Bricks** — orthogonal primitives. Inside each wall, build a small set of
   independent parts (inputs, transforms, transports, stores, state machines). The
   parts share one contract. Assemble features as compositions of these parts.
3. **Proof** — walk the core use cases through the walls. Simulate each likely change
   (target: one component touched). Assemble current and future features from existing
   bricks (target: at most one new brick).

`/decompose` draws the result as C4 diagrams: a system context diagram and a component
diagram. The component diagram has one band per layer, and every arrow is an allowed
call.

In an existing codebase, `/decompose` measures volatility from git history instead of
guessing. `decompose/scripts/volatility.py` reports component churn, change coupling, and
hotspots. The script is standard-library Python and works on Windows. The output is a
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

Then hand the design to one of these skills:

- `/argue`, to check the design for contradictions;
- `/blueprint`, to make the design agent-ready;
- `/quiz-plan`, to turn the design into a change plan.

---

## `/probe` — Exploratory Tester

Autonomous exploratory bug hunting for a running app. `probe` reads docs/specs, commit
history, and code. From these, `probe` builds an app map and derives user-facing feature
flows. Then it fans out a **flow × dimension** matrix of read-only probe agents (via a
`Workflow`). Each probe agent first reasons about the code statically. Then the agent
drives the live app non-destructively and records surprises and bugs with repro +
evidence. An adversarial verify pass drops false positives before `probe` writes a
severity-ranked Markdown report plus a machine-readable JSON findings file. Every probe
agent is strictly read-only; nothing it does may mutate the target app.

**Example**

```
/probe the staging checkout flow at https://staging.example.com
```

`probe` maps `checkout`, `sign-up`, and `apply-discount-code` as feature flows. It fans
out one read-only agent per (flow, quality-dimension) cell. The quality dimensions are
functional, robustness, security, perf, a11y and ux. `probe` verifies the raw findings
adversarially. Then it writes two files:

- `probe-report.md`: ranked findings with repro + evidence;
- `probe-findings.json`: validates against `probe/references/findings.schema.json`.

---

## `/quiz` — Inline Clarifier

Asks clarifying questions one at a time before starting work, to lock in decisions
(audience, scope, tone, approach) without a back-and-forth prose conversation. Each
question is a native picker the user clicks. Where there's no picker, each question is a
short plain-markdown question that the user answers with a letter.

`/quiz` plans its questions up front in a fixed order: purpose, style, scope, focus, next
step. Because of this order, the same request gets the same questions. `/quiz` recommends
an option only when something the user said points to it.

**Example**

```
/quiz a dashboard that shows real-time API health metrics
```

**Output** (plain-markdown fallback; with a picker the same options are clickable)

> **Question 1 of 3 · Audience**
> Who is the primary audience for this dashboard?
>
> - **A · Engineers**: It shows dense raw metrics with no fluff. It suits the team that
>   runs the API. It is hard for anyone outside the team to read.
> - **B · Managers**: It shows trends and status, not raw numbers. It suits people who
>   track health over weeks. It hides the detail that on-call needs.
> - **C · Both**: It gives an overview with a drill-down toggle. It serves both groups
>   from one page. It takes more to build.
>
> Reply A, B or C, optionally with a note.

Each option gives three short sentences: what it is, why it fits, and what it costs.
Reply with a letter, optionally with a note (`B, include p99 latency`). `/quiz` echoes
each answer in one line (`✓ 1/3 Audience → Managers`). After the last question, `/quiz`
shows the resolved list for a final OK before work begins.

Cap: ~7 questions. For more, escalate to `/squiz`.

---

## `/quiz-plan` — Quiz-driven Change Plan

Runs an adaptive interview (not a fixed list) to surface every assumption, ambiguity,
and dependency in a proposed change. Then it writes a structured `plans/<name>.plan.md`,
with Intent, Ground truth, Boundaries, gated Steps, Verification/rollback, and a live
progress tracker. Step 1 always tests the riskiest assumption.

**Example**

```
/quiz-plan add rate limiting to the public API routes
```

The agent drills down: configurable or hardcoded limit? which middleware dir? what must
not change? The agent keeps asking until it can picture the exact files and changes.
Then it confirms and writes `plans/add-api-rate-limiting.plan.md`. The plan has per-step
gates (AUTO / GATED) and a 12-char progress bar in the header.

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

At the start it asks one question: whether to create a new branch for the work. Steps
run one at a time, in order, in the main thread. Steps that share a `Parallel group` tag
in the plan run at the same time instead. Each of those steps gets its own agent in its
own git worktree. The executor merges their work back in step order, one commit per
step. When all steps are done, it moves the plan to `plans/completed/` and offers to
squash-merge locally or open a PR.

**Example**

```
/quiz-plan-execute plans/add-api-rate-limiting.plan.md
```

GATED steps pause for human review; AUTO steps continue. If a step conflicts with Intent
or Boundaries, the executor stops and asks. The executor doesn't resolve the conflict
itself.

---

## `pdlc` — Development Lifecycle Harness

A Claude Code plugin that runs your project's development lifecycle. Intents enter an
inbox, become job, capability and design specs, then small changes that each touch one
job or one capability. pdlc builds each change test first. An independent reviewer
checks the change, and you approve it. Every commit traces back to its requirement and
intent.

It fits any kind of system, and can manage changes to this repository, including
changes to pdlc itself.

Unlike the skills above, pdlc installs as a plugin from this repo's marketplace:

```
/plugin marketplace add ptetau/pskills
claude plugin install pdlc@pskills --scope project
```

Full steps are in `plugins/pdlc/INSTALL.md`.

Skills: `ship` (runs everything), `init`, `intake`, `ready`, `change`, `tests`, `build`,
`show`, `verify`, `conventions`, `trace`, `board`, `dashboard` (optional live dashboard).
Agents: `recon`, `test-writer`, `builder`, `reviewer`. Read `plugins/pdlc/OUTLINE.md` for the design and
`plans/build-pdlc-v1.plan.md` for build progress.

**Example**

```
/pdlc:init
/pdlc:ship let users reset their password by email
```

---

## `/squiz` — Visual Clarifier Document

The document-mode twin of `/quiz`. Instead of one-at-a-time questions, the
[squiz](https://github.com/squiz-cli/squiz) Go binary renders a self-contained
interactive HTML document with all decisions at once. The document has retro Apple //e
styling and mini-wireframe previews for visual options.

The user fills it in at their own pace and pastes a single JSON payload back.

**Example**

```
/squiz a mobile onboarding flow for a habit-tracking app
```

Squiz renders an HTML doc covering every decision (layout, tone, data model,
progression logic). The user fills in each section and pastes the JSON result
back. Claude then reads the payload and begins implementation.

Requires the `squiz` binary: see [squiz releases](https://github.com/squiz-cli/squiz/releases).

Prefer `/quiz` for small sets of textual questions. If decisions are visual, numerous,
or benefit from seeing all options side by side, use `/squiz`.

---

## `/vet` — Skill Evaluator

Writes and runs an eval for another skill. A good skill meets its own rubric and gives
much the same output every time, so `/vet` scores both:

1. Reads the skill's SKILL.md and extracts the expected **output structure** and a
   **rubric** (`structure`, `behavior` and `outcome` items, weighted, each citing its
   source)
2. Writes **10 varied test prompts**, with scripted user replies for interactive skills
3. Asks **which models** to use for the skill and for the judges, the biggest variable
   in any eval
4. Runs **3 prompts × 10 repeats** in waves, each run in its own git worktree, in
   parallel via a `Workflow`
5. **Rubric judges** grade every run: met / partial / missed / n/a, with evidence
6. **Similarity judges** (one per prompt per wave by default) place each new run into
   the groups so far, for each rubric item. A similarity judge classifies each new run:
   identical → equivalent → minor drift → major drift → contradictory. The judges also
   compare structure items across prompts. The script tallies each split, e.g.
   `7 / 3 of 10`
7. Scores **quality**, **stability**, and **overall** = √(quality × stability). It
   records the grade after every wave, so you can watch the grade **settle**. To stop
   early once the grade settles, add `--stop-when-settled`

You choose what each agent does. Four roles (`run`, `grade`, `compare`, `cross`) each
take a model, effort and batching. Presets set the batching:

| Preset | Agents, 3 × 10 runs in waves of 2 | One wave (`--wave 10`) | Judges |
|---|---|---|---|
| `thorough` | up to 213 | 93 | one per run, one per rubric item |
| `lean` (default) | up to 61 | 37 | one grader and one comparer per prompt |
| `minimal` | up to 46 | 34 | one judge per prompt grades and compares |

Override per role in `evals/agents.json` or per run, e.g.
`/vet quiz --agent grade.model=<model> --agent grade.effort=low`.

`/vet` saves the suite to `evals/<skill>/suite.json` and reuses it, so later runs are
comparable. You review the rubric and prompts once, when `/vet` first writes a suite.

**Example**

```
/vet quiz
```

**Output (excerpt)**

```
wave 1/5 (2 of 10 runs per prompt): quality 90.2 · stability 81.0 · overall 85.5 (B) · settling
wave 2/5 (4 of 10 runs per prompt): quality 88.4 · stability 75.3 · overall 81.6 (B) · moved -3.9 · settling
wave 3/5 (6 of 10 runs per prompt): quality 88.1 · stability 74.1 · overall 80.8 (B) · moved -0.8 · settling
wave 4/5 (8 of 10 runs per prompt): quality 88.0 · stability 74.4 · overall 80.9 (B) · moved +0.1 · settled

Quality 88 · Stability 74 · Overall 80.7 (B)    30/30 runs usable · settled at wave 4

Where it varies
  R5 question order · P02 — major_drift
    6 runs (P02#1,#2,#4,#6,#7,#9): asks about audience first
    4 runs (P02#3,#5,#8,#10):      asks about scope first
```

Writes `evals/quiz/runs/<runId>/report.md`, `results.json`, and one capture per run.
Options: `--prompts N`, `--sample M`, `--runs R`, `--use P02,P07`, `--regen`,
`--wave W`, `--stop-when-settled`, `--preset`, `--agent role.key=value`.

