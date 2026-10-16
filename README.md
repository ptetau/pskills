# pskills

A collection of Claude Code skills. To install a skill, copy its folder into
`~/.claude/skills/`. Claude Code finds the skill automatically.

All text in this repository obeys `WRITING-GUIDELINES.md`: ASD-STE100 Simplified Technical
English, and two more rules. A pronoun refers only to a noun in the same paragraph, and
each ID has a short description. Each skill has a copy of the guidelines in
`references/writing-guidelines.md`. The skills use the guidelines for their replies and
for each file that they write. See "Writing guidelines" below.

```
~/.claude/skills/
  argue/
    SKILL.md
    references/
      writing-guidelines.md
  blueprint/
    SKILL.md
    references/
      blueprint-template.md
      c4.md
      conventions.md
      notifications.blueprint.md
      sources.md
      writing-guidelines.md
    scripts/
      check_blueprint.py
      check_writing.py
  decompose/
    SKILL.md
    references/
      bricks.md
      brownfield.md
      c4.md
      design-template.md
      examples.md
      sources.md
      walls.md
      writing-guidelines.md
    scripts/
      check_writing.py
      volatility.py
  improve-writing/
    SKILL.md
    references/
      writing-guidelines.md
    scripts/
      check_writing.py
      compare_vet.py
      test_check_writing.py
  probe/
    SKILL.md
    references/
      findings.schema.json
      report-template.md
      writing-guidelines.md
  quiz/
    SKILL.md
    references/
      writing-guidelines.md
  quiz-plan/
    SKILL.md
    references/
      writing-guidelines.md
  quiz-plan-execute/
    SKILL.md
    references/
      writing-guidelines.md
  squiz/
    SKILL.md
    references/
      writing-guidelines.md
  vet/
    SKILL.md
    references/
      agents.schema.json
      report-template.md
      results.schema.json
      suite.schema.json
      vet.workflow.js
      writing-guidelines.md
```

---

## Writing guidelines

`WRITING-GUIDELINES.md` is the standard for all text in this repository. It is also the
standard for all text that the skills write. It has three parts:

1. The 53 rules of ASD-STE100 Simplified Technical English, Issue 9, in short form.
2. The local-references rule. A pronoun or a short noun refers only to a noun in the same
   paragraph. A new paragraph, list item, or reply starts with the full noun.
3. The described-IDs rule. Each ID has a short description in the same sentence. A
   question with alternatives gives the description of each alternative.

The STE standard and its dictionary are free from <https://www.asd-ste100.org>. ASD does
not let other persons distribute them, so this repository has only a short form of the
rules. To examine words against the dictionary, give the linter your copy:

```
python3 improve-writing/scripts/check_writing.py FILE.md --dictionary ASD-STE100.pdf
```

**Change the guidelines.** Edit only `WRITING-GUIDELINES.md`. Then run
`python3 scripts/sync_shared.py`. The script copies the guidelines into each skill. It
also writes the `pdlc` design spec `DES-writing-style.md`, which holds the same rules.

**Make the guidelines your default writing style.** To make Claude Code use the guidelines
in all your projects, copy the file and import it in your personal `CLAUDE.md`:

```
cp WRITING-GUIDELINES.md ~/.claude/WRITING-GUIDELINES.md
echo '@~/.claude/WRITING-GUIDELINES.md' >> ~/.claude/CLAUDE.md
```

