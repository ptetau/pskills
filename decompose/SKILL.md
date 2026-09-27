---
name: decompose
description: >
  Software design for a new system or for a new subsystem inside an established
  codebase. Sets the walls with volatility-based decomposition: components go around
  what is likely to change (Managers for changing workflows, Engines for changing
  rules, ResourceAccess for changing storage and vendors), so each change lands in one
  place. Then designs the inside of each wall as a few orthogonal, composable
  primitives (inputs, transforms, transports, stores, state machines), so features are
  assembled rather than hand-built. In an existing codebase it measures volatility from
  git history instead of guessing. Validates the design by walking the core use cases,
  simulating each likely change, and assembling future features, then writes a design
  document. Use when the user says "/decompose", asks to design, architect, or break
  down a system or subsystem, asks where service or module boundaries should go, wants
  to turn a feature list into an architecture, or wants to add a subsystem without the
  change rippling everywhere.
---

# Decompose: walls from volatility, bricks from primitives

## Purpose

Most designs are cut along features ("an invoicing service, a reporting service") or along
the nouns of the business ("customers, orders, products"). Both put the same changeable
thing in many places, so one change ripples through many components.

`/decompose` designs in two passes and then proves the result:

1. **Walls — volatility-based decomposition.** Find what is likely to change. Put each of
   those things behind its own component, so that when it changes, nothing outside that
   component notices. This sets the architecture: components, boundaries, who calls whom.
2. **Bricks — orthogonal primitives.** Inside each wall, don't build features. Build a
   small set of independent parts (inputs, transforms, transports, stores, state machines)
   that share one contract, then assemble each feature as a composition of them.
3. **Proof.** Walk the core use cases through the walls. Simulate each likely change and
   count the components it touches (the target is one existing component). Assemble current and plausible
   future features from existing bricks (the target is zero or one new brick).

Short version: **volatility decides where the walls go; primitives decide how the parts
inside connect.**

It works at two scales. At **inception** the input is a brainstormed feature list and
volatility is judged from the business. For a **subsystem of an established system** the
host's structure is a constraint, volatility is measured from git history, and the output
includes the seam where the subsystem attaches and a step-by-step migration.

## When to use this skill

Use `/decompose` when:
- The user says `/decompose`, or asks to design, architect, or break down a system,
  service, or subsystem.
- There is a feature list or a set of requirements and the question is "what are the
  components?"
- The question is where boundaries should go: services, modules, packages, layers.
- A subsystem must be added to an existing codebase and the user wants it not to leak.
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

