# pskills

pskills is a collection of Claude Code skills. To install a skill, copy its folder into
`~/.claude/skills/`. Claude Code finds the skill automatically.

All text in this repository obeys `WRITING-GUIDELINES.md`. The guidelines are ASD-STE100
Simplified Technical English (STE), and two more rules:

- A pronoun refers only to a noun in the same paragraph.
- Each ID has a short description.

Each skill has a copy of the writing guidelines in `references/writing-guidelines.md`. The
skills use the writing guidelines for their replies and for each file that they write. See
"Writing guidelines" below.

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
      notifications.design.md
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
  quiz-visual/
    SKILL.md
    examples/
      summit-welcome.quiz.html
      summit-welcome.quiz.json
    references/
      page-template.html
      preview-kinds.md
      spec.md
      writing-guidelines.md
    scripts/
      check_quiz.py
      check_writing.py
      render_quiz.py
      test_page_browser.js
      test_quiz_visual.py
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

## The chain: decompose, blueprint, pdlc

`/decompose`, `/blueprint`, and `pdlc` work as one chain for a new system. Each tool takes the
output of the tool before it. You can also use each tool alone.

| Step | Tool | The question | The output |
|---|---|---|---|
| 1 | `/decompose` | Where do the walls go? | `<name>.design.md` |
| 2 | `/blueprint` | What exactly gets built? | `<name>.blueprint.md` |
| 3 | `/pdlc:intake` | How does it become verified code? | specs, changes, checks, and code |

The commands, in order:

```
/decompose a notifications service
/blueprint notifications.design.md
/pdlc:init
/pdlc:intake notifications.blueprint.md
```

The same idea has a different name in each tool. This table gives the match:

| In the blueprint | In pdlc |
|---|---|
| The in-scope list of section 1 | "What and why" of the intent |
| An invariant, with its enforcement point | A requirement of the capability that enforces the rule |
| The error table: code, meaning, fault | The rows of `DES-errors`: code, meaning, whose fault |
| The signature of a method | The "Interface" of a change |
| A scenario (Given, when, then) | The acceptance lines of a requirement |
| An Engine or a ResourceAccess | A capability |
| A method of a Manager | A job |
| A decision marked `(assumed)` | The same mark, `(assumed)` |
| The fault words `caller`, `system`, and `outside service` | The same three words in `DES-errors` |

Four rules keep the chain consistent:

- The design and the blueprint are frozen inputs. After intake, the pdlc specs lead. To change
  the design later, run `/decompose` on the real code, then `/blueprint`, then
  `/pdlc:intake` again.
- The blueprint has no IDs. Intake gives each requirement its pdlc ID.
- The blueprint writes the mark `(assumed)` in plain form, with any reason outside the
  brackets. The pdlc merge check accepts that form, and any other mark that starts with
  `(assumed`.
- `/decompose` and `/blueprint` use the master writing check. It has a reading grade of 7 and
  a glossary rule. pdlc has a smaller check, with four rules.

---

## Writing guidelines

`WRITING-GUIDELINES.md` is the standard for all text in this repository. The file is also
the standard for all text that the skills write. The file has three parts:

1. The 53 rules of ASD-STE100 Simplified Technical English, Issue 9, in short form.
2. The local-references rule. A pronoun or a short noun refers only to a noun in the same
   paragraph. A new paragraph, list item, or reply starts with the full noun.
3. The described-IDs rule. Each ID has a short description in the same sentence. A
   question with alternatives gives the description of each alternative.

The STE standard and its dictionary are free from <https://www.asd-ste100.org>. ASD does
not let other persons distribute the standard or the dictionary. Thus, this repository has
only a short form of the rules. To examine words against the dictionary, give the linter
your copy:

```
python3 improve-writing/scripts/check_writing.py FILE.md --dictionary ASD-STE100.pdf
```

**Change the guidelines.** Edit only `WRITING-GUIDELINES.md`. Then run
`python3 scripts/sync_shared.py`. The script copies the guidelines into each skill. The
script also writes the `pdlc` design spec `DES-writing-style.md`, which has the same rules.

**Make the guidelines your default writing style.** To make Claude Code use the guidelines
in all your projects, copy `WRITING-GUIDELINES.md`. Then import the copy in your personal
`CLAUDE.md`:

