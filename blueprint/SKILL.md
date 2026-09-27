---
name: blueprint
description: >
  Turns a system design (a /decompose design document, or any architecture doc) into
  an Agent System Design Document: a spec a person can skim and a coding agent can
  implement without guessing. Six sections: scope boundaries, enforceable invariants
  with error codes, strongly typed data contracts, explicit state machines, module
  boundaries with typed method signatures and failure and retry semantics, and a
  Gherkin verification suite. Every detail the design leaves open is decided once,
  marked as assumed, and listed for review. Removes methodology jargon and IDs, then
  checks the result with a bundled checker and writes a blueprint document. Use when
  the user says "/blueprint", asks to turn a design into a spec, make a design
  agent-ready or implementable, write the types, interfaces, contracts, or acceptance
  tests for a design, or wants the next step after /decompose.
---

# Blueprint: from design to buildable spec

## Purpose

A design document explains *why* the system is shaped the way it is. A coding agent needs
*what exactly* to build: types, error codes, state transitions, method signatures, and
tests that say when it is done. Hand an agent the design alone and it will invent those
details, differently each time.

`/blueprint` rewrites a design into an **Agent System Design Document** (a blueprint) with
six sections:

1. **Header and boundary box**: what the system is, how it is deployed, what is in and out
   of scope, and every decision the blueprint added.
2. **System invariants**: 4–7 enforceable rules, each with where it is enforced and the
   error code it raises.
3. **Core data contracts**: exact types, not prose.
4. **State machines**: every lifecycle, with guards, terminal states, and illegal moves.
5. **Module boundaries and interface signatures**: every component's purpose, constraints,
   typed methods, and failure and retry behavior.
6. **Verification suite**: 3–5 Gherkin scenarios that exercise every invariant.

A person reads it top to bottom in minutes. A coding agent can scaffold the directories,
types, and test harness from it directly.

It is the companion to [[decompose]]: `/decompose` decides the walls and bricks and proves
them; `/blueprint` makes them buildable. After it, [[quiz-plan]] turns the blueprint into
steps, and [[quiz-plan-execute]] implements them, using the Gherkin scenarios as its failing
tests.

## When to use this skill

Use `/blueprint` when:
- The user says `/blueprint`, or asks to turn a design into a spec, or to make a design
  agent-ready or implementable.
- There is a design document (ideally a `name.design.md` from `/decompose`) and the next
  step is building it.
- The user asks for the types, interfaces, contracts, or acceptance tests of a design.

Do **not** use it when:
- There is no design yet. Run [[decompose]] first. (If the user insists, work from what they
  gave, and expect many more assumed decisions.)
- The user wants a step-by-step change plan. That is [[quiz-plan]], which can take the
  blueprint as input.

## The core rule: never guess silently

The design will leave details open: a retry count, an idempotency key format, a storage
engine, an error code's name, a time zone. The blueprint must decide them, because an agent
that meets an open question guesses, and each agent guesses differently.

So every detail that the source does not state is a **decision added by this spec**:

1. Decide it once, choosing the conventional default (`references/conventions.md`).
2. Mark it inline with *(assumed)*.
3. List it in section 1 under **Decisions added by this spec**, with one line on what
   changes if it is wrong.

A person reviews that list once. After that, nothing in the blueprint is a guess.

If a decision would change the design itself (a new component, a different call path), do
not make it. Stop and ask, or send the user back to `/decompose`.

## Inputs and how a design maps

Read the design in full, and in subsystem mode read the host codebase: its language,
framework, directory conventions, error handling, and existing types. The blueprint follows
the host's conventions over this skill's defaults.

From a `/decompose` design document:

