---
name: blueprint
description: >
  Turns a system design (a /decompose design document, or any architecture doc) into
  an Agent System Design Document. This document is a spec that a person can skim, and
  that a coding agent can implement with no guesses. Its six sections are scope boundaries, enforceable
  invariants with error codes, strongly typed data contracts, explicit state machines,
  module boundaries, and a Gherkin verification suite. Each module boundary gives typed
  method signatures and failure and retry semantics. Decides each detail that the design
  leaves open one time, marks it as assumed, and lists it for review. Removes methodology
  jargon and IDs. Then checks the result with a bundled checker, and writes a blueprint
  document. Use when the user says "/blueprint", or asks to turn a design into a spec.
  Also use when the user asks to make a design agent-ready or implementable. Also use
  when the user asks to write the types, interfaces, contracts, or acceptance tests for a
  design, or wants the next step after /decompose.
---

# Blueprint: from design to buildable spec

## Purpose

A design document tells *why* the system has its shape. A coding agent must know *exactly
what* to build. The agent needs the types, error codes, state transitions, method
signatures, and the tests that show when the work is done. If an agent gets only the design, the agent invents
those details, and the details are different each time.

`/blueprint` writes an **Agent System Design Document** (a blueprint) from a design. The
blueprint has six sections:

1. **Header and boundary box**: what the system is, how the system is deployed, what is in
   scope and out of scope, and each decision that the blueprint adds.
2. **System invariants**: 4–7 enforceable rules. Each rule has its enforcement point and
   the error code that it raises.
3. **Core data contracts**: exact types, not prose.
4. **State machines**: each lifecycle, with its guards, terminal states, and illegal
   moves.
5. **Module boundaries and interface signatures**: the purpose, constraints, typed
   methods, and failure and retry behaviour of each component.
6. **Verification suite**: 3–5 Gherkin scenarios that exercise each invariant.

A person can read the blueprint from top to bottom in minutes. A coding agent can scaffold
the directories, the types, and the test harness directly from the blueprint.

`/blueprint` is the companion to [[decompose]]. `/decompose` decides the walls and the
bricks, and proves them. `/blueprint` makes the walls and the bricks buildable. After
`/blueprint`, [[quiz-plan]] turns the blueprint into steps. Then [[quiz-plan-execute]]
implements the steps, and uses the Gherkin scenarios as its failing tests.

## When to use this skill

Use `/blueprint` in these conditions:

- The user says `/blueprint`, or asks to turn a design into a spec. Or the user asks to
  make a design agent-ready or implementable.
- There is a design document (ideally a `name.design.md` from `/decompose`), and the next
  step is to build the design.
- The user asks for the types, interfaces, contracts, or acceptance tests of a design.

Do **not** use `/blueprint` in these conditions:

- There is no design yet. Run [[decompose]] first. If the user insists, work from the text
  that the user gave, and expect many more assumed decisions.
- The user wants a step-by-step change plan. A change plan is the job of [[quiz-plan]],
  which can take the blueprint as input.

## The core rule: never guess silently

The design leaves some details open. Examples are a retry count, the format of an
idempotency key, a storage engine, the name of an error code, and a time zone. The
blueprint must decide these details. An agent that meets an open question guesses, and
each agent guesses differently.

Thus, each detail that the source does not state is a **decision added by this spec**. For
each such detail, do these steps:

1. Decide the detail one time. Use the conventional default
   (`references/conventions.md`).
2. Mark the detail *(assumed)* one time, at the place where a reader first meets it. The
   checker compares the number of marks with the number of listed decisions.
3. List the detail in section 1, under **Decisions added by this spec**. Add one line that
   tells what changes if the decision is wrong.

A person reviews that list one time. After the review, nothing in the blueprint is a
guess.

A few questions cannot get a default, because a wrong guess is expensive. Mark each such
question inline as `[NEEDS CLARIFICATION: the specific question]`. Mark a maximum of three
questions. Select them by impact, in this order (the rule of GitHub spec-kit):

1. Scope.
2. Security, privacy, and legal compliance.
3. User experience.
4. Technical detail.

Ask the user to answer these questions. A blueprint with open questions is a draft. The
checker reports the draft as not agent-ready until the questions are resolved.

If a decision changes the design itself (a new component, or a different call path), do
not make the decision. Stop and ask the user, or send the user back to `/decompose`.

## Inputs and how a design maps

Read the full design. In subsystem mode, also read the host codebase: its language,
framework, directory conventions, error handling, and existing types. If the conventions
of the host are different from the defaults of this skill, the blueprint uses the
conventions of the host.