- **A shared contract** (the one data shape the bricks pass around inside a wall, as
  opposed to the wall's API) lets any brick follow any other.
- **Mechanism, not policy.** Bricks are mechanism; "which" and "when" are policy, supplied
  as data or as a policy brick.
- **Earn every brick** (the skill's rule). A brick serves two or more current features,
  or it serves one current feature as a variant a recorded volatility names (one channel,
  one kind of discount). Otherwise the logic stays inline. Never build a brick only a
  future feature needs (Fowler's YAGNI covers abstractions too). Prefer duplication over
  the wrong abstraction (Metz).

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
   volatility register and decide there. Walls move only for volatility reasons.
2. **Only stable bricks cross walls.** Volatile bricks stay inside their wall. A stable
   brick that several walls need goes where it fits: plumbing that passes the Utility test
   (usable in a completely different system) is a Utility; stable business rules that
   several components need (the rules of a game, a fixed calculation) go in a shared
   domain module with no volatility of its own, which depends on nothing. That module is
   not a component; it is the nature of the business, written down once.
3. **A wall's API never exposes its wiring.** Callers use business verbs. A verb may be
   backed by a single brick (`RenderingEngine.Render`), but callers never see which bricks
   run or in what order, so that stays free to change.

## Two modes

| | Inception | Subsystem of an established system |
|---|---|---|
| Input | brainstormed features, goals | a request, plus the host codebase |
| Volatility evidence | business reasoning, interviews, roadmap | git history (`scripts/volatility.py`), commit messages, tickets, plus reasoning |
| Walls | the whole system | the subsystem plus its seam to the host; the host's walls are given |
| Extra output | — | attach point, translation at the seam, migration steps |
| Extra risk | speculative walls | leaky seams; host code that depends on current behavior |

The details of subsystem mode are in `references/brownfield.md`.

## Phase 0 — Frame

Goal: know the mode, the scope, and the inputs before designing anything.

1. **Pick the mode.** Inception if there is no host code for this area. Subsystem if the
   design must live inside an existing codebase.
2. **Collect the feature list.** Use what the user gave. If they gave only a sentence,
   propose the smallest set of features that makes the thing work, and list likely extras
   separately. Design for the core set. The extras are not built; they become future
   features that test the design in Phase 5. Mark every feature you proposed as an
   assumption, and treat volatilities that rest only on your own proposals as weak
   evidence.
3. **Ask only what changes the design.** Usually: who uses it, what is likely to change,
   what must not change. If more than one question is needed, ask them one at a time as
   [[quiz]] cards. If the user wants speed, state assumptions and proceed.
4. **Subsystem mode: read the host.** Its structure, entry points, data stores, and
   conventions. Then measure volatility:

   ```
   python <skill-dir>/scripts/volatility.py --path <area> --depth <n> --since "12 months ago"
   ```

   Read the commit messages of the top hotspots (`git log --oneline -- <file>`) to learn
   *what kind* of change keeps happening. See `references/brownfield.md` for how to read
   the report.

Output: a short frame (problem, users, constraints, assumptions, host facts) and a numbered feature
list (F1, F2, …).

## Phase 1 — Core use cases

Goal: separate the essence from the variations.

1. Rewrite each feature as a use case: who does what, and what the system does in response.
2. Group variations. "Welcome email", "reset SMS", and "Slack alert" are one core use case
   ("notify someone about an event") with different parameters.
3. Mark the **core use cases**: the few that express what the system is for. Löwy:
   typically two or three, seldom more than six. Everything else should turn out to be a
   variation of these.
4. Write down the **nature of the business**: what will stay true for the life of the
   system. These things are not walled off.

## Phase 2 — Volatility register

Goal: a list of what is likely to change, with evidence, and a list of what was rejected.

1. **Generate candidates** along both axes (one customer over time, many customers now).
   Good prompts are in `references/walls.md`: named vendors, "for now" and "initially",
   numbers and thresholds, regulation, anything a competitor does differently, and
   everything that changed in the domain over a period as long as the system's expected
   life.
2. **Look for solutions disguised as requirements.** "Send a Twilio SMS" is a solution. The
   need is "reach the user fast"; the volatility is the channel and the vendor.
3. **Filter each candidate:**
   - *Variable, not volatile?* Handle it with data or a parameter inside one component.
   - *Nature of the business?* Don't wall it off.
   - *Speculative?* No evidence it will change. Record it and move on.
4. **Record the survivors** as V1, V2, … with the axis, the evidence, and a likelihood.
   Subsystem mode: cite the git evidence (hotspot, coupling, commit messages).

## Phase 3 — Walls

Goal: components, their types, their APIs, and the call graph.

1. **Assign each volatility to one component** of the right type (the table above). A
   component may hold several related volatilities. Name each component for the
   volatility it hides, not for a feature: `PricingEngine`, not
   `BlackFridayDiscountService`. Managers, Engines, and ResourceAccess get two-part
   PascalCase names with the type as suffix; gerund prefixes are for Engines only.
   Clients and Utilities are named for what they are (`AdminPortal`, `Scheduler`). If an Engine's name is also a feature name, ask
   what activity would survive a redesign of the feature, and name it that.
2. **Write each component's API as business verbs.** For a Client, list its entry points
   (routes, screens, commands). ResourceAccess exposes verbs such
   as `Deliver`, `FindRecipients`, `ConfirmDelivery`, never `Insert`, `Update`, `Save`,
   a generic `Record`, or a vendor's API.
3. **Draw the call graph** by layer and check the call rules. Fix violations by moving
   responsibility, not by adding exceptions.
4. **Check the size and shape.** Löwy's heuristics: about ten components in order of
   magnitude; even a large system commonly has two to five Managers, two to three Engines
   (fewer than the Managers), three to eight ResourceAccess and Resources, and about six
   Utilities. Eight Managers means feature-based decomposition. Volatility should decrease
   going down the layers. Apply the expendability test to each Manager (see
   `references/walls.md`). These are smell checks, not targets: when the design falls
   outside them, write down why.
5. **Place the cross-cutting concerns** (audit, authorization, tenancy) and any writes
   that must be atomic across resources. `references/walls.md` says how.
6. **Subsystem mode:** fit the new walls to the host. Pick the attach point (the seam) and
   keep host types out of the subsystem: an anti-corruption layer where the subsystem
   calls the host, an open-host service where the host calls the subsystem.

## Phase 4 — Bricks

Goal: for each component, a small catalog of orthogonal bricks and a shared contract.
Start with the most volatile component. See `references/bricks.md` for tests and smells.

1. **List what the component must support**: its share of the features, plus the
   volatilities it contains.
2. **Write each feature as a short sentence and pull out the verbs.** Verbs that recur
   across features are brick candidates. Classify each: Input, Transform, Transport,
   Store, or State machine.
3. **Define the shared contract**: the data shape the wall's bricks exchange, with its
   fields and invariants. Each wall has one; walls that pass data along the same flow may
   share it. Most bricks are `contract → contract` (a policy may return zero or many).
   The edges differ: an Input produces the contract, a Transport consumes it and returns
   a receipt, a State machine takes events and returns the next state plus commands. If
   the register says the data's shape itself will change, keep that change additive
   (see `references/bricks.md`).
4. **Split any brick that does two independent things.** A flag that switches between
   different behaviors means two or more bricks. A parameter the same behavior uses (a
   predicate, a threshold) is fine. Don't over-split: keep pieces together when they share
   information or when splitting would complicate their interfaces (Ousterhout's
   *classitis*).
5. **Separate mechanism from policy.** Hard-coded "which" and "when" become policy bricks
   or data.
6. **Choose the composition medium**: plain code by default. A pipeline definition, rule
   table, or stored workflow only when the composition itself is a recorded volatility
   *and* one of these holds: it differs by kind of item, customer, or locale, or runs long
   across sessions and devices (Löwy's reasons for storing workflows); or it changes faster
   than you can deploy (the skill's addition).
   Rules that end users write (an accountant's categorization rules, a marketer's
   promotions) are different: they are customer data, and their small rule language
   belongs to an Engine.
7. **Re-check the walls** (rule 1 of the hybrid). If the bricks hint that two components
   hide the same volatility, or one hides two, go back to Phase 2 and decide from the
   volatility register. Merge or split only if the register agrees.

## Phase 5 — Validate

Goal: prove the design, don't assert it. Run every check and record the results in the
design doc. Fix and re-run until they pass, or record why a failure is accepted.

1. **Use-case walkthrough.** Write each core use case as a call chain through the walls,
   one `Caller → Callee.Verb` per line so the direction of every call is visible. It must
   need no new component and break no call rule.
2. **Change simulation** (Parnas's 1972 test). For each volatility in the register,
   imagine it happening, at least once, and more than once if it covers distinct kinds of
   change. List the components that must change. Target: one existing component. These
   exceptions don't count as leaks: a new verb on a ResourceAccess because the change
   records a new kind of business fact (see `references/walls.md`); a new Client for a
   new kind of caller; adding one new ResourceAccess when the change brings
   in a genuinely new resource (a new vendor or store), and a Client change when the
   change adds something a person does or must see. Record either. Two or more existing
   components changing for any other reason means a leaky wall.
3. **Feature assembly.** Write every current feature as wiring over the brick catalog,
   with no logic in the wiring beyond selecting bricks and passing parameters. This
   checks that the catalog is complete. Then the real test: two or three plausible future
   features drawn from the register (including extras you proposed in Phase 0). Each
   should need at most one new brick, inside one component. You may also try a rejected
   candidate to see what it would cost, but it isn't expected to pass.
4. **Orthogonality check.** For each brick, ask: if its requirement changed a lot, what
   else would change? Anything other than "nothing" is a hidden dependency.
5. **Rule and smell audit.** Call rules, names, sizes, and the smell list in
   `references/walls.md` and `references/bricks.md`.
6. **Trace audit.** Every component traces to a volatility. (Every Client hides who
   calls and how; every ResourceAccess over your own storage hides the storage
   technology. Both count.) Every brick traces to a feature or a volatility. Anything that
   traces to neither goes on the cut list.
7. **Subsystem mode: measured coupling.** For every component pair above the coupling
   threshold in the volatility report, say whether the design puts a wall between them
   and why the coupling will fall. Name the metric to re-check after the change ships.

## Phase 6 — Write it up

1. Write `<name>.design.md` at the project root (or where the user asks), from
   `references/design-template.md`. **Size the document to the problem.** The design of a
   small system should be shorter than its code. With a handful of components, record
   each Phase 5 check as a table row or a line, skip the layer diagram, and don't justify
   being below Löwy's sizes: those are warnings for large systems. Keep the section
   numbers even when a section is empty ("Not applicable: inception").
2. Show a compact summary in chat, in a code block:

   ```
   DECOMPOSE: <name> · <inception | subsystem of X>
   ══════════════════════════════════════════════════
   VOLATILITIES  <n> contained · <n> rejected
   WALLS         <n> components: <n> Clients · <n> Managers · <n> Engines · <n> ResourceAccess · plus <n> Utilities
   BRICKS        <n> across <n> components · contracts: <names>
   ──────────────────────────────────────────────────
   USE CASES     <passed>/<total> walk through cleanly
   CHANGE SIM    <passed>/<total> volatilities touch one component
   FEATURES      <n> current assembled · <n> future with ≤1 new brick
   ASSUMPTIONS   <n> (carried into /blueprint's decisions)
   VERDICT       ready | ready, <n> accepted leaks: <list> | <n> leaks to resolve: <list>
   ```

3. Offer next steps: `/argue` the design doc to check it for contradictions;
   [[blueprint]] to turn it into an agent-ready spec (typed contracts, state machines,
   signatures, and Gherkin scenarios); and `/quiz-plan` to turn the walls (and, in
   subsystem mode, the migration steps) into an executable change plan.

## Rules

- **Evidence over taste.** Every volatility cites evidence: the user's words, the roadmap,
  or git history. Every component traces to a volatility; every brick to a feature or a
  volatility.
- **Never name a component after a feature.** Names come from the volatility hidden inside.
- **APIs speak business verbs.** No CRUD, no vendor types, no storage details across
  a wall.
- **Walls before bricks; bricks never decide where walls go.** They can only prompt a
  re-check.
- **Don't build for imagined futures.** A future feature is used as a test of the design,
  not as a reason to build it now.
- **Subsystem mode: respect the host.** Follow its conventions, change it only at the seam,
  and keep existing behavior until callers have moved (people depend on it, documented or
  not).
- **Run the validation.** A design that has not been through Phase 5 is a sketch. Say so
  if the user asks to stop early.

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