| Design section | Goes to | How |
|----------------|---------|-----|
| Frame, users, constraints, assumptions | 1. Header | Purpose, target mode, scope; carry assumptions into *Decisions added* |
| Nature of the business | 2. Invariants | Each fact that must never be violated becomes an enforceable rule |
| Features and core use cases | 1. In scope; 5. Manager methods | Features become scope bullets; each core use case becomes a Manager method with its call sequence |
| Volatility register | 5. "Absorbs change" line | Each component states, in plain words, the change it contains |
| Rejected candidates, cut list | 1. Out of scope | As non-goals |
| Walls: components, APIs, call rules | 5. Modules | Grouped by type; the call rules become each component's "May call" line |
| Bricks and shared contracts | 3. Contracts; 5. Internals | Contracts become types; bricks become private modules inside their component |
| State machines | 4. State machines | Redrawn with guards, terminal states, and illegal transitions |
| Feature assembly, walkthroughs | 5. Flows; 6. Scenarios | Call sequences under each Manager method; key features become scenarios |
| Validation results | — | Stays in the design; link to it |
| Seams and migration | 1. Scope; 5. Translation at the seam | Migration steps belong to the change plan, not the blueprint |
| Risks and open questions | 1. Decisions added, or stop and ask | Resolve each one, or ask |

Any other design format works the same way: find the scope, rules, data, lifecycles,
components, and behaviors, and translate each.

## Phase 0 — Choose the target

1. **Language.** Use the host codebase's language. With no host, use the language the user
   names; otherwise ask once, offering TypeScript as the default. All code blocks in the
   blueprint use that one language.
2. **Target mode.** The deployment style: a modular monolith by default, services only if
   the design calls for separately deployed parts. Say it in one line.
3. **Name.** `name.blueprint.md`, next to the design document.

## Phase 1 — Header and boundary box

- **System** and **target mode** on one line each.
- **In scope**: what gets built, as features in the user's words.
- **Out of scope (non-goals)**: rejected candidates, future changes that are only tests of
  the design, and anything else a reasonable agent might wander into.
- **Decisions added by this spec**: every *(assumed)* detail, one line each.
- A link to the source design.

## Phase 2 — Invariants

Write 4–7 rules that must hold no matter what: design by contract's invariants, made
concrete. Find them in the nature of the business, the Engines' rules, the state machines,
the atomicity notes, and anything a duplicate or a retry could break.

Each invariant states:
- **The rule**, in one sentence a tester could check.
- **Where it is enforced**: `Component.method`, and the transaction boundary if the check
  must be atomic with a write.
- **The error code** raised when something tries to break it, in `UPPER_SNAKE_CASE`.

Always cover, where they apply: idempotency (what makes two requests "the same", and what
happens on a replay), immutability (what can never change once written), and the hard
rejections (what the system refuses, and with which code).

## Phase 3 — Data contracts

Translate every shared contract, record, and API payload into exact types, in one code
block per module or one for the whole domain. Rules (details in `references/conventions.md`):

- **Make illegal states unrepresentable.** Unions for enums and states, not strings;
  separate types for separate states when their fields differ.
- **Required vs optional is explicit** on every field.
- **Identifiers are distinct types** (branded types in TypeScript, newtypes in Go and Rust),
  so an `OrderId` can't be passed as a `CustomerId`.
- **Money is an integer in minor units plus an ISO 4217 currency code.** Never a float.
- **Time is one explicit convention** (for example ISO 8601 UTC strings), stated once.
- **Errors are data**: an `ErrorCode` union holding every code in the blueprint, and a
  result or error type that carries it.
- No `any`, no untyped maps where the shape is known.

## Phase 4 — State machines

