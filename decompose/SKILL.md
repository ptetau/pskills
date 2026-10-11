---
name: decompose
description: >
  Software design for a new system, or a new subsystem in an established codebase. Sets
  the walls with volatility-based decomposition: components go around what is likely to
  change, so each change lands in one place. Managers hold changing workflows, Engines
  changing rules, and ResourceAccess changing storage and vendors. Then designs each
  wall's inside as a few orthogonal, composable primitives (inputs, transforms,
  transports, stores, state machines). Features become assemblies, not hand-built code.
  In an existing codebase, it measures volatility from git history, not guesses.
  Validates the design by walking the core use cases, simulating each likely change, and
  assembling future features, then writes a design doc. Use when the user says
  "/decompose" or asks to design, architect, or break down a system or subsystem. Use it
  when the user asks where service or module boundaries should go. Use it to turn a
  feature list into an architecture. Also use it to add a subsystem without the change
  rippling everywhere.
---

# Decompose: walls from volatility, bricks from primitives

## Purpose

Most designs split the system along features ("an invoicing service, a reporting service")
or along the nouns of the business ("customers, orders, products"). Both put the same
changeable thing in many places, so one change ripples through many components.

`/decompose` designs in two passes and then proves the result:

1. **Walls — volatility-based decomposition.** Find what is likely to change. Put each of
   those things behind its own component, so that when it changes, nothing outside that
   component notices. This sets the architecture: components, boundaries, who calls whom.
2. **Bricks — orthogonal primitives.** Inside each wall, don't build features. Build a
   small set of independent parts (inputs, transforms, transports, stores, state machines)
   that share one contract. Then assemble each feature as a composition of these parts.
3. **Proof.** Walk the core use cases through the walls. Simulate each likely change.
   Count the components it touches (the target is one existing component). Assemble
   current and plausible future features from existing bricks (the target is zero or one
   new brick).

Short version: **volatility decides where the walls go; primitives decide how the parts
inside connect.**

`/decompose` works at two scales:

- At **inception**, the input is a brainstormed feature list. The skill judges volatility
  from the business.
- For a **subsystem of an established system**, the host's structure is a constraint. The
  skill measures volatility from git history. The output includes the seam where the
  subsystem attaches and a step-by-step migration.

## When to use this skill

Use `/decompose` when:
- The user says `/decompose`, or asks to design, architect, or break down a system,
  service, or subsystem.
- There is a feature list or a set of requirements and the question is "what are the
  components?"
- The question is where boundaries should go: services, modules, packages, layers.
- The user must add a subsystem to an existing codebase and wants the subsystem not to
  leak.
- An area of an existing codebase keeps changing in many places at once and needs
  re-cutting.

Do **not** use it when:
- The change is small and local (one function, one bug). Just make the change.
- The components are already decided and the user needs a step-by-step change plan. Use
  [[quiz-plan]].
- The user wants a visual or UI design. This skill is about software structure.

## The ideas, distilled

The full rules, sources, and smells are in `references/walls.md` and
`references/bricks.md`. The essentials:

### Walls (volatility-based decomposition)

- **Decompose by what changes, not by what the system does** (Parnas 1972; Löwy,
  *Righting Software*, 2019). Put each likely change behind one component.
- **Volatile is not variable.** A value that changes (a rate, a limit) is data or a
  parameter. A thing is volatile when its change would ripple across the system if left
  unwrapped.
- **Two axes:** what changes for one customer over time, and what differs between
  customers at the same moment.
- **Don't wall off the nature of the business.** Walls for changes nobody expects are
  speculative design.
- **Component types:**

  | Type | Encapsulates | Example |
  |------|--------------|---------|
  | Client | who calls, and how: UI, API, scheduler, other systems | `AdminPortal` |
  | Manager | the volatile *sequence* of a family of related use cases (a workflow) | `EnrollmentManager` |
  | Engine | a volatile *activity*: a business rule, calculation, or algorithm | `PricingEngine` |
  | ResourceAccess | volatile *access* to a resource, exposed as business verbs, not CRUD | `MembersAccess` |
  | Resource | the actual store or external system | database, vendor API |
  | Utility | infrastructure any component may use | logging, security, pub/sub |

- **Calls go down, never up or sideways.** Clients → one Manager per use case → Engines
  and ResourceAccess; Engines → ResourceAccess; anyone → Utilities. Managers reach other
  Managers only through a queue. Only Managers publish events; Clients and Managers may
  subscribe. Full matrix in `references/walls.md`.
- **Features are integration, not implementation** (Löwy). A new feature should mostly be
  a new interaction between existing components.