```
cp WRITING-GUIDELINES.md ~/.claude/WRITING-GUIDELINES.md
echo '@~/.claude/WRITING-GUIDELINES.md' >> ~/.claude/CLAUDE.md
```

For a tool that reads `AGENTS.md`, copy the "Writing" section of the `AGENTS.md` file of
this repository into your personal `AGENTS.md`.

---

## `/argue` — Logical Contradiction Detector

Paste any text (spec, plan, essay, argument). Then `/argue` does these steps:

1. `/argue` divides the pasted text into discrete logical claims (C1, C2, …).
2. `/argue` encodes each claim in propositional logic.
3. `/argue` runs **Z3** as a deterministic SAT solver to prove hard contradictions.
4. `/argue` uses reasoning to flag tensions and ambiguities.
5. `/argue` gives an annotated version of the original text, and a tiered summary.

The `z3-solver` package is necessary for `/argue`. To install the package, run
`pip install z3-solver`.

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

`/blueprint` is the companion to `/decompose`. A design document tells *why* the system
has its shape. But a coding agent must know *what exactly* to build. `/blueprint` rewrites
a design (a `name.design.md`, or any architecture doc) into an **Agent System Design
Document**. A person can skim this document, and an agent can implement it with no
guesses. The document has six sections:

1. **Header and boundary box**: purpose, target mode, in scope, out of scope.
2. **System invariants**: 4–7 enforceable rules. Each rule has the place where the system
   enforces the rule, and its error code.
3. **Core data contracts**: exact types (TypeScript, Go, or Rust).
4. **State machines**: each lifecycle, with guards, terminal states, and illegal moves.
5. **Module boundaries and signatures**: typed methods, constraints, and the failure and
   retry behaviour of each component.
6. **Verification suite**: 3–5 Gherkin scenarios that exercise each invariant.

Some details can stay open in a design, for example a retry count, a key format, or a
storage engine. `/blueprint` decides each open detail one time. Then `/blueprint` marks
the detail *(assumed)*, and lists the detail for review. Thus, an agent gets each detail,
and does not guess.

`blueprint/scripts/check_blueprint.py` checks the result for these conditions:

- The structure is correct.
- Each invariant has an enforcement point and an error code.
- A scenario exercises each error code.
- Each state type has a state machine.
- No design ID stays in the result (for example, `V1`).

With `--compile`, `check_blueprint.py` also type-checks the TypeScript.

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
holds). `/blueprint` also draws a C4 component diagram (who calls whom).
`check_blueprint.py` makes sure that the two diagrams agree with the text. `--render`
renders each diagram with Mermaid.

Give the output of `/blueprint` to `/quiz-plan` to get a change plan. Then run
`/quiz-plan-execute`. `/quiz-plan-execute` uses the Gherkin scenarios as its failing
tests.

**`/blueprint` and `/decompose` obey the writing guidelines.** The two skills write for a
bright 10-year-old, at a reading grade of 7 or lower. The sentences are short, and the
words are common. Each technical word is in a "Words used here" list. Names, types, and
error codes stay the same.

`check_writing.py` is the linter for the guidelines. `/blueprint` and `/decompose` each
have a copy of the linter. The linter measures the sentence length and the reading grade.
The linter also lists each technical word that has no entry in the "Words used here"
list.

---

## `/decompose` — Software Design by Volatility and Primitives

`/decompose` designs a new system (inception), or a new subsystem in an existing codebase.
`/decompose` makes the design in two passes, and then proves the result:

1. **Walls** — volatility-based decomposition. `/decompose` finds the items that are
   likely to change. Then `/decompose` puts each item behind one component:
   - Managers, for workflows that change.
   - Engines, for rules that change.
   - ResourceAccess, for storage and third parties that change.

   Thus, a change occurs in one place.
2. **Bricks** — orthogonal primitives. In each wall, `/decompose` builds a small set of
   independent parts (inputs, transforms, transports, stores, state machines). The parts
   share one contract. `/decompose` assembles each feature as a combination of the parts.
3. **Proof** — `/decompose` walks the core use cases through the walls. Then
   `/decompose` simulates each likely change (target: one component touched). Last,
   `/decompose` assembles current and future features from existing bricks (target: a
   maximum of one new brick).

`/decompose` draws its result as C4 diagrams:

- A system context diagram.
- A component diagram with one band for each layer. Each arrow in this diagram is an
  allowed call.