For a tool that reads `AGENTS.md`, copy the "Writing" section of the `AGENTS.md` file of
this repository into your personal `AGENTS.md`.

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
DECISIONS    11 added for review + 0 carried from the design · 0 open questions
CHECK        PASS
```

It draws a C4 container diagram (what runs, and which parts each container holds) and a
C4 component diagram (who calls whom), and the checker confirms both match the text.
`--render` renders every diagram with Mermaid.

Hand the blueprint to `/quiz-plan` for a change plan, then `/quiz-plan-execute`, which uses
the Gherkin scenarios as its failing tests.

**The two skills obey the writing guidelines** and write for a bright 10-year-old, at a
reading grade of 7 or lower. Each technical word is in a "Words used here" list. Names,
types, and error codes stay the same. `check_writing.py` (in the two skills) is the linter
for the guidelines.

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

It draws the result as C4 diagrams: a system context diagram, and a component diagram
with one band per layer, where every arrow is an allowed call.

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

## `/improve-writing` — Rewrite Text to the Writing Guidelines

Writes a file or a skill again, so that the text obeys `WRITING-GUIDELINES.md`. The
meaning, the facts, the code, and quoted text stay the same.

```
/improve-writing <path> [<path> …] [--no-eval] [--dictionary PATH]
```

For a document, the skill writes the text again and runs the linter. The skill stops when
the linter shows no findings, or only findings with a recorded reason.

A rewrite can change what a skill does. Thus, for a skill or a prompt, the skill does
these steps:

1. It records each behavior of the old version in a list, the behavior inventory.
2. It writes the text again.
3. It makes sure that the rewrite keeps each behavior in the inventory.
4. It runs `/vet` on the old version and on the new version, with the same suite and
   the same models.
5. It compares the two results with `compare_vet.py`. The script shows "REGRESSION" if
   the overall score falls more than 5 points. It also shows "REGRESSION" if a weight-3
   rubric item falls more than 20 points, or if fewer runs are usable.

**Output (excerpt)**

```
| File          | Findings before | Findings after | Inventory     | Baseline | Rewrite | Result        |
|---------------|-----------------|----------------|---------------|----------|---------|---------------|
| quiz/SKILL.md | 46              | 0              | 34 of 34 kept | 82.1     | 83.0    | NO REGRESSION |
```

The skill does not commit. You examine the change first.

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

Asks clarifying questions one at a time before starting work, to lock in decisions
(audience, scope, tone, approach) without a back-and-forth prose conversation. Each
question is a native picker the user clicks, or, where there's no picker, a short
plain-markdown question answered with a letter.

It plans its questions up front in a fixed order (purpose, style, scope, focus, next
step), so the same request gets the same questions, and it recommends an option only
when something the user said points to it.

**Example**

```
/quiz a dashboard that shows real-time API health metrics
```

**Output** (plain-markdown fallback; with a picker the same options are clickable)

> **Question 1 of 3 · Audience**
> Who is the primary audience for this dashboard?
>
> - **A · Engineers**: raw metrics, dense, no fluff; hard for anyone outside the team to read.
> - **B · Managers**: trends and status rather than raw numbers; hides the detail on-call needs.
> - **C · Both**: an overview with a drill-down toggle; more to build.
>
> Reply A, B or C, optionally with a note.

Reply with a letter, optionally with a note (`B, include p99 latency`). Each answer is
echoed in one line (`✓ 1/3 Audience → Managers`), and after the last question the
resolved list is shown for a final OK before work begins.

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

## `pdlc` — Development Lifecycle Harness

A Claude Code plugin that runs your project's development lifecycle. Intents enter an
inbox, become job, capability and design specs, then small changes that each touch one
job or one capability. Changes are built test first, checked by an independent reviewer,
and approved by you. Every commit traces back to its requirement and intent.

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

---

## `/vet` — Skill Evaluator

Writes and runs an eval for another skill. A good skill meets its own rubric and gives
much the same output every time, so `/vet` scores both:

1. Reads the skill's SKILL.md and extracts the expected **output structure** and a
   **rubric** (structure, behavior and outcome items, weighted, each citing its source)
2. Writes **10 varied test prompts**, with scripted user replies for interactive skills
3. Asks **which models** to use for the skill and for the judges, the biggest variable
   in any eval
4. Runs **3 prompts × 10 repeats** in waves, each run in its own git worktree, in
   parallel via a `Workflow`
5. **Rubric judges** grade every run: met / partial / missed / n/a, with evidence
6. **Similarity judges** (one per prompt per wave by default) place each new run into
   the groups so far for each rubric item and classify it: identical → equivalent →
   minor drift → major drift → contradictory. Structure items are also compared across
   prompts. The script tallies each split, e.g. `7 / 3 of 10`
7. Scores **quality**, **stability**, and **overall** = √(quality × stability), and
   records the grade after every wave so you can watch it **settle**. Add
   `--stop-when-settled` to stop early once it does

You choose what each agent does. Four roles (`run`, `grade`, `compare`, `cross`) each
take a model, effort and batching. Presets set the batching:

| Preset | Agents, 3 × 10 runs in waves of 2 | One wave (`--wave 10`) | Judges |
|---|---|---|---|
| `thorough` | up to 213 | 93 | one per run, one per rubric item |
| `lean` (default) | up to 61 | 37 | one grader and one comparer per prompt |
| `minimal` | up to 46 | 34 | one judge per prompt grades and compares |

Override per role in `evals/agents.json` or per run, e.g.
`/vet quiz --agent grade.model=<model> --agent grade.effort=low`.

The suite is saved to `evals/<skill>/suite.json` and reused, so later runs are
comparable. You review the rubric and prompts once, when a suite is first written.

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