### Bricks (orthogonal primitives)

- **Orthogonal means independent**: if the requirement behind one brick changes a lot,
  nothing else changes (Hunt and Thomas).
- **Brick kinds:**

  | Kind | Does | Example |
  |------|------|---------|
  | Input | brings something into a flow: an event, a request, a timer tick, a pull from a feed | `OnEvent(type)`, `OnSchedule(cron)` |
  | Transform | turns data into data, or into a decision (a *policy*); pure where possible | `Render`, `Match`, `QuietHours` |
  | Transport | moves data out: a vendor, a queue, a file, another service | `Email.send`, `Publish` |
  | Store | keeps data and hands it back through business verbs | `Hold(key, window)`, `Release(due)` |
  | State machine | remembers where a long-running thing is and what may happen next | `Delivery`: pending → sending → failed → retrying |

- **A shared contract** lets any brick follow any other. The shared contract is the one
  data shape the bricks pass around inside a wall, as opposed to the wall's API.
- **Mechanism, not policy.** Bricks are mechanism; "which" and "when" are policy, supplied
  as data or as a policy brick.
- **Earn every brick** (the skill's rule):
  - A Transform, policy, or Store serves two or more current features. Failing that, it
    serves one current feature as a variant that a recorded volatility names (one
    channel, one kind of discount). Otherwise the logic stays inline.
  - Inputs and Transports at the edges are exempt: every feature needs a way in and out.
  - Never merge bricks to satisfy this rule. A merged brick with a mode flag is a smell.
  - Never build a brick only a future feature needs (Fowler's YAGNI covers abstractions
    too).
  - Prefer duplication over the wrong abstraction (Metz).

### The hybrid: how walls and bricks fit together

| Wall | Its bricks |
|------|------------|
| Client | Inputs from the outside world (endpoints, UI, timers, event subscriptions) plus presentation |
| Manager | the wiring: flows that call Engines and ResourceAccess, plus State machines. The Manager decides each transition; when the state must outlive one flow, a ResourceAccess stores it and its verbs guard each transition as it is written (compare-and-set). It may own Inputs that subscribe to events. Flows are code by default. Löwy stores them as data run by a workflow tool when they differ by kind of item, customer, or locale, or run long across sessions and devices; the skill adds flows that change faster than you can deploy. |
| Engine | Transforms and policies behind one stable API. New rules are new bricks or new data, not new call paths. Pure by default: the Manager passes in the data the Engine needs. If an Engine must read, it calls ResourceAccess (Löwy allows it) and the design says so. |
| ResourceAccess | Stores, Transports, and Inputs that pull from vendors, behind business verbs. Vendor and storage details never cross its API. |
| Utility | stable mechanisms shared by everyone |

Three rules connect the two ideas:

1. **Walls first, bricks second, then re-check the walls.** Bricks often hint that two
   walls hide the same volatility, or that one wall hides two. Take the hint back to the
   volatility register. Decide there. Walls move only for volatility reasons.
2. **Only stable bricks cross walls.** Volatile bricks stay inside their wall. A stable
   brick that several walls need goes where it fits:
   - Plumbing that passes the Utility test (usable in a completely different system) is a
     Utility.
   - Stable business rules (the rules of a game, a fixed calculation) go in a domain
     module. The domain module has no volatility of its own and depends on nothing. It is
     not a component. It is the nature of the business, written down once, and it keeps
     rules out of Managers.
3. **A wall's API never exposes its wiring.** Callers use business verbs. A single brick
   may back a verb (`RenderingEngine.Render`). But callers never see which bricks run or
   in what order, so the wiring stays free to change.

## Two modes

| | Inception | Subsystem of an established system |
|---|---|---|
| Input | brainstormed features, goals | a request, plus the host codebase |
| Volatility evidence | business reasoning, interviews, roadmap | git history (`scripts/volatility.py`), commit messages, tickets, plus reasoning |
| Walls | the whole system | the subsystem plus its seam to the host; the host's walls are given |
| Extra output | — | attach point, translation at the seam, migration steps |
| Extra risk | speculative walls | leaky seams; host code that depends on current behaviour |

The details of subsystem mode are in `references/brownfield.md`.

## Phase 0 — Frame

Goal: know the mode, the scope, and the inputs before designing anything.

1. **Pick the mode.** Inception if there is no host code for this area. Subsystem if the
   design must live inside an existing codebase.
2. **Collect the feature list.** Use what the user gave. If the user gave only a
   sentence:
   - Propose the smallest set of features that makes the thing work. List likely extras
     separately.
   - Design for the core set. Don't build the extras; they become future features that
     test the design in Phase 5 (Validate).
   - Mark every feature you proposed as an assumption. Treat volatilities that rest only
     on your own proposals as weak evidence.
3. **Ask only what changes the design.** Usually: who uses it, what is likely to change,
   what must not change. If you need more than one question, ask them one at a time as
   [[quiz]] cards. If the user wants speed, state assumptions. Then proceed.
4. **Subsystem mode: read the host.** Its structure, entry points, data stores, and
   conventions. Then measure volatility:

   ```
   python <skill-dir>/scripts/volatility.py --path <area> --depth <n> --since "12 months ago"
   ```

   Read the commit messages of the top hotspots (`git log --oneline -- <file>`) to learn
   *what kind* of change keeps happening. See `references/brownfield.md` for how to read
   the report.

5. **Draw the system context diagram** (C4 level 1): the system as one box, the people who
   use it, and the other systems it talks to. In subsystem mode, the host is the system.
   See `references/c4.md`.

Output: a short frame (problem, users, constraints, assumptions, host facts), a context
diagram, and a numbered feature list (F1, F2, …).

## Phase 1 — Core use cases

Goal: separate the essence from the variations.

1. Rewrite each feature as a use case: who does what, and what the system does in response.
2. Group variations. "Welcome email", "reset SMS", and "Slack alert" are one core use case
   ("notify someone about an event") with different parameters.
3. Mark the **core use cases**: the few that express what the system is for. Löwy:
   typically two or three, seldom more than six. Everything else should turn out to be a
   variation of these.
4. Write down the **nature of the business**: what will stay true for the life of the
   system. Don't wall these things off.

## Phase 2 — Volatility register

Goal: a list of what is likely to change, with evidence, and a list of what you rejected.

1. **Generate candidates** along both axes (one customer over time, many customers now).
   `references/walls.md` has good prompts:
   - named vendors;
   - "for now" and "initially";
   - numbers and thresholds;
   - regulation;
   - anything a competitor does differently;
   - everything that changed in the domain over a period as long as the system's
     expected life.
2. **Look for solutions disguised as requirements.** "Send a Twilio SMS" is a solution. The
   need is "reach the user fast"; the volatility is the channel and the vendor.
3. **Filter each candidate:**
   - *Variable, not volatile?* Handle it with data or a parameter inside one component.
   - *Nature of the business?* Don't wall it off.
   - *Speculative?* No evidence it will change. Record it and move on.
4. **Record the survivors** as V1, V2, … with the axis, the evidence, and a likelihood.
   In subsystem mode, cite the git evidence (hotspot, coupling, commit messages).

## Phase 3 — Walls

Goal: components, their types, their APIs, and the call graph.

1. **Assign each volatility to one component** of the right type (the table above). A
   component may hold several related volatilities. Name each component for the
   volatility it hides, not for a feature: `PricingEngine`, not
   `BlackFridayDiscountService`.

   Managers, Engines, and ResourceAccess get two-part PascalCase names with the type as
   suffix; gerund prefixes are for Engines only. Name Clients and Utilities for what they
   are (`AdminPortal`, `Scheduler`). If an Engine's name is also a feature name, ask what
   activity would survive a redesign of the feature. Name the Engine for that activity.
2. **Write each component's API as business verbs.** For a Client, list its entry points:
   routes, commands, screens, or the user actions a UI handles (`ClickCell`). ResourceAccess exposes verbs such
   as `Deliver`, `FindRecipients`, `ConfirmDelivery`, never `Insert`, `Update`, `Save`,
   a generic `Record`, or a vendor's API.
3. **Draw the call graph** by layer. Check the call rules. Fix violations by moving
   responsibility, not by adding exceptions. Draw the call graph as a C4 component
   diagram, one band per layer, inside the system's boundary (containers are
   `/blueprint`'s choice). If there are three parts or fewer, skip the diagram. See
   `references/c4.md`.
4. **Check the size and shape.** Löwy's heuristics: about ten components, in order of
   magnitude. Even a large system commonly has:
   - two to five Managers;
   - two to three Engines (fewer than the Managers);
   - three to eight ResourceAccess and Resources;
   - about six Utilities.

   Eight Managers means feature-based decomposition. Volatility should decrease going
   down the layers. Apply the expendability test to each Manager (see
   `references/walls.md`). These are smell checks, not targets. If the design falls
   outside them, write down why.
5. **Place the cross-cutting concerns** (audit, authorisation, tenancy) and any writes
   that must be atomic across resources. `references/walls.md` says how.
6. **Subsystem mode:** fit the new walls to the host. Pick the attach point (the seam).
   Keep host types out of the subsystem:
   - Where the subsystem calls the host, use an anti-corruption layer.
   - Where the host calls the subsystem, use an open-host service.

## Phase 4 — Bricks

Goal: for each component, a small catalogue of orthogonal bricks and a shared contract.
Start with the most volatile component. See `references/bricks.md` for tests and smells.

1. **List what the component must support**: its share of the features, plus the
   volatilities it contains.
2. **Write each feature as a short sentence.** Pull out the verbs. Verbs that recur
   across features are brick candidates. Classify each: Input, Transform, Transport,
   Store, or State machine.
3. **Define the shared contract**: the data shape the wall's bricks exchange, with its
   fields and invariants. Each wall has one; walls that pass data along the same flow may
   share it. Most bricks are `contract → contract` (a policy may return zero or many).
   The edges differ:
   - An Input produces the contract.
   - A Transport consumes the contract and returns a receipt.
   - A State machine takes events and returns the next state plus commands.

   If the register says the data's shape itself will change, keep that change additive
   (see `references/bricks.md`).
4. **Split any brick that does two independent things.** A flag that switches between
   different behaviours means two or more bricks. A parameter the same behaviour uses (a
   predicate, a threshold) is fine. Don't over-split. Keep pieces together when they
   share information, or when splitting would complicate their interfaces (Ousterhout's
   *classitis*).
5. **Separate mechanism from policy.** Hard-coded "which" and "when" become policy bricks
   or data.
6. **Choose the composition medium**: plain code by default. Use a pipeline definition,
   rule table, or stored workflow only when both of these are true:
   - The composition itself is a recorded volatility.
   - One of these holds. Löwy stores workflows for the first two reasons; the skill adds
     the third.
     - It differs by kind of item, customer, or locale.
     - It runs long across sessions and devices.
     - It changes faster than you can deploy.

   Rules that end users write are different (an accountant's categorisation rules, a
   marketer's promotions). They are customer data, and their small rule language belongs
   to an Engine.
7. **Re-check the walls** (rule 1 of the hybrid: walls first, bricks second). If the
   bricks hint that two components hide the same volatility, or one hides two, go back to
   Phase 2 (Volatility register). Decide from the register. Merge or split only if the
   register agrees.

## Phase 5 — Validate

Goal: prove the design, don't assert it. Run every check. Fix and re-run until the checks
pass, or record why you accept a failure. Record the results in the design doc as they are
now, not the drafts before them. Under "Choices the checks depend on", list each design
choice that a check needs, with that check.

1. **Use-case walkthrough.** Write each core use case as a call chain through the walls,
   one `Caller → Callee.Verb` per line. This makes the direction of every call visible.
   The chain must need no new component and break no call rule.

   Start each chain with the caller and how the system knows who the caller is. For
   example: a sign-in, an API key, a card and PIN. If no part or verb answers that, the
   design is missing one.
2. **Change simulation** (Parnas's 1972 test). For each volatility in the register,
   imagine it happening at least once. If it covers distinct kinds of change, imagine it
   more than once. List the components that must change. Target: one existing component.

   These exceptions don't count as leaks:
   - a new verb on a ResourceAccess, because the change records a new kind of business
     fact (see `references/walls.md`);
   - a new Client for a new kind of caller;
   - a new Engine, when the change brings in a new volatile activity;
   - one new ResourceAccess, when the change brings in a genuinely new resource (a new
     vendor or store);
   - a Client change, when the change adds something a person does or must see.

   Record each exception that applies. If two or more existing components change for any
   other reason, that means a leaky wall.
3. **Feature assembly.** Write every current feature as wiring over the brick catalogue.
   The wiring holds no logic beyond selecting bricks and passing parameters. This checks
   that the catalogue is complete. Then the real test: two or three plausible future
   features drawn from the register. Include extras you proposed in Phase 0 (Frame).

   Each future feature should need at most one new brick, inside one component. A new
   two-way resource, which needs an Input and a Transport, counts as one. Describe each
   future feature in one line: what it would add, and where. Don't design it. You may also
   try a rejected candidate to see what it would cost. Don't expect a rejected candidate
   to pass.
4. **Independence (orthogonality) check.** For each brick, ask: if its requirement changed a lot, what
   else would change? Anything other than "nothing" is a hidden dependency.
5. **Rule and smell audit.** Call rules, names, sizes, and the smell list in
   `references/walls.md` and `references/bricks.md`.
6. **Trace audit.** Every component traces to a volatility. (Every Client hides who
   calls and how; every ResourceAccess over your own storage hides the storage
   technology. Both count.) Every brick traces to a feature or a volatility. Anything that
   traces to neither goes on the cut list.
7. **Subsystem mode: measured coupling.** The volatility report lists component pairs
   above the coupling threshold. For each such pair, say whether the design puts a wall
   between them, and why the coupling will fall. Name the metric to re-check after the
   change ships.

## Phase 6 — Write it up

1. Write `<name>.design.md` at the project root (or where the user asks), from
   `references/design-template.md`. **Size the document to the problem.** The design of a
   small system should be shorter than its code. A **small system** (one Manager, and no
   more than one Engine or ResourceAccess) gets a short form:
   - Phase 5 (Validate) is one table, with one row per check. Where a check has nothing
     to test, write "n/a". Examples: orthogonality with two bricks, expendability for a
     Manager with nothing below it.
   - No layer diagram, and no justifying being below Löwy's sizes: those are warnings for
     large systems.
   - Empty sections keep their number in one line ("Not applicable: inception").
2. Check that the document reads plainly:
   `python <skill-dir>/scripts/readability.py <name>.design.md`. Rewrite the flagged
   sentences. Add any unexplained word to "Words used here". Check that every diagram
   renders: use `mmdc` if it is installed, or paste the diagram into
   <https://mermaid.live>. Give each diagram a title naming its type, and a `Key:` line
   under it.
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
   - `/argue` the design doc, to check it for contradictions;
   - [[blueprint]], to turn it into an agent-ready spec (typed contracts, state machines,
     signatures, and Gherkin scenarios);
   - `/quiz-plan`, to turn the walls (and, in subsystem mode, the migration steps) into
     an executable change plan.

## Rules

- **Plain English.** Write the design for a bright 10-year-old: short sentences and
  common words. Explain every technical word once, in a "Words used here" list in §1
  (Frame). Names, code, and numbers stay exact. See `references/plain-language.md`. Run
  `scripts/readability.py` on the finished document.
- **Evidence over taste.** Every volatility cites evidence: the user's words, the roadmap,
  or git history. Every component traces to a volatility; every brick to a feature or a
  volatility.
- **Never name a component after a feature.** Names come from the volatility hidden inside.
- **APIs speak business verbs.** No CRUD, no vendor types, no storage details across
  a wall.
- **Walls before bricks; bricks never decide where walls go.** They can only prompt a
  re-check.
- **Don't build for imagined futures.** Use a future feature as a test of the design, not
  as a reason to build it now.
- **Subsystem mode: respect the host.** Follow its conventions. Change it only at the
  seam. Keep existing behaviour until callers have moved (people depend on it, documented
  or not).
- **Run the validation.** A design that has not been through Phase 5 (Validate) is a
  sketch. If the user asks to stop early, say so.

## References

- `references/walls.md` — volatility-based decomposition in full: finding volatilities,
  component types, call rules, naming, sizing, smells.
- `references/bricks.md` — orthogonal primitives in full: brick kinds, the shared
  contract, composition, orthogonality tests, guardrails, smells.
- `references/brownfield.md` — subsystem mode: measuring volatility, reading the report,
  mapping the host, seams, anti-corruption layers, migration.
- `references/design-template.md` — the shape of `<name>.design.md`.
- `references/examples.md` — a worked inception example (notifications) and a worked
  subsystem example (promotions in an existing shop).
- `references/sources.md` — where each idea comes from, with links.
- `references/c4.md` — the C4 diagrams: which level each skill draws, the notation rules,
  and Mermaid examples that render. Shared with `/blueprint`.
- `references/plain-language.md` — how to write the design in plain English; shared with
  `/blueprint`.
- `scripts/readability.py` — checks the finished design reads plainly: sentence length,
  reading grade, unexplained technical words. Shared with `/blueprint`.
- `scripts/volatility.py` — measures component volatility, change coupling, and hotspots
  from git history. Standard library only.

## Example

```
/decompose a notifications service: welcome emails, password-reset SMS, daily digests,
Slack alerts for ops, user channel preferences, quiet hours, retries, localization
```

The skill finds five volatilities (channels and vendors, routing rules, content,
delivery flows, recipient data) and rejects three candidates. It sets one Manager, two
Engines, and three ResourceAccess components. Inside them it defines one `Envelope`
contract and about a dozen bricks. It assembles all eight features with no new bricks,
shows that WhatsApp, escalation, and a regional rule each touch one component, and
writes `notifications.design.md`. See `references/examples.md` for the full run.