In an existing codebase, `/decompose` measures volatility from the git history, and does
not guess. `decompose/scripts/volatility.py` reports component churn, change coupling, and
hotspots. The script is standard-library Python, and works on Windows.

The output of `/decompose` is a `<name>.design.md` file. The file has the volatility
register, walls, bricks, feature assembly, and validation results. For a subsystem, the
file also has the seam and the migration steps.

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

Give the `<name>.design.md` file to one of these skills for the next step:

- `/argue`, to find contradictions in the design.
- `/blueprint`, to make the design agent-ready.
- `/quiz-plan`, to make a change plan from the design.

---

## `/improve-writing` — Rewrite Text to the Writing Guidelines

`/improve-writing` writes a file or a skill again, so that the text obeys
`WRITING-GUIDELINES.md`. The meaning, the facts, the code, and the quoted text stay the
same.

```
/improve-writing <path> [<path> …] [--no-eval] [--dictionary PATH]
```

For a document, `/improve-writing` writes the text again and runs the linter. The skill
stops when the linter shows no findings, or only findings with a recorded reason.

A rewrite can change what a skill does. Thus, for a skill or a prompt, `/improve-writing`
does these steps:

1. `/improve-writing` records each behaviour of the old version in a list, the behaviour
   inventory.
2. `/improve-writing` writes the text again.
3. `/improve-writing` makes sure that the rewrite keeps each behaviour in the inventory.
4. `/improve-writing` runs `/vet` on the old version and on the new version, with the
   same suite and the same models.
5. `/improve-writing` compares the two results with `compare_vet.py`. The script shows
   "REGRESSION" in these conditions:
   - The overall score falls more than 5 points.
   - A weight-3 rubric item falls more than 20 points.
   - Fewer runs are usable.

**Output (excerpt)**

```
| File          | Findings before | Findings after | Inventory     | Baseline | Rewrite | Result        |
|---------------|-----------------|----------------|---------------|----------|---------|---------------|
| quiz/SKILL.md | 46              | 0              | 34 of 34 kept | 82.1     | 83.0    | NO REGRESSION |
```

`/improve-writing` does not commit. You examine the change first.

---

## `/probe` — Exploratory Tester

`/probe` does autonomous, exploratory bug hunting in a running app. First, `probe` reads
the docs and specs, the commit history, and the code. From these sources, `probe` builds
an app map and derives the user-facing feature flows. Then `probe` starts a **flow ×
dimension** matrix of read-only probe agents (a fan-out, through a `Workflow`). Each agent
first examines the code statically. Then the agent drives the live app with no
destructive action, and records surprises and bugs with a repro and evidence.

An adversarial verify pass removes the false positives. Then `probe` writes a Markdown
report, ranked by severity, and a machine-readable JSON findings file.

Each probe agent is strictly read-only. A probe agent must not change the target app.

**Example**

```
/probe the staging checkout flow at https://staging.example.com
```

`probe` maps `checkout`, `sign-up`, and `apply-discount-code` as feature flows. Then
`probe` starts one read-only agent for each (flow, quality-dimension) cell. The quality
dimensions are functional, robustness, security, perf, a11y, and ux. Then `probe` runs the
adversarial verify pass on the raw findings, and writes these two files:

- `probe-report.md`: the ranked findings, with a repro and evidence for each finding.
- `probe-findings.json`: the findings, which validate against
  `probe/references/findings.schema.json`.

---

## `/quiz` — Inline Clarifier

`/quiz` asks clarifying questions, one at a time, before the work starts. The answers lock
the decisions (audience, scope, tone, approach). A back-and-forth prose conversation is
not necessary. Each question is a native picker that the user clicks. If there is no
picker, each question is a short plain-markdown question, and the user answers with a
letter.

`/quiz` plans its questions first, in a fixed order (purpose, style, scope, focus, next
step). Thus, the same request gets the same questions. `/quiz` recommends an option only
when something that the user said points to that option.

**Example**

```
/quiz a dashboard that shows real-time API health metrics
```

**Output** (plain-markdown fallback. With a picker, you can click the same options.)