This table maps a `/decompose` design document to the blueprint. The design sections have
the numbers of `decompose/references/design-template.md`.

| Design section | Goes to | How |
|----------------|---------|-----|
| §1 Frame: problem, users, constraints | 1. Header | System, target mode, and scope. Carry the design's assumptions into *Decisions added* |
| §1 Nature of the business | 2. Invariants | Each fact that must always be true becomes an enforceable rule |
| §2 Features and core use cases | 1. In scope, and 5. Flows | Features become scope bullets. Each core use case becomes a flow across the methods of its Manager |
| §3 Volatility register | 5. "Encapsulates" line | Each component gives, in plain words, the change that it encapsulates ("Contained by" in the register) |
| §3 Rejected candidates, and §7 Cut list | 1. Out of scope | As non-goals |
| §4 Walls: components, APIs, call rules | 5. Modules | The same components in the same groups. Each API verb becomes a method. The call rules become the "May call" line of each component |
| §5 Shared contracts | 3. Contracts | Each contract becomes exact types, and keeps its name |
| §5 Bricks | 5. Internals | Each brick becomes a private module inside its component |
| §5 State machines | 4. State machines | Drawn again, with guards, terminal states, and illegal transitions. Each transition has the name of the API verb that does it |
| §6 Feature assembly, and §7 Walkthroughs | 5. Flows, and 6. Scenarios | Each walkthrough becomes the flow under its Manager method. Key features become scenarios |
| §7 Validation results | — | Stays in the design. Link to the results |
| §7 Accepted leaks | 1. Decisions added | Each leak as a known limitation: the future change that will touch two components |
| §6 Future features that failed assembly | 1. Out of scope | As a non-goal, with the cost of the feature |
| §8 Seams and migration | 1. Scope, and 5. Translation at the seam | Migration steps belong to the change plan, not to the blueprint |
| §1 Assumptions | 1. Decisions carried from the design | Carried without changes |
| §4 Cross-cutting concerns, atomic writes | 2. Invariants, and 5. Constraints and Failure & retry | Each enforcement point becomes an invariant or a constraint. Each atomic write names its transaction |
| §5 How the pieces are joined (composition medium), rule tables | 5. Internals, and 3. Contracts | Say if the flows are code or data. A rule table becomes typed data |
| §9 Risks and open questions | 1. Decisions added, or `[NEEDS CLARIFICATION]` | Resolve each item, or ask the user |

**Names stay the same.** Components keep their names (`RoutingEngine`). API verbs become
methods in the style of the language: `Route` becomes `route` in TypeScript, and stays
`Route` in Go. Contracts keep their names (`Envelope`) and their variants. A narrower or
wider contract is a design change. A blueprint does not add, remove, or rename a component
or a verb, and the `--design` option checks this rule.

**Lifecycles** follow the design. The Manager decides each transition. If the state lives
longer than one flow, a ResourceAccess stores the state. The verbs of that ResourceAccess
do each transition atomically. The "Stored by" line in section 4 names that
ResourceAccess.

**Business thresholds** that the design gives to a named owner ("Legal decides the
expiry"): select a conservative placeholder. Mark the placeholder *(assumed; owner:
Legal)*, and list it. Use a `[NEEDS CLARIFICATION]` only when no placeholder is safe to
build against.

Use the same method for a design in a different format. Find the scope, rules, data,
lifecycles, components, and behaviours, and translate each one.

## Phase 0 — Choose the target

1. **Language.** Use the language of the host codebase. If there is no host, use the
   language that the user names. If the user names no language, ask one time, and offer
   TypeScript as the default. All code blocks in the blueprint use that one language.
2. **Target mode.** Write in one line what gets built and how it runs. The choices are a
   browser app, a CLI, a library, a single service or modular monolith, or separately
   deployed services (only if the design calls for them). Then draw the **C4 container
   diagram** (see `references/c4.md`). The diagram shows each container (an app, a
   database, a queue) and the components that the container holds. Do not split a
   component across containers, because in C4 "it's the container that's the deployable
   unit". If there is one container, one line that says so is sufficient.
3. **Name.** Name the file `name.blueprint.md`, and put it next to the design document.

## Phase 1 — Header and boundary box

- **System** and **target mode**, each on one line.
- **In scope**: what gets built, as features in the words of the user.
- **Out of scope (non-goals)**: rejected candidates, future changes that are only tests of
  the design, and any other work that a reasonable agent can wander into.
- **Decisions carried from the design**: the assumptions of the design, without changes.
- **Decisions added by this spec**: each *(assumed)* detail, on one line each. Keep the
  two lists separate. Then the new list is short enough to review.
