---
name: decompose
description: >
  Software design for a new system, or for a new subsystem in an established codebase.
  Sets the walls with volatility-based decomposition: components go around what is
  likely to change (Managers for changing workflows, Engines for changing rules,
  ResourceAccess for changing storage and vendors). Thus, each change lands in one
  place. Then designs the inside of each wall as a few orthogonal, composable primitives
  (inputs, transforms, transports, stores, state machines). Thus, you assemble features,
  and you do not build each feature by hand. In an existing codebase, measures
  volatility from git history and does not guess. Validates the design in three ways:
  walks the core use cases, simulates each likely change, and assembles future features.
  Then writes a design document. Use when the user says "/decompose", or asks to
  "design", "architect", or "break down" a system or subsystem. Also use when the user
  asks where service or module boundaries go. Also use when the user wants to turn a
  feature list into an architecture. Also use when the user wants to add a subsystem
  without a change that ripples everywhere.
---

# Decompose: walls from volatility, bricks from primitives

## Purpose

Most designers cut a design along features ("an invoicing service, a reporting service")
or along the nouns of the business ("customers, orders, products"). Both cuts put the
same changeable thing in many places. Thus, one change ripples through many components.

`/decompose` designs in two passes, and then proves the result:

1. **Walls — volatility-based decomposition.** Find what is likely to change. Put each of
   those things behind its own component. Then a change to one of those things has no
   effect outside its component. The walls set the architecture: the components, the
   boundaries, and who calls whom.
2. **Bricks — orthogonal primitives.** Inside each wall, do not build features. Build a
   small set of independent parts (inputs, transforms, transports, stores, state
   machines) that share one contract. Then assemble each feature as a composition of
   these parts.
3. **Proof.** Walk the core use cases through the walls. Simulate each likely change, and
   count the components that the change touches. The target is one existing component.
   Assemble the current features and plausible future features from the existing
   bricks. The target is zero or one new brick.

Short version: **volatility decides where the walls go. Primitives decide how the parts
inside a wall connect.**

`/decompose` works at two scales:

- At **inception**, the input is a brainstormed feature list. You judge volatility from
  the business.
- For a **subsystem of an established system**, the structure of the host is a
  constraint. You measure volatility from git history. The output includes the seam
  where the subsystem attaches, and a step-by-step migration.

## When to use this skill

Use `/decompose` in these conditions:

- The user says `/decompose`, or asks to "design", "architect", or "break down" a system,
  a service, or a subsystem.
- There is a feature list or a set of requirements, and the question is "what are the
  components?"
- The question is where the boundaries go: services, modules, packages, or layers.
- The user wants to add a subsystem to an existing codebase, and the subsystem must not
  leak.
- An area of an existing codebase changes in many places at the same time, again and
  again, and the area needs a new cut.

Do **not** use `/decompose` in these conditions:

- The change is small and local (one function, one bug). Make the change.
- The components are already decided, and the user needs a step-by-step change plan. Use
  [[quiz-plan]].
- The user wants a visual design or a UI design. This skill is about the structure of
  software.

## The ideas, distilled

`references/walls.md` and `references/bricks.md` give the full rules, the sources, and
the smells. This section gives the primary ideas.

### Walls (volatility-based decomposition)

- **Decompose by what changes, not by what the system does** (Parnas 1972; Löwy,
  *Righting Software*, 2019). Put each likely change behind one component.
- **Volatile is not variable.** A value that changes (a rate, a limit) is data or a
  parameter. A thing is volatile when a change to it would ripple across the system
  without a wall around it.
- **Two axes:** what changes for one customer over time, and what is different between
  customers at the same moment.
- **Do not put a wall around the nature of the business.** A wall for a change that
  nobody expects is speculative design.
- **Component types:**

  | Type | Encapsulates | Example |
  |------|--------------|---------|
  | Client | who calls, and how: UI, API, scheduler, other systems | `AdminPortal` |
  | Manager | the volatile *sequence* of a family of related use cases (a workflow) | `EnrollmentManager` |
  | Engine | a volatile *activity*: a business rule, a calculation, or an algorithm | `PricingEngine` |
  | ResourceAccess | volatile *access* to a resource, shown as business verbs, not CRUD | `MembersAccess` |
  | Resource | the actual store or external system | database, vendor API |
  | Utility | infrastructure that any component can use | logging, security, pub/sub |

