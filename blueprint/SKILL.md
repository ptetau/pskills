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

A few questions can't be defaulted, because a wrong guess would be expensive. Mark those
inline as `[NEEDS CLARIFICATION: the specific question]`, at most three, choosing by
impact: scope first, then security, privacy, and legal compliance, then user experience, then technical
detail (GitHub spec-kit's rule). Ask the user to answer them. A blueprint with open
questions is a draft: the checker reports it as not agent-ready until they are resolved.

If a decision would change the design itself (a new component, a different call path), do
not make it. Stop and ask, or send the user back to `/decompose`.

## Inputs and how a design maps

Read the design in full, and in subsystem mode read the host codebase: its language,
framework, directory conventions, error handling, and existing types. The blueprint follows
the host's conventions over this skill's defaults.

From a `/decompose` design document (its sections are numbered as in
`decompose/references/design-template.md`):

| Design section | Goes to | How |
|----------------|---------|-----|
| §1 Frame: problem, users, constraints | 1. Header | System, target mode, scope; carry the design's assumptions into *Decisions added* |
| §1 Nature of the business | 2. Invariants | Each fact that must never be violated becomes an enforceable rule |
| §2 Features and core use cases | 1. In scope; 5. Flows | Features become scope bullets; each core use case becomes a flow across its Manager's methods |
| §3 Volatility register | 5. "Encapsulates" line | Each component states, in plain words, the change it encapsulates (the register's "Contained by") |
| §3 Rejected candidates; §7 Cut list | 1. Out of scope | As non-goals |
| §4 Walls: components, APIs, call rules | 5. Modules | Same components, same groups; each API verb becomes a method; the call rules become each component's "May call" line |
| §5 Shared contracts | 3. Contracts | Each contract becomes exact types, keeping its name |
| §5 Bricks | 5. Internals | Each brick becomes a private module inside its component |
| §5 State machines | 4. State machines | Redrawn with guards, terminal states, and illegal transitions; transitions named after the API verbs that perform them |
| §6 Feature assembly; §7 Walkthroughs | 5. Flows; 6. Scenarios | Each walkthrough becomes the flow under its Manager method; key features become scenarios |
| §7 Validation results | — | Stays in the design; link to it |
| §7 Accepted leaks | 1. Decisions added | Each one as a known limitation: which future change will touch two components |
| §6 Future features that failed assembly | 1. Out of scope | As a non-goal, with what it would cost |
| §8 Seams and migration | 1. Scope; 5. Translation at the seam | Migration steps belong to the change plan, not the blueprint |
| §1 Assumptions | 1. Decisions carried from the design | Carried as they are |
| §4 Cross-cutting concerns, atomic writes | 2. Invariants; 5. Constraints and Failure & retry | Each enforcement point becomes an invariant or a constraint; atomic writes name their transaction |
| §5 Composition medium, rule tables | 5. Internals; 3. Contracts | Say whether flows are code or data; a rule table becomes typed data |
| §9 Risks and open questions | 1. Decisions added, or `[NEEDS CLARIFICATION]` | Resolve each one, or ask |

**Names carry over unchanged.** Components keep their names (`RoutingEngine`). API verbs
become methods in the language's style: `Route` becomes `route` in TypeScript and stays
`Route` in Go. Contracts keep their names (`Envelope`) and their variants; narrowing or
widening a contract is a design change. A blueprint never adds, removes, or renames a
component or a verb; `--design` checks this.

**Lifecycles** follow the design: the Manager decides each transition, and when the state
outlives one flow, a ResourceAccess stores it and its verbs perform each transition
atomically. Section 4's "Stored by" line names that ResourceAccess.

**Business thresholds** the design leaves to a named owner ("Legal decides the expiry"):
choose a conservative placeholder, mark it *(assumed; owner: Legal)*, and list it. Use a
`[NEEDS CLARIFICATION]` only when no placeholder is safe to build against.

Any other design format works the same way: find the scope, rules, data, lifecycles,
components, and behaviors, and translate each.

## Phase 0 — Choose the target

1. **Language.** Use the host codebase's language. With no host, use the language the user
   names; otherwise ask once, offering TypeScript as the default. All code blocks in the
   blueprint use that one language.
2. **Target mode.** What gets built and how it runs, in one line: a browser app, a CLI, a
   library, a single service or modular monolith, or separately deployed services (only
   if the design calls for them). Then draw the **C4 container diagram**: each container
   (an app, a database, a queue) and the components it holds. Components are never split
   across containers; C4: "it's the container that's the deployable unit". With one
   container, one line saying so is enough. See `references/c4.md`.
3. **Name.** `name.blueprint.md`, next to the design document.

## Phase 1 — Header and boundary box

- **System** and **target mode** on one line each.
- **In scope**: what gets built, as features in the user's words.
- **Out of scope (non-goals)**: rejected candidates, future changes that are only tests of
  the design, and anything else a reasonable agent might wander into.
- **Decisions carried from the design**: the design's own assumptions, as they are.
- **Decisions added by this spec**: every *(assumed)* detail, one line each. Keeping the two
  lists apart keeps the new list short enough to review.
- **Words used here**: each technical word the blueprint uses, explained in one plain
  line.
- A link to the source design.

## Phase 2 — Invariants

Write the rules that must hold no matter what: design by contract's invariants, made
concrete. The format asks for 4–7, which suits most systems. A small domain may have
fewer; never pad with a rule the types already guarantee, or one only a buggy caller could
break. Find them in the nature of the business, the Engines' rules, the state machines,
the atomicity notes, and anything a duplicate or a retry could break.

Each invariant states:
- **The rule**, in one sentence a tester could check.
- **Where it is enforced**: `Component.method`, and the transaction boundary if the check
  must be atomic with a write.
- **The error code** raised when something tries to break it, in `UPPER_SNAKE_CASE`.

Name invariants; don't number them with IDs. The format's style rule bans cryptic IDs, and
a name like **Each message is delivered at most once** is its own reference.

Cover, where they apply: idempotency (what makes two requests "the same", and what
happens on a replay), immutability (what can never change once written), and the hard
rejections (what the system refuses, and with which code). If nothing can be repeated
harmfully, say so in one line instead of inventing an idempotency rule.

## Phase 3 — Data contracts

Translate every shared contract, record, and API payload into exact types, in one code
block per module or one for the whole domain. Rules (details in `references/conventions.md`):

- **Make illegal states unrepresentable.** Unions for enums and states, not strings;
  separate types for separate states when their fields differ.
- **Name every lifecycle type `...Status` or `...State`** (`DeliveryStatus`, `MatchState`), so
  readers and the checker can find its state machine.
- **Required vs optional is explicit** on every field.
- **Identifiers are distinct types** (branded types in TypeScript, newtypes in Go and Rust),
  so an `OrderId` can't be passed as a `CustomerId`.
- **Money is an integer in minor units plus an ISO 4217 currency code.** Never a float.
- **Time is one explicit convention** (for example ISO 8601 UTC strings), stated once.
- **Errors are data**: an `ErrorCode` union holding every code in the blueprint, and a
  result or error type that carries it.
- No `any`, no untyped maps where the shape is known.

End the section with an **error catalog**: a table with one row per code, giving its
meaning, whose fault it is, its HTTP status (only when the system has an HTTP boundary;
drop the column otherwise), and whether a retry can help. Design by
contract settles fault: a broken precondition is the caller's fault (a 4xx), a broken
postcondition or invariant is the supplier's (a 5xx). At an HTTP boundary, errors travel
as RFC 9457 problem details, with the code in a `code` member.

## Phase 4 — State machines

Draw every lifecycle: every `...Status` or `...State` type in section 3 gets one. Use a
Mermaid `stateDiagram-v2` (or ASCII when Mermaid won't render), with:

- `[*]` for the start, and terminal states marked, if there are any.
- Only legal transitions are drawn; anything not drawn is refused.
- Each transition labeled `event [guard]`.
- Held, waiting, and rollback branches shown, not implied.
- One line under the diagram: where the state is stored, which method performs each
  transition atomically, and the error code for an illegal transition.

## Phase 5 — Module boundaries and signatures

1. **Module map**: a directory tree an agent can create as is, one folder per component,
   with contracts and tests placed.
   Then the **C4 component diagram**: the design's diagram, redrawn inside its container,
   with each box's technology added. Required when there are more than three parts.
2. **Groups**, named for what they do, with the method's term in brackets:
   Entry points (Clients), Orchestration (Managers), Business rules (Engines),
   Resource access (ResourceAccess), Shared infrastructure (Utilities: a subsection only
   when the system builds one, such as a security policy; off-the-shelf logging just gets a
   folder in the module map). Stable business
   rules (the design's domain module) get a folder in the module map and no subsection:
   they are not a component. Resources (the
   databases and vendors themselves) appear in the target mode, not as components. In
   subsystem mode, the translation at the seam goes where the design put it: an
   anti-corruption layer is a ResourceAccess component; an open-host service is the
   subsystem's own API, with the host-side translator named in the flow.
3. **Per component**, as a `#### ComponentName` subsection:
   - **Purpose**: one line.
   - **Encapsulates**: the likely change it contains, in plain words.
   - **Constraints**: Engines are pure and in-memory, with no network, storage, clock, or
     randomness; the Manager passes in what they need (the same default `/decompose` uses).
     If the design records an Engine calling ResourceAccess, keep that call and inject the
     ResourceAccess as a read-only interface. ResourceAccess is the only code that touches
     a vendor or storage. Managers orchestrate and hold no business rules.
   - **May call**: from the design's call rules.
   - **Signatures**: a typed interface: business verbs, parameter and return types, and the
     error codes each method can return.
   - **Flows** (Managers): each public method's call sequence, one call per line: calls to
     other components, and to the domain module for stable rules. Managers apply rules by
     calling the domain module; they never contain them.
   - **Failure and retry**: which errors are retryable and which are final, timeouts,
     backoff, idempotency on retry, and how races resolve. For in-process, synchronous code
     one line is enough ("in-process; errors returned as values; nothing to retry").
   - **Internals**: the component's bricks from the design, as private modules. Required
     when the design lists bricks for the component; `--design` checks it.
   - A component's methods are the design's API verbs, no more and no fewer. A blueprint
     may add parameters the design left implicit (an idempotency key); a new verb is a
     design change, so add it to the design first.

## Phase 6 — Verification suite

Write 3–5 Gherkin scenarios that a test harness can run.

- **Cover**: idempotency and duplicate execution; the hard rejections and guardrails; state
  transitions, including an illegal one and an immutability check.
- **Every invariant's error code appears in at least one scenario.** Use a
  `Scenario Outline` with an `Examples` table to cover a family of rejections in one
  scenario.
- **Declarative steps**: state *what* happens in domain terms, not clicks, URLs, or SQL.
- **Concrete values**: real IDs, amounts, and times in the steps, so each scenario is a key
  example (Adzic), with boundary values where a rule has a threshold.
- **One behavior per scenario**, in 3–5 steps. `Given` puts the system in a known state,
  `When` is one event or action, and `Then` asserts an observable outcome (a response, a
  message sent, a status a caller can read), not a row in a database.
- A `Background` holds shared context only, in four lines or fewer.
- **End with the definition of done**: the command that runs the suite, and one line saying
  that done means these scenarios pass and the existing tests still pass (SWE-bench's
  FAIL_TO_PASS and PASS_TO_PASS).

## Phase 7 — Check and deliver

1. Run the checker, against the design, and fix until it passes:

   ```
   python <skill-dir>/scripts/check_blueprint.py name.blueprint.md --design name.design.md --compile --render
   ```

   It checks structure, invariant enforcement points and codes, that every code is in the
   error catalog, that every state type has a state machine, that every component has
   signatures and failure semantics, that every invariant's code is exercised by a
   scenario, that no scenario uses an undefined code, that section 6 ends with a verify
   command, that no design IDs such as `V1` or `F2` remain, and that no
   `[NEEDS CLARIFICATION]` is left open (use `--draft` while questions are still out).
   Its C4 checks confirm that the component diagram names exactly section 5's components,
   that every arrow obeys the call rules, that every component sits in a container, and
   that each diagram has a typed title and a key. With `--render` it renders every Mermaid
   diagram (needs `mmdc`). It also runs the plain-English check.
   With `--design` it checks congruence: every component in the design has a section 5
   subsection, no Manager, Engine, or ResourceAccess appears that the design lacks, and each
   design verb has a matching method. With `--compile` it type-checks TypeScript blocks
   when `tsc` is installed.
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
   MODULES      <n> components: <n> Clients · <n> Managers · <n> Engines · <n> ResourceAccess
   SCENARIOS    <n> · every invariant exercised
   DECISIONS    <n> added for review + <n> carried from the design · <n> open questions
   CHECK        PASS | DRAFT (open questions) | FAIL
   ```

4. Offer next steps: review the *Decisions added* list; `/quiz-plan` to turn the blueprint
   into steps; `/quiz-plan-execute` to build it, with the scenarios as its failing tests.

## Style

- **Plain English.** Write every sentence for a bright 10-year-old: one idea per sentence,
  common words, and each technical word explained once in section 1's "Words used here"
  list. Names, types, error codes, and numbers stay exact. Plain is not vague: "send each
  message at most once" is as exact as "idempotent delivery". See
  `references/plain-language.md`; the checker measures it.
- **Size it to the system.** A small system gets a short blueprint: fewer invariants, no
  HTTP column without HTTP, one line where a paragraph isn't needed.
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
- `references/c4.md`: the C4 diagrams: which level each skill draws, the notation rules,
  and Mermaid examples that render. Shared with `/decompose`.
- `references/plain-language.md`: how to write it in plain English; shared with
  `/decompose`.
- `scripts/check_blueprint.py`: the checker. Standard library only. It also runs
  `scripts/readability.py`, which ships alongside it (and with `/decompose`).

## Example

```
/blueprint notifications.design.md
```

The skill reads the design from `/decompose`'s worked example, chooses TypeScript and a
modular monolith, and writes `notifications.blueprint.md`:

- Six invariants: at-most-once delivery, quiet hours, no silent drops, forward-only
  delivery history, bounded retries, no message without content.
- Nineteen types, including the design's `Envelope`, plus an error catalog of nine codes.
- Two state machines, with transitions named after `OutboxAccess`'s lifecycle verbs.
- The design's nine components with typed interfaces, flows, and failure and retry rules.
- Five Gherkin scenarios that exercise every invariant, and the command that runs them.
- Nine decisions the design left open, listed for review.

It passes `check_blueprint.py --design notifications.design.md --compile`. The full result
is `references/notifications.blueprint.md`.