> **Question 1 of 3 · Audience**
> Who is the primary audience for this dashboard?
>
> - **A · Engineers**: shows raw, dense metrics with no extra text, but it is hard for
>   anyone outside the team to read.
> - **B · Managers**: shows trends and status instead of raw numbers, but it hides the
>   detail that on-call staff need.
> - **C · Both**: gives an overview with a drill-down toggle, but it takes more work to
>   build.
>
> Reply A, B, or C. You can add a note, for example `B, keep it short`.

Reply with a letter. You can add a note (`B, include p99 latency`). `/quiz` echoes each
answer in one line (`✓ 1/3 Audience → Managers`). After the last question, `/quiz` shows
the resolved list for a final OK before the work starts.

`/quiz` has a limit of about 7 questions. When the options differ in how they look, sound, or work, use `/quiz-visual`.

---

## `/quiz-plan` — Quiz-driven Change Plan

`/quiz-plan` runs an adaptive interview, not a fixed list. The interview finds each
assumption, ambiguity, and dependency in a proposed change. Then `/quiz-plan` writes a
structured `<name>.plan.md` in the `plans/` folder at the project root. The plan has these
parts: Intent, Ground truth, Boundaries, gated Steps, Verification/rollback, and a live
progress tracker. Step 1 always tests the riskiest assumption.

**Example**

```
/quiz-plan add rate limiting to the public API routes
```

`/quiz-plan` asks more and more specific questions, for example "configurable or hardcoded
limit?", "which middleware dir?", and "what must not change?". `/quiz-plan` continues
until it can see the exact files and changes. Then `/quiz-plan` asks the user to confirm.
After that, `/quiz-plan` writes `plans/add-api-rate-limiting.plan.md`. The plan has a gate
for each step (AUTO / GATED), and a 12-character progress bar in the header.

---

## `/quiz-plan-execute` — Plan Executor (TDD, per-step commits)

`/quiz-plan-execute` is the executor twin of `/quiz-plan`. `/quiz-plan-execute` reads a
`.plan.md`, and completes each step through a strict 6-stage gate. Each stage must finish
before the next stage starts:

1. **Understand** the acceptance criteria (the `Done when` of the step).
2. **Red** — write the failing test.
3. **Green** — write the minimum implementation that passes the test.
4. **Refactor** — remove duplication, obey the conventions, and decrease the complexity.
5. **Review** the work against the acceptance criteria.
6. **Commit** — make one commit for each step. Update the plan tracker in the same commit.

At the start, `/quiz-plan-execute` asks one question: whether to make a new branch. At
the end, `/quiz-plan-execute` offers to squash-merge locally or to open a PR.

**Example**

```
/quiz-plan-execute add-api-rate-limiting.plan.md
```

A GATED step pauses for human review. An AUTO step continues. If a conflict with the
Intent or the Boundaries occurs, `/quiz-plan-execute` stops and asks. `/quiz-plan-execute`
does not resolve the conflict itself.

---

## `/quiz-visual` — Visual Clarifier Page

`/quiz-visual` asks the questions on one HTML page. Each option shows its result, so the
user picks what they see. The rule is **show, do not tell**. Each kind of difference has its
own preview:

- A tone is a sample of the real words.
- A layout is a wireframe.
- A colour scheme is a palette in use.
- A flow is a diagram.
- A behaviour is a small prototype that the user clicks.

**Example**

```
/quiz-visual a welcome email for new members of my climbing gym
```

The skill plans a fixed list of questions, writes them as `<name>.quiz.json`, and renders
`<name>.quiz.html` with `scripts/render_quiz.py`. The checker `scripts/check_quiz.py` makes
sure that the page is complete and that the words follow the writing guidelines.

The user opens the page in any browser and answers. A sticky list shows the progress. Each
question has a note field and a **You decide** button. At the end, **Copy answers** puts the
answers on the clipboard, and the user pastes them into the chat. In the Claude app, the
skill also publishes the page as an Artifact. The page then has a **Send answers to the
agent** button, and the skill reads the answers itself.

The page follows the theme of the system, in light and in dark. The page works on a phone.
A finished example is in `quiz-visual/examples/summit-welcome.quiz.html`.

Usually, use `/quiz` when words answer the question, for example a name or a date. Use
`/quiz-visual` when the options differ in how they look, sound, or work.

---

## `pdlc` — Development Lifecycle Harness

`pdlc` is a Claude Code plugin that runs the development lifecycle of your project.
Intents go into an inbox. Then the intents become job, capability, and design specs. Then
the specs become small changes, and each change touches one job or one capability.