- **Words used here**: each technical word that the blueprint uses, with a plain
  explanation in one line.
- A link to the source design.

## Phase 2 — Invariants

Write the rules that must be true in all conditions. These rules are the invariants of
design by contract, made concrete. The format asks for 4–7 invariants, and this number
suits most systems. A small domain can have fewer invariants.

Do not pad the list with a rule that the types already guarantee. Also do not pad the list with a rule that only a
caller with a bug can break. Find the invariants in these places:

- The nature of the business.
- The rules of the Engines.
- The state machines.
- The atomicity notes.
- Each thing that a duplicate or a retry can break.

Each invariant gives these items:

- **The rule**, in one sentence that a tester can check.
- **The enforcement point**: `Component.method`. If the check must be atomic with a write,
  also give the transaction boundary.
- **The error code** that the system raises when something tries to break the rule, in
  `UPPER_SNAKE_CASE`.

Give each invariant a name. Do not give the invariants ID numbers. The style rule of the
format does not permit cryptic IDs. A name such as **Each message is delivered at most
once** is its own reference.

Cover these topics, where they apply:

- Idempotency: what makes two requests "the same", and what occurs on a replay.
- Immutability: what cannot change after the system writes it.
- The hard rejections: what the system refuses, and with which code.

If no repeated action can cause harm, say so in one line. Do not invent an idempotency
rule.

## Phase 3 — Data contracts

Translate each shared contract, record, and API payload into exact types. Use one code
block for each module, or one code block for the full domain. Obey these rules (the
details are in `references/conventions.md`):

- **Make illegal states unrepresentable.** Use unions for enums and states, not strings.
  If two states have different fields, give each state a separate type.
- **Name each lifecycle type `...Status` or `...State`** (`DeliveryStatus`, `MatchState`).
  Then readers and the checker can find its state machine.
- **On each field, show if the field is required or optional.**
- **Give each identifier a distinct type** (branded types in TypeScript, newtypes in Go
  and Rust). Then code cannot pass an `OrderId` as a `CustomerId`.
- **Money is an integer in minor units, plus an ISO 4217 currency code.** Do not use a
  float.
- **Use one explicit convention for time** (for example, ISO 8601 UTC strings). State the
  convention one time.
- **Errors are data**: an `ErrorCode` union that holds each code in the blueprint, and a
  result or error type that carries the code.
- Do not use `any`. Do not use an untyped map when you know the shape of the data.

End the section with an **error catalogue**. The error catalogue is a table with one row
for each code. Each row gives these items:

- The meaning of the code.
- Whose fault the error is.
- The HTTP status. Give this column only when the system has an HTTP boundary. If there is
  no HTTP boundary, remove the column.
- Whether a retry can help.

Design by contract decides the fault. A broken precondition is the fault of the caller (a
4xx). A broken postcondition or invariant is the fault of the supplier (a 5xx). At an HTTP
boundary, errors travel as RFC 9457 problem details, with the code in a `code` member.

## Phase 4 — State machines

Draw each lifecycle. Each `...Status` or `...State` type in section 3 gets a state machine.
Each state machine brick in the design also gets a state machine, with all of its states.
Give the state machine the heading `### {Machine}Status`. Or, under a different heading,
write "the design's `{Machine}` machine". The `--design` option checks the two forms. Use
a Mermaid `stateDiagram-v2` (or ASCII when Mermaid does not render), and obey these rules:

- Use `[*]` for the start. Mark the terminal states, if there are any.
- Draw only the legal transitions. The system refuses each transition that is not drawn.
- Label each transition `event [guard]`.
- Show the held, waiting, and rollback branches. Do not only imply them.
- Write one line under the diagram. The line gives where the state is stored, the method
  that does each transition atomically, and the error code for an illegal transition.

## Phase 5 — Module boundaries and signatures

1. **Module map**: a directory tree that an agent can create without changes. Give one
   folder for each component, and show the place of the contracts and the tests.
   Then draw the **C4 component diagram**: the diagram of the design, drawn again inside
   its container, with the technology of each box added. The component diagram is
   necessary when there are more than three parts.