Draw every lifecycle: every `...Status` or `...State` type in section 3 gets one. Use a
Mermaid `stateDiagram-v2` (or ASCII when Mermaid won't render), with:

- `[*]` for the start, and terminal states marked.
- Each transition labeled `event [guard]`.
- Held, waiting, and rollback branches shown, not implied.
- One line under the diagram: where the state is stored, which method performs each
  transition atomically, and the error code for an illegal transition.

## Phase 5 — Module boundaries and signatures

1. **Module map**: a directory tree an agent can create as is, one folder per component,
   with contracts and tests placed.
2. **Groups**, named for what they do, with the method's term in brackets:
   Entry points (Clients), Orchestration (Managers), Business rules (Engines),
   Resource access (ResourceAccess), Shared infrastructure (Utilities).
3. **Per component**, as a `#### ComponentName` subsection:
   - **Purpose**: one line.
   - **Absorbs change**: the likely change it contains, in plain words.
   - **Constraints**: Engines are pure and in-memory, with no network, storage, clock, or
     randomness (inject them). ResourceAccess is the only code that touches a vendor or
     storage. Managers orchestrate and hold no business rules.
   - **May call**: from the design's call rules.
   - **Signatures**: a typed interface: business verbs, parameter and return types, and the
     error codes each method can return.
   - **Flows** (Managers): each public method's call sequence, one call per line.
   - **Failure and retry**: which errors are retryable and which are final, timeouts,
     backoff, idempotency on retry, and how races resolve.
   - **Internals** (optional): the component's bricks, as private modules.

## Phase 6 — Verification suite

Write 3–5 Gherkin scenarios that a test harness can run.

- **Cover**: idempotency and duplicate execution; the hard rejections and guardrails; state
  transitions, including an illegal one and an immutability check.
- **Every invariant's error code appears in at least one scenario.** Use a
  `Scenario Outline` with an `Examples` table to cover a family of rejections in one
  scenario.
- **Declarative steps**: state *what* happens in domain terms, not clicks, URLs, or SQL.
- **Concrete values**: real IDs, amounts, and times in the steps, so each scenario is a key
  example, not a description.
- Each scenario tests one behavior, with `Given`, `When`, and `Then` in that order.

## Phase 7 — Check and deliver

1. Run the checker and fix until it passes:

   ```
   python <skill-dir>/scripts/check_blueprint.py name.blueprint.md
   ```

   It checks structure, invariant enforcement points and codes, that every state type has a
   state machine, that every component has signatures and failure semantics, that every
   invariant's code is exercised by a scenario, that no scenario uses an undefined code,
   and that no design IDs such as `V1` or `F2` remain. With `--compile` it also type-checks
   TypeScript blocks when `tsc` is installed.
2. Re-read the blueprint as the coding agent: for each section, could you write the code or
   test without asking a question? Any question you would ask is a missing decision. Add it
   to *Decisions added*, or ask the user.
3. Show a summary in chat:

   ```
   BLUEPRINT: <name> · <language> · <target mode>
   ══════════════════════════════════════════════════
   SCOPE        <n> in · <n> out
   INVARIANTS   <n> · codes: <CODE_A, CODE_B, …>
   CONTRACTS    <n> types · <n> state machines
   MODULES      <n> components in <n> groups
   SCENARIOS    <n> · every invariant exercised
   ASSUMED      <n> decisions for review
   CHECK        PASS
   ```

4. Offer next steps: review the *Decisions added* list; `/quiz-plan` to turn the blueprint
   into steps; `/quiz-plan-execute` to build it, with the scenarios as its failing tests.

## Style

- **Zero fluff.** Lead each section with its substance. No introductions, no summaries of
  what the reader is about to read.
- **Plain domain terms.** No design IDs (`V1`, `F2`, `UC3`). Methodology terms appear once,
  in brackets, in the group headings of section 5.
- **Scannable.** Tables and short bullets; code where precision matters; each section
  readable on its own.
- **Agent-ready.** An agent with no other context can create the directory tree, the type
  definitions, and the test harness from this document alone.
- **Faithful.** Never change the design's components or call rules. If the design is wrong,
  say so and stop; don't quietly redesign it in the blueprint.

## References

- `references/blueprint-template.md`: the document's exact shape, which the checker expects.
- `references/conventions.md`: default decisions (money, time, IDs, idempotency, errors,
  retries, Gherkin style) and where each comes from.
- `references/notifications.blueprint.md`: a worked blueprint of `/decompose`'s
  notifications example. It passes the checker.
- `references/sources.md`: the sources behind the conventions.
- `scripts/check_blueprint.py`: the checker. Standard library only.