- **Calls go down. Calls do not go up or sideways.** The call rules are these:
  - Clients → one Manager for each use case → Engines and ResourceAccess.
  - Engines → ResourceAccess.
  - Any component → Utilities.
  - A Manager calls a different Manager only through a queue.
  - Only Managers publish events. Clients and Managers can subscribe.

  The full matrix is in `references/walls.md`.
- **Features are integration, not implementation** (Löwy). In a good design, a new
  feature is mostly a new interaction between existing components.

### Bricks (orthogonal primitives)

- **Orthogonal means independent.** If the requirement behind one brick changes a lot,
  nothing else changes (Hunt and Thomas).
- **Brick kinds:**

  | Kind | Does | Example |
  |------|------|---------|
  | Input | brings something into a flow: an event, a request, a timer tick, a pull from a feed | `OnEvent(type)`, `OnSchedule(cron)` |
  | Transform | turns data into data, or into a decision (a *policy*). Pure where possible | `Render`, `Match`, `QuietHours` |
  | Transport | moves data out: to a vendor, a queue, a file, or a different service | `Email.send`, `Publish` |
  | Store | keeps data, and gives the data back through business verbs | `Hold(key, window)`, `Release(due)` |
  | State machine | remembers where a long-running thing is, and what can happen next | `Delivery`: pending → sending → failed → retrying |

- **A shared contract** lets any brick follow any other brick. The shared contract is the
  one data shape that the bricks pass around inside a wall. The shared contract is not
  the API of the wall.
- **Mechanism, not policy.** Bricks are mechanism. "Which" and "when" are policy. Supply
  policy as data or as a policy brick.