2. **Groups.** Name each group for what it does, with the methodology term in brackets:
   - Entry points (Clients).
   - Orchestration (Managers).
   - Business rules (Engines).
   - Resource access (ResourceAccess).
   - Shared infrastructure (Utilities). Give this subsection only when the system builds a
     Utility, for example a security policy. Also, the design must name the Utility,
     ideally as a `Utility` row in its walls table. Off-the-shelf logging gets only a
     folder in the module map.

   Stable business rules (the domain module of the design) get a folder in the module map,
   and no subsection. Stable business rules are not a component. Resources (the databases
   and the vendors) appear in the target mode, not as components. In subsystem mode, put
   the translation at the seam where the design put it:
   - An anti-corruption layer is a ResourceAccess component.
   - An open-host service is the API of the subsystem. Name the translator on the host
     side in the flow.
3. **Per component**: write a `#### ComponentName` subsection with these items:
   - **Purpose**: one line.
   - **Encapsulates**: the likely change that the component contains, in plain words.
   - **Constraints**:
     - Engines are pure and in-memory, with no network, storage, clock, or randomness.
       The Manager passes in the data that the Engines need. `/decompose` uses the same
       default.
     - If the design records an Engine that calls a ResourceAccess, keep that call.
       Inject the ResourceAccess as a read-only interface.
     - ResourceAccess is the only code that touches a vendor or storage.
     - Managers run the steps in order, and hold no business rules.
     - A Client says how its callers prove who they are (a sign-in, an API key, a card and
       PIN). If the design does not say, decide how, and mark the decision *(assumed)*.
   - **May call**: take this item from the call rules of the design. Write it as a
     separate `- **May call:**` line. The checker reads only that line. Thus, "only
     librarians may call it" in other text is not a problem.
   - **Signatures**: a typed interface with the business verbs, the parameter and return
     types, and the error codes that each method can return.
   - **Flows** (Managers): the call sequence of each public method, with one call on each
     line. Give the calls to other components, and the calls to the domain module for
     stable rules. Managers apply rules through calls to the domain module. Managers do
     not contain the rules. A call to another Manager goes through a queue. Say so on the
     line of the call: "4. Queue `NoticeManager.tellHoldReady(hold)`."
   - **Failure and retry**: which errors are retryable and which are final, the timeouts,
     the backoff, idempotency on retry, and how races resolve. For in-process,
     synchronous code, one line is sufficient ("In-process. Errors are returned as
     values. There is nothing to retry.").
   - **Internals**: the bricks of the component from the design, as private modules. Name
     each brick in backticks, with the spelling of the design (`mayBorrow` for
     `MayBorrow` is correct). This item is necessary when the design lists bricks for the
     component. The `--design` option checks this item.
   - The methods of a component are the API verbs of the design, no more and no fewer. A
     blueprint can add parameters that the design left implicit (an idempotency key). A
     new verb is a design change. Thus, add a new verb to the design first.

## Phase 6 — Verification suite

Write 3–5 Gherkin scenarios that a test harness can run.

- **Cover** these behaviours:
  - Idempotency and duplicate execution.
  - The hard rejections and guardrails.
  - State transitions, including an illegal transition and an immutability check.
- **The error code of each invariant appears in at least one scenario.** To cover a family
  of rejections in one scenario, use a `Scenario Outline` with an `Examples` table.
- **Declarative steps**: state *what* happens, in domain terms. Do not give clicks, URLs,
  or SQL.
- **Concrete values**: put real IDs, amounts, and times in the steps. Then each scenario
  is a key example (Adzic). Where a rule has a threshold, use boundary values.
- **One behaviour in each scenario**, in 3–5 steps:
  - `Given` puts the system in a known state.
  - `When` is one event or action.
  - `Then` asserts an observable outcome (a response, a message sent, a status a caller
    can read), not a row in a database.
- A `Background` holds only shared context, in four lines or fewer.
- **End with the definition of done**: the command that runs the suite, and one line. The
  line says that done means these scenarios pass, and the existing tests still pass
  (FAIL_TO_PASS and PASS_TO_PASS in SWE-bench).

## Phase 7 — Check and deliver

1. Run the checker against the design. Fix the blueprint until the checker passes it:

   ```
   python <skill-dir>/scripts/check_blueprint.py name.blueprint.md --design name.design.md --compile --render
   ```

   The checker examines these items:
   - The structure.
   - The enforcement points and the codes of the invariants.
   - Each code is in the error catalogue.
   - Each state type has a state machine.
   - Each component has signatures and failure semantics.
   - A scenario exercises the code of each invariant.
   - No scenario uses an undefined code.
   - Section 6 ends with a "Verify" line that gives a command.
   - No design IDs remain (for example, `V1` or `F2`).
   - No `[NEEDS CLARIFICATION]` stays open. Use `--draft` while questions are still open.

   The C4 checks make sure of these items:
   - The component diagram names exactly the components of section 5.
   - Each arrow obeys the call rules.
   - Each component is in a container.
   - Each diagram has a typed title and a key.

   With `--render`, the checker renders each Mermaid diagram (this needs `mmdc`). The
   checker also runs the writing check. With `--design`, the checker examines the
   congruence with the design:
   - Each component in the design has a section 5 subsection.
   - No Manager, Engine, or ResourceAccess appears that the design does not have.
   - Each verb of the design has a matching method.
   - Each brick and each shared contract keeps its name.
   - Each state machine of the design appears in section 4, with all its states.

   A render proves the syntax of a diagram, not its layout. Open each diagram. Fix the
   labels that overlap or that are cut off (`references/c4.md`). With `--compile`, the
   checker type-checks the TypeScript blocks when `tsc` is installed.
2. Read the blueprint again as the coding agent. For each section, ask: can you write the
   code or the test with no questions? Each question that you would ask is a missing
   decision. Add the decision to *Decisions added*, or ask the user.
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

4. Offer these next steps:
   - Review the *Decisions added* list.
   - Run `/quiz-plan` to turn the blueprint into steps.
   - Run `/quiz-plan-execute` to build the blueprint, with the scenarios as its failing
     tests.

## Style

- **Writing.** Write all text to `references/writing-guidelines.md`: the replies to the
  user and the blueprint. Write each sentence for a bright 10-year-old, at a reading grade
  of 7 or lower. Give each technical word one time in the "Words used here" list in
  section 1. Names, types, error codes, and numbers stay the same. Plain text is not
  vague: "send each message at most one time" is as accurate as "idempotent delivery".
  The checker examines the writing.
- **Size it to the system.** A small system gets a short blueprint: fewer invariants, no
  HTTP column without HTTP, and one line where a paragraph is not necessary. Say each
  thing one time. The signature block gives the types, so the prose adds only what the
  types cannot give (order, failure, why). Point to an invariant in section 2. Do not
  write the invariant again in section 5.
- **Zero fluff.** Start each section with its substance. Do not write introductions. Do
  not write summaries of the text that comes next.
- **Plain domain terms.** Do not use design IDs (`V1`, `F2`, `UC3`). Use the methodology
  terms (Client, Manager, Engine, ResourceAccess, Utility) only where the template puts
  them. These places are the group headings of section 5, the component type in diagram
  boxes, and the "Words used here" list. In all other places, say what the part does.
- **Scannable.** Use tables and short bullets. Use code where precision is important. Make
  each section readable alone.
- **Agent-ready.** An agent with no other context can create the directory tree, the type
  definitions, and the test harness from this document alone.
- **Faithful.** Do not change the components or the call rules of the design. If the
  design is wrong, say so and stop. Do not quietly design the system again in the
  blueprint.

## References

- `references/blueprint-template.md`: the exact shape of the document, which the checker
  expects.
- `references/conventions.md`: the default decisions (money, time, IDs, idempotency,
  errors, retries, Gherkin style), and the source of each decision.
- `references/notifications.blueprint.md`: a worked blueprint of the notifications example
  of `/decompose`. This blueprint passes the checker.
- `references/sources.md`: the sources of the conventions.
- `references/c4.md`: the C4 diagrams: the level that each skill draws, the notation
  rules, and Mermaid examples that render. Shared with `/decompose`.
- `references/writing-guidelines.md`: the writing guidelines for all text: ASD-STE100
  Simplified Technical English and two more rules. Shared with each skill.
- `scripts/check_blueprint.py`: the checker. Standard library only. The checker also runs
  `scripts/check_writing.py`, the linter for the writing guidelines. The linter is shared
  with `/decompose` and `/improve-writing`.

## Example

```
/blueprint notifications.design.md
```

The skill reads the design from the worked example of `/decompose`. The skill selects
TypeScript and a modular monolith, and writes `notifications.blueprint.md`:

- Six invariants: at-most-once delivery, quiet hours, no silent drops, forward-only
  delivery history, bounded retries, no message without content.
- Nineteen types, including the `Envelope` of the design, and an error catalogue of nine
  codes.
- Two state machines, with transitions that have the names of the lifecycle verbs of
  `OutboxAccess`.
- The nine components of the design, with typed interfaces, flows, and failure and retry
  rules.
- Five Gherkin scenarios that exercise each invariant, and the command that runs the
  scenarios.
- Eleven decisions that the design left open, including how callers prove who they are.
  The blueprint marks each decision where it applies, and lists it for review.

The blueprint passes `check_blueprint.py --design notifications.design.md --compile
--render`. The full result is `references/notifications.blueprint.md`.