`pdlc` builds each change test first. An independent reviewer checks the change, and you
approve the change. Each commit traces back to its requirement and its intent.

`pdlc` fits all types of system. `pdlc` can also manage changes to this repository, and
changes to `pdlc` itself.

`pdlc` runs only on a Sonnet 5.5 class model or above. On a lower model, for example a
Haiku model, each `pdlc` skill and agent does no work. The skill or agent tells you that
`pdlc` needs a Sonnet 5.5 class model or above.

`pdlc` does not install like the skills above. `pdlc` installs as a plugin from the
marketplace of this repository:

```
/plugin marketplace add ptetau/pskills
claude plugin install pdlc@pskills --scope project
```

`plugins/pdlc/INSTALL.md` gives the full steps.

`pdlc` has these skills: `ship` (runs everything), `init`, `intake`, `ready`, `change`,
`acceptance`, `tests`, `build`, `show`, `verify`, `conventions`, `trace`, `board`, and
`dashboard` (optional live dashboard). Each skill states its goal, its constraints, its
inputs, and its outputs, and the model decides how to reach the goal. `pdlc` has these agents: `recon`, `test-writer`, `builder`, and
`reviewer`. For the design, read `plugins/pdlc/OUTLINE.md`. For the build progress, read
`plans/build-pdlc-v1.plan.md`.

**Example**

```
/pdlc:init
/pdlc:ship let users reset their password by email
```

---

## `/vet` — Skill Evaluator

`/vet` writes and runs an eval for a different skill. A good skill meets its own rubric. A
good skill also gives almost the same output each time. `/vet` scores the two qualities
with these steps:

1. `/vet` reads the SKILL.md of the target skill. `/vet` extracts the expected **output
   structure** and a **rubric** (`structure`, `behavior`, and `outcome` items, weighted,
   each with a citation of its source).
2. `/vet` writes **10 varied test prompts**. For an interactive skill, `/vet` also writes
   scripted user replies.
3. `/vet` asks **which models** to use for the skill and for the judges. The models are
   the biggest variable in an eval.
4. `/vet` runs **3 prompts × 10 repeats** in waves, in parallel through a `Workflow`. Each
   run is in its own git worktree.
5. **Rubric judges** grade each run: met / partial / missed / n/a, with evidence.
6. **Similarity judges** (by default, one for each prompt in each wave) put each new run
   into the current groups for each rubric item. The judges classify the run on this
   scale: identical → equivalent → minor drift → major drift → contradictory. Structure
   items are also compared across prompts. The `Workflow` script counts each split, for
   example `7 / 3 of 10`.
7. `/vet` scores **quality**, **stability**, and **overall** = √(quality × stability).
   `/vet` records the grade after each wave, so you can watch the grade **settle**. To
   stop early when the grade settles, add `--stop-when-settled`.

You select what each agent does. Each of the four roles (`run`, `grade`, `compare`,
`cross`) has its own model, effort, and batching. The presets set the batching:

| Preset | Agents, 3 × 10 runs in waves of 2 | One wave (`--wave 10`) | Judges |
|---|---|---|---|
| `thorough` | up to 213 | 93 | one per run, one per rubric item |
| `lean` (default) | up to 61 | 37 | one grader and one comparer per prompt |
| `minimal` | up to 46 | 34 | one judge per prompt grades and compares |

You can override a role in `evals/agents.json`, or for one run, for example
`/vet quiz --agent grade.model=<model> --agent grade.effort=low`.

`/vet` saves the suite to `evals/<skill>/suite.json`, and uses the suite again. Thus, you
can compare later runs. You examine the rubric and the prompts one time, when `/vet` first
writes a suite.

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

`/vet` writes `evals/quiz/runs/<runId>/report.md`, `results.json`, and one capture for
each run. `/vet` has these options: `--prompts N`, `--sample M`, `--runs R`,
`--use P02,P07`, `--regen`, `--wave W`, `--stop-when-settled`, `--preset`,
`--agent role.key=value`.

---

## Words used here

- **Decomposition**: the division of a system into components.
- **Deterministic**: gives the same result each time for the same input.
- **Invariant**: a rule that must always be true in the system.
- **Orthogonal**: independent. A change to one part does not change a different part.
- **Primitive**: a small, basic part that does one job.
- **Volatility**: how likely an item is to change.