- **Earn every brick** (the skill's rule). Each Transform, policy, or Store must meet one
  of these conditions:
  - The brick serves two or more current features.
  - The brick serves one current feature as a variant that a recorded volatility names
    (one channel, one kind of discount).

  If a brick meets neither condition, the logic stays inline. Inputs and Transports at
  the edges are exempt, because each feature needs a way in and a way out. Do not merge
  bricks to satisfy this rule. A merged brick with a mode flag is a smell. Do not build a
  brick that only a future feature needs (Fowler's YAGNI covers abstractions too).
  Prefer duplication over the wrong abstraction (Metz).

### The hybrid: how walls and bricks fit together

| Wall | Its bricks |
|------|------------|
| Client | Inputs from the outside world (endpoints, UI, timers, event subscriptions), plus presentation. |
| Manager | The wiring: flows that call Engines and ResourceAccess, plus State machines. The Manager decides each transition. When the state must outlive one flow, a ResourceAccess stores the state. The verbs of that ResourceAccess guard each transition when they write it (compare-and-set). A Manager can own Inputs that subscribe to events. Flows are code by default. Löwy stores flows as data, and a workflow tool runs them, in two cases: the flows differ by kind of item, customer, or locale, or the flows run long across sessions and devices. The skill adds a third case: flows that change faster than you can deploy. |
| Engine | Transforms and policies behind one stable API. A new rule is a new brick or new data, not a new call path. An Engine is pure by default: the Manager passes in the data that the Engine needs. If an Engine must read, the Engine calls ResourceAccess (Löwy allows this), and the design says so. |
| ResourceAccess | Stores, Transports, and Inputs that pull from vendors, behind business verbs. Vendor details and storage details never cross the API of the ResourceAccess. |
| Utility | Stable mechanisms that all components share. |

Three rules connect the two ideas:

1. **Walls first, bricks second, then re-check the walls.** Bricks often hint that two
   walls hide the same volatility, or that one wall hides two. Take the hint back to the
   volatility register, and decide there. Walls move only for volatility reasons.
2. **Only stable bricks cross walls.** Volatile bricks stay inside their wall. A stable
   brick that several walls need goes where it fits:
   - Plumbing that passes the Utility test (usable in a completely different system) is
     a Utility.
   - Stable business rules (the rules of a game, a fixed calculation) go in a domain
     module. The domain module has no volatility of its own, and it depends on nothing.
     The domain module is not a component. The domain module is the nature of the
     business, written one time, and it keeps rules out of Managers.
3. **The API of a wall does not show its wiring.** Callers use business verbs. A verb can
   have only one brick behind it (`RenderingEngine.Render`). But callers do not see which
   bricks run, or in what order. Thus, the wiring stays free to change.

## Two modes

| | Inception | Subsystem of an established system |
|---|---|---|
| Input | brainstormed features, goals | a request, plus the host codebase |
| Volatility evidence | business reasoning, interviews, roadmap | git history (`scripts/volatility.py`), commit messages, tickets, plus reasoning |
| Walls | the whole system | the subsystem, plus its seam to the host. The walls of the host are fixed |
| Extra output | — | attach point, translation at the seam, migration steps |
| Extra risk | speculative walls | leaky seams, and host code that depends on the current behaviour |

`references/brownfield.md` gives the details of subsystem mode.

## Phase 0 — Frame

Goal: know the mode, the scope, and the inputs before you design anything.

1. **Pick the mode.** If there is no host code for this area, use inception mode. If the
   design must live inside an existing codebase, use subsystem mode.
2. **Collect the feature list.** Use the features that the user gave. If the user gave
   only a sentence, propose the smallest set of features that makes the thing work. List
   the likely extras separately. Design for the core set.

   The design does not build the extras. The extras become future features that test the
   design in Phase 5. Mark each feature that you proposed as an assumption. If a
   volatility rests only on your own proposals, treat it as weak evidence.
3. **Ask only what changes the design.** Usually, ask who uses the system, what is likely
   to change, and what must not change. If you need more than one question, ask the
   questions one at a time as [[quiz]] cards. If the user wants speed, state your
   assumptions and continue.
4. **Subsystem mode: read the host.** Read its structure, entry points, data stores, and
   conventions. Then measure volatility:

   ```
   python <skill-dir>/scripts/volatility.py --path <area> --depth <n> --since "12 months ago"
   ```

   Read the commit messages of the top hotspots (`git log --oneline -- <file>`). The
   messages show *what kind* of change occurs again and again. `references/brownfield.md`
   tells you how to read the report.

5. **Draw the system context diagram** (C4 level 1). Show the system as one box, the
   people who use it, and the other systems that it talks to. In subsystem mode, the host
   is the system. See `references/c4.md`.

Output: a short frame (problem, users, constraints, assumptions, host facts), a context
diagram, and a numbered feature list (F1, F2, …).

## Phase 1 — Core use cases

Goal: separate the essence from the variations.

1. Write each feature again as a use case: who does what, and what the system does in
   response.
2. Group the variations. "Welcome email", "reset SMS", and "Slack alert" are one core use
   case ("notify someone about an event") with different parameters.
3. Mark the **core use cases**: the few use cases that express what the system is for.
   Löwy says that there are typically two or three, and seldom more than six. Each other
   use case must be a variation of the core use cases.
4. Write the **nature of the business**: what stays true for the life of the system. Do
   not put a wall around these things.

## Phase 2 — Volatility register

Goal: a list of what is likely to change, with evidence, and a list of the rejected
candidates.

1. **Generate candidates** along the two axes (one customer over time, many customers
   now). `references/walls.md` gives good prompts:
   - Named vendors.
   - "For now" and "initially".
   - Numbers and thresholds.
   - Regulation.
   - Anything that a competitor does differently.
   - Each thing that changed in the domain over a period as long as the expected life of
     the system.
2. **Look for solutions disguised as requirements.** "Send a Twilio SMS" is a solution.
   The need is "reach the user fast". The volatility is the channel and the vendor.
3. **Filter each candidate:**
   - *Variable, not volatile?* Handle the candidate with data or a parameter inside one
     component.
   - *Nature of the business?* Do not put a wall around the candidate.
   - *Speculative?* There is no evidence that the candidate will change. Record the
     candidate and continue.
4. **Record the survivors** as V1, V2, … with the axis, the evidence, and a likelihood.
   In subsystem mode, cite the git evidence (hotspot, coupling, commit messages).

## Phase 3 — Walls

Goal: the components, their types, their APIs, and the call graph.

1. **Assign each volatility to one component** of the correct type (see the table above).
   One component can hold several related volatilities.
   - Name each component for the volatility that it hides, not for a feature:
     `PricingEngine`, not `BlackFridayDiscountService`.
   - Give Managers, Engines, and ResourceAccess two-part PascalCase names, with the type
     as the suffix. Use gerund prefixes only for Engines.
   - Name Clients and Utilities for what they are (`AdminPortal`, `Scheduler`).
   - If an Engine's name is also a feature name, ask what activity would survive a
     redesign of the feature. Name the Engine for that activity.
2. **Write the API of each component as business verbs.** For a Client, list its entry
   points: routes, commands, screens, or the user actions that a UI handles
   (`ClickCell`). A ResourceAccess exposes verbs such as `Deliver`, `FindRecipients`, and
   `ConfirmDelivery`. A ResourceAccess does not expose `Insert`, `Update`, `Save`, a
   generic `Record`, or the API of a vendor.
3. **Draw the call graph** by layer, and make sure that each call obeys the call rules. If
   a call breaks a rule, move the responsibility. Do not add an exception. Draw the call
   graph as a C4 component diagram, with one band for each layer. Put the diagram inside
   the boundary of the system. (The choice of containers belongs to `/blueprint`.) If there are three
   parts or fewer, do not draw the diagram. See `references/c4.md`.
4. **Examine the size and the shape.** Löwy gives these heuristics. A system has about
   ten components, as an order of magnitude. Even a large system commonly has these
   numbers:
   - Two to five Managers.
   - Two to three Engines, fewer than the Managers.
   - Three to eight ResourceAccess and Resources.
   - About six Utilities.

   Eight Managers means a feature-based decomposition. Volatility must decrease from the
   top layer to the bottom layer. Apply the expendability test to each Manager (see
   `references/walls.md`). These heuristics are smell checks, not targets. When the
   design is outside them, write the reason.
5. **Place the cross-cutting concerns** (audit, authorisation, tenancy). Also place each
   write that must be atomic across resources. `references/walls.md` tells you how.
6. **Subsystem mode: fit the new walls to the host.** Pick the attach point (the seam).
   Keep the types of the host out of the subsystem:
   - Where the subsystem calls the host, use an anti-corruption layer.
   - Where the host calls the subsystem, use an open-host service.

## Phase 4 — Bricks

Goal: for each component, a small catalogue of orthogonal bricks and a shared contract.
Start with the most volatile component. `references/bricks.md` gives the tests and the
smells.

1. **List what the component must support**: its share of the features, plus the
   volatilities that it contains.
2. **Write each feature as a short sentence, and find its verbs.** Verbs that recur across
   features are brick candidates. Classify each candidate as an Input, a Transform, a
   Transport, a Store, or a State machine.
3. **Define the shared contract**: the data shape that the bricks of the wall exchange,
   with its fields and invariants. Each wall has one shared contract. Walls that pass
   data along the same flow can share one. Most bricks are `contract → contract` (a
   policy can return zero or many). The edges are different:
   - An Input produces the contract.
   - A Transport consumes the contract and returns a receipt.
   - A State machine takes events, and returns the next state plus commands.

   If the register says that the shape of the data will change, keep that change
   additive (see `references/bricks.md`).
4. **Split each brick that does two independent things.** A flag that switches between
   different behaviours means two or more bricks. A parameter that the same behaviour
   uses (a predicate, a threshold) is fine. Do not over-split. Keep pieces together when
   they share information, or when a split would complicate their interfaces
   (Ousterhout's *classitis*).
5. **Separate mechanism from policy.** Hard-coded "which" and "when" become policy bricks
   or data.
6. **Choose the composition medium.** Use plain code by default. Use a pipeline
   definition, a rule table, or a stored workflow only when the two conditions that follow
   are true:
   - The composition itself is a recorded volatility.
   - One of these reasons applies. The composition differs by kind of item, customer, or
     locale, or runs long across sessions and devices (Löwy's reasons to store
     workflows). Or the composition changes faster than you can deploy (the skill's
     addition).

   Rules that end users write are different (an accountant's categorisation rules, a
   marketer's promotions). These rules are customer data, and their small rule language
   belongs to an Engine.
7. **Re-check the walls** (rule 1 of the hybrid). The bricks can hint that two components
   hide the same volatility, or that one component hides two. If so, go back to Phase 2,
   and decide from the volatility register. Merge or split only if the register agrees.

## Phase 5 — Validate

Goal: prove the design. Do not only assert the design. Run each check, and record the
results in the design document. Fix the design and run the checks again until they
pass. As an alternative, record why you accept a failure.

1. **Use-case walkthrough.** Write each core use case as a call chain through the walls.
   Write one `Caller → Callee.Verb` on each line, so that the direction of each call is
   visible. The chain must need no new component, and must break no call rule. Start
   each chain with who calls, and how the system knows who they are (a sign-in, an API
   key, a card and PIN). If no part or verb answers that question, a part or a verb is
   missing from the design.
2. **Change simulation** (Parnas's 1972 test). For each volatility in the register,
   imagine that the change happens at least one time. If the volatility covers distinct
   kinds of change, imagine more than one change. List the components that must change.
   The target is one existing component. These exceptions are not leaks:
   - A new verb on a ResourceAccess, because the change records a new kind of business
     fact (see `references/walls.md`).
   - A new Client for a new kind of caller.
   - A new Engine, when the change brings in a new volatile activity.
   - One new ResourceAccess, when the change brings in a genuinely new resource (a new
     vendor or store).
   - A Client change, when the change adds something that a person does or must see.

   Record either. If two or more existing components change for any other reason, the
   wall leaks.
3. **Feature assembly.** Write each current feature as wiring over the brick catalogue.
   The wiring has no logic, other than to select bricks and pass parameters. This step
   makes sure that the catalogue is complete. Then do the real test:
   - Take two or three plausible future features from the register. Include the extras
     that you proposed in Phase 0.
   - Each future feature must need at most one new brick, inside one component. (A new
     two-way resource that needs an Input and a Transport counts as one brick.)
   - Give each future feature in one line: what the feature would add, and where. Do not
     design the feature.

   You can also try a rejected candidate to see its cost. You do not expect a rejected
   candidate to pass.
4. **Independence (orthogonality) check.** For each brick, ask: if the requirement of the
   brick changed a lot, what else would change? Any answer other than "nothing" is a
   hidden dependency.
5. **Rule and smell audit.** Examine the call rules, the names, the sizes, and the smell
   lists in `references/walls.md` and `references/bricks.md`.
6. **Trace audit.** Each component traces to a volatility. (Each Client hides who calls
   and how. Each ResourceAccess over your own storage hides the storage technology. Both
   count.) Each brick traces to a feature or a volatility. Put each item that traces to
   neither on the cut list.
7. **Subsystem mode: measured coupling.** Find each component pair above the coupling
   threshold in the volatility report. For each pair, say whether the design puts a wall
   between the two components, and why the coupling will fall. Name the metric to check
   again after the change ships.

## Phase 6 — Write the design document

1. Write `<name>.design.md` at the project root (or where the user asks), from
   `references/design-template.md`. **Size the document to the problem.** The design of a
   small system must be shorter than its code. A **small system** (one Manager, and no
   more than one Engine or ResourceAccess) gets a short form:
   - Phase 5 is one table, with one row for each check. Write "n/a" where a check has
     nothing to test (orthogonality with two bricks, expendability for a Manager with
     nothing below it).
   - Do not draw a layer diagram. Do not give a reason for sizes below Löwy's sizes,
     because those sizes are warnings for large systems.
   - Each empty section keeps its number, in one line ("Not applicable: inception").
2. Examine the writing: `python <skill-dir>/scripts/check_writing.py <name>.design.md --max-grade 7`.
   Write the flagged sentences again. Add each word that the linter shows as not explained
   to "Words used here".
   Make sure that each diagram renders. Use `mmdc` if it is installed, or paste the
   diagram into <https://mermaid.live>. Give each diagram a title that names its type, and
   a `Key:` line under it.
3. Show a compact summary in chat, in a code block:

   ```
   DECOMPOSE: <name> · <inception | subsystem of X>
   ══════════════════════════════════════════════════
   VOLATILITIES  <n> contained · <n> rejected
   WALLS         <n> components: <n> Clients · <n> Managers · <n> Engines · <n> ResourceAccess · plus <n> Utilities
   BRICKS        <n> across <n> components · contracts: <names>
   ──────────────────────────────────────────────────
   USE CASES     <passed>/<total> walk through cleanly
   CHANGE SIM    <passed>/<total> simulations across <n> volatilities touch one component
   FEATURES      <n> current assembled · <n> future with ≤1 new brick
   ASSUMPTIONS   <n> (carried into /blueprint's decisions)
   VERDICT       ready | ready, <n> accepted leaks: <list> | <n> leaks to resolve: <list>
   ```

4. Offer these next steps:
   - `/argue` the design document, to find contradictions.
   - [[blueprint]], to turn the design into an agent-ready spec (typed contracts, state
     machines, signatures, and Gherkin scenarios).
   - `/quiz-plan`, to turn the walls (and, in subsystem mode, the migration steps) into
     an executable change plan.

## Rules

- **Writing.** Write all text to `references/writing-guidelines.md`: the replies to the
  user and the design document. Write the design for a bright 10-year-old, at a reading
  grade of 7 or lower. Give each technical word one time in a "Words used here" list in §1.
  Names, code, and numbers stay the same. Run `scripts/check_writing.py` on the finished
  document.
- **Evidence over taste.** Each volatility cites evidence: the words of the user, the
  roadmap, or git history. Each component traces to a volatility. Each brick traces to a
  feature or a volatility.
- **Do not name a component after a feature.** The name comes from the volatility that
  the component hides.
- **APIs use business verbs.** Do not send CRUD, vendor types, or storage details across a
  wall.
- **Walls before bricks.** Bricks do not decide where walls go. Bricks can only prompt a
  re-check.
- **Do not build for imagined futures.** Use a future feature as a test of the design,
  not as a reason to build the feature now.
- **Subsystem mode: respect the host.** Follow the conventions of the host. Change the
  host only at the seam. Keep the existing behaviour until the callers move, because
  people depend on that behaviour, documented or not.
- **Run the validation.** A design without the checks of Phase 5 is a sketch. If the
  user asks to stop early, tell the user that the design is a sketch.

## References

- `references/walls.md`: volatility-based decomposition in full. It gives how to find
  volatilities, the component types, the call rules, naming, sizing, and smells.
- `references/bricks.md`: orthogonal primitives in full. It gives the brick kinds, the
  shared contract, composition, the orthogonality tests, guardrails, and smells.
- `references/brownfield.md`: subsystem mode. It gives how to measure volatility, how to
  read the report, how to map the host, seams, anti-corruption layers, and migration.
- `references/design-template.md`: the shape of `<name>.design.md`.
- `references/examples.md`: a worked inception example (notifications), and a worked
  subsystem example (promotions in an existing shop).
- `references/sources.md`: where each idea comes from, with links.
- `references/c4.md`: the C4 diagrams. It gives the level that each skill draws, the
  notation rules, and Mermaid examples that render. Shared with `/blueprint`.
- `references/writing-guidelines.md`: the writing guidelines for all text. They are
  ASD-STE100 Simplified Technical English, and two more rules. Shared with each skill.
- `scripts/check_writing.py`: the linter for the writing guidelines. It examines sentence
  length, verb forms, pronouns that refer back, IDs with no description, and the reading
  grade. Shared with `/blueprint` and `/improve-writing`.
- `scripts/volatility.py`: measures component volatility, change coupling, and hotspots
  from git history. It uses only the standard library.

## Example

```
/decompose a notifications service: welcome emails, password-reset SMS, daily digests,
Slack alerts for ops, user channel preferences, quiet hours, retries, localization
```

The skill finds five volatilities: channels and vendors, routing rules, content, delivery
flows, and recipient data. The skill rejects three candidates. The skill sets one
Manager, two Engines, and three ResourceAccess components. Inside these components, the
skill defines one `Envelope` contract and about a dozen bricks.

The skill assembles all eight features with no new bricks. The skill shows that WhatsApp,
escalation, and a regional rule each touch one component. Then the skill writes
`notifications.design.md`. See `references/examples.md` for the full run.
