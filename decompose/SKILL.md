---
name: decompose
description: >
  Software design for a new system (inception) or a new subsystem inside an
  established codebase. First sets the walls with volatility-based decomposition:
  components are placed around what is likely to change (Managers for changing
  workflows, Engines for changing business rules, ResourceAccess for changing storage
  and third parties) so a change lands in one place. Then designs the inside of each
  wall as a small set of orthogonal, composable primitives (inputs, transforms,
  transports, stores, state machines) so features are assembled from bricks instead of
  hand-built. In an existing codebase it measures volatility from git history (hotspots
  and change coupling) instead of guessing. Validates the design by walking the core
  use cases, simulating each likely change, and assembling current and future features
  from the bricks, then writes a `<name>.design.md`. Use when the user says
  "/decompose", asks to design, architect, or break down a system or subsystem, asks
  where service or module boundaries should go, wants to turn a brainstormed feature
  list into an architecture, or asks how to add a subsystem to an existing codebase
  without the change rippling everywhere.
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
   count the components it touches (the target is one). Assemble current and plausible
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

- **Decompose by what changes, not by what the system does.** (Parnas 1972: hide each
  design decision that is likely to change inside one module. Löwy, *Righting Software*
  2019: decompose based on volatility.)
- **Volatile is not the same as variable.** A value that changes (a rate, a limit, a
  list) is handled by data or a parameter. A thing is *volatile* when its change would
  ripple across the system if left unwrapped.
- **Look along two axes.** What changes for one customer over time? What differs between
  customers at the same moment?
- **Don't wall off the nature of the business.** Things that would make it a different
  system if they changed are not volatilities. Walling them off is speculative design.
- **Each volatility maps to one component type:**

  | Type | Encapsulates | Example |
  |------|--------------|---------|
  | Client | who and what calls the system (UI, API, scheduler, other systems) | `AdminPortal` |
  | Manager | the volatile *sequence*: the order of steps in a family of related use cases (a workflow) | `EnrollmentManager` |
  | Engine | a volatile *activity*: a business rule, calculation, or algorithm | `PricingEngine` |
  | ResourceAccess | volatile *access* to a resource, exposed as business verbs, not CRUD | `MembersAccess` |
  | Resource | the actual store or external system | database, vendor API |
  | Utility | cross-cutting plumbing any component may use | logging, security, pub/sub |

- **Calls go down, never up, and never sideways.** Clients call one Manager per use case
  and never call Engines. Managers call Engines and ResourceAccess. Engines call
  ResourceAccess. Everything may call Utilities. Managers talk to other Managers only
  through a queue. Engines don't call Engines; ResourceAccess components don't call each
  other. Only Managers publish or subscribe to events.
- **Features live in the integration, not in one component.** Löwy: "features are always
  and everywhere aspects of integration, not implementation." A feature is a particular
  way the Manager puts Engines and ResourceAccess together. Adding a feature should mostly
  mean a new composition, not a new component.

### Bricks (orthogonal primitives)

- **Orthogonal means independent.** Changing one brick never requires changing another.
  (Hunt & Thomas's test: if a requirement behind one function changes a lot, how many
  modules are affected? The answer should be one.)
- **Build a small set of brick kinds:**

  | Kind | Does | Example |
  |------|------|---------|
  | Input | brings something into a flow: an event, a request, a timer tick | `OnEvent(type)`, `OnSchedule(cron)` |
  | Transform | turns data into data, or into a decision; pure where possible | `Render`, `Match`, `QuietHours` |
  | Transport | moves data somewhere else: a vendor, a queue, a file, another service | `Email.send`, `Publish` |
  | Store | keeps data and hands it back through business verbs | `Collect(window)` backed by a log |
  | State machine | remembers where a long-running thing is and what may happen next | `Delivery`: pending → sent → failed → retrying |

- **One shared contract.** Every brick accepts and returns the same shape (an envelope,
  record, or event). This is what makes composition free: any brick can follow any other,
  and a composition can itself be used as a brick.
- **Separate mechanism from policy.** Bricks are mechanism. What to do in a given case
  (which channel, which discount) is policy, supplied as data or as a policy brick.
- **Features are compositions.** Write every feature as `Input → Transform → … → Transport`.
  A feature that cannot be written that way either needs a genuinely new brick (justify
  it) or reveals a wrong wall.
- **Guardrails against over-building.** A brick earns its place by serving two or more
  current features, or by being the one home of a recorded volatility. Otherwise leave
  the logic inline in the composition. When extracting bricks from existing code, wait
  for the third occurrence (rule of three), and prefer duplication over the wrong
  abstraction. Keep compositions in code until the composition itself is a volatility
  (for example, flows that differ per customer); a config format that grows loops and
  conditionals has become a worse programming language.

### The hybrid: how walls and bricks fit together

| Wall | What its bricks look like |
|------|---------------------------|
| Manager | the composition layer: it assembles flows from Inputs, calls to Engines and ResourceAccess, and State machines. When workflows are volatile, the flow becomes data the Manager runs. |
| Engine | a family of Transforms and policy bricks behind one stable contract. New rules are new bricks or new data, not new call paths. |
| ResourceAccess | Stores and Transports behind business verbs. Vendor and storage details never cross its contract. |
| Utility | stable bricks shared by everyone. |
| Client | Inputs plus presentation. |

Three rules connect the two ideas:

1. **Walls first, bricks second, then re-check the walls.** Bricks often reveal that two
   walls hide the same volatility (merge them) or that one wall hides two (split it).
2. **Only stable bricks cross walls.** Volatile bricks stay inside their wall. Sharing a
   volatile brick between two walls couples them. Shared bricks belong in Utilities.
3. **A wall's contract never exposes its bricks.** Callers use business verbs. How the
   bricks are wired inside is the wall's own business, free to change.

## Two modes

| | Inception | Subsystem of an established system |
|---|---|---|
| Input | brainstormed features, goals | a request, plus the host codebase |
| Volatility evidence | business reasoning, interviews, roadmap | git history (`scripts/volatility.py`), commit messages, tickets, plus reasoning |
| Walls | the whole system | the subsystem plus its seam to the host; the host's walls are given |
| Extra output | — | attach point, anti-corruption layer, migration steps |
| Extra risk | speculative walls | leaky seams; host code that depends on current behavior |

The details of subsystem mode are in `references/brownfield.md`.

## Phase 0 — Frame

Goal: know the mode, the scope, and the inputs before designing anything.

1. **Pick the mode.** Inception if there is no host code for this area. Subsystem if the
   design must live inside an existing codebase.
2. **Collect the feature list.** Use what the user gave. If they gave only a sentence,
   brainstorm the likely features and show them for confirmation.
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

Output: a short frame (problem, users, constraints, host facts) and a numbered feature
list (F1, F2, …).

## Phase 1 — Core use cases

Goal: separate the essence from the variations.

1. Rewrite each feature as a use case: who does what, and what the system does in response.
2. Group variations. "Welcome email", "reset SMS", and "Slack alert" are one core use case
   ("notify someone about an event") with different parameters.
3. Mark the **core use cases**: the few that express what the system is for. Most
   systems have two or three, and seldom more than six. Everything else should turn out
   to be a variation of these.
4. Write down the **nature of the business**: what will stay true for the life of the
   system. These things are not walled off.

## Phase 2 — Volatility register

Goal: a list of what is likely to change, with evidence, and a list of what was rejected.

1. **Generate candidates** along both axes (one customer over time, many customers now).
   Good prompts are in `references/walls.md`: named vendors, "for now" and "initially",
   numbers and thresholds, regulation, anything a competitor does differently, anything
   that changed in the domain over the last five to seven years.
2. **Look for solutions disguised as requirements.** "Send a Twilio SMS" is a solution. The
   need is "reach the user fast"; the volatility is the channel and the vendor.
3. **Filter each candidate:**
   - *Variable, not volatile?* Handle it with data or a parameter inside one component.
   - *Nature of the business?* Don't wall it off.
   - *Speculative?* No evidence it will change. Record it and move on.
4. **Record the survivors** as V1, V2, … with the axis, the evidence, and a likelihood.
   Subsystem mode: cite the git evidence (hotspot, coupling, commit messages).

## Phase 3 — Walls

Goal: components, their types, their contracts, and the call graph.

1. **Assign each volatility to one component** of the right type (the table above). A
   component may hold several related volatilities. Name each component for the
   volatility it hides, not for a feature: `PricingEngine`, not
   `BlackFridayDiscountService`. Names are two-part PascalCase with the type as suffix;
   gerund prefixes are for Engines only.
2. **Write each component's contract as business verbs.** ResourceAccess exposes verbs such
   as `Deliver`, `FindRecipients`, `RecordOutcome`, never `Insert`, `Update`, `Select` or a
   vendor's API.
3. **Draw the call graph** by layer and check the call rules. Fix violations by moving
   responsibility, not by adding exceptions.
4. **Check the size and shape.** Löwy's heuristics: about ten components in order of
   magnitude, two to five Managers, fewer Engines than Managers, a dozen or two components
   at most. Eight Managers means feature-based decomposition. Volatility should decrease
   going down the layers. Apply the expendability test to each Manager (see
   `references/walls.md`). These are smell checks, not targets: when the design falls
   outside them, write down why.
5. **Subsystem mode:** fit the new walls to the host. Pick the attach point (the seam),
   and put an anti-corruption layer between host concepts and the subsystem's contract.

## Phase 4 — Bricks

Goal: for each component, a small catalog of orthogonal bricks and a shared contract.
Start with the most volatile component. See `references/bricks.md` for tests and smells.

1. **List what the component must support**: its share of the features, plus the
   volatilities it contains.
2. **Write each feature as a short sentence and pull out the verbs.** Verbs that recur
   across features are brick candidates. Classify each: Input, Transform, Transport,
   Store, or State machine.
3. **Define the shared contract**: the one data shape bricks exchange, its fields and
   invariants. Every brick is `contract → contract` (a policy may return zero or many).
4. **Split any brick that does two things.** A brick with a `mode` or `type` flag that
   switches between behaviors is two or more bricks.
5. **Separate mechanism from policy.** Hard-coded "which" and "when" become policy bricks
   or data.
6. **Choose the composition medium**: plain code by default; a pipeline definition, rule
   table, or state-machine table only when the composition itself is a recorded volatility.
7. **Re-check the walls** (rule 1 of the hybrid). Merge or split components if the bricks
   say so.

## Phase 5 — Validate

Goal: prove the design, don't assert it. Run every check and record the results in the
design doc. Fix and re-run until they pass, or record why a failure is accepted.

1. **Use-case walkthrough.** Write each core use case as a call chain through the walls,
   one `Caller → Callee.Verb` per line so the direction of every call is visible. It must
   need no new component and break no call rule.
2. **Change simulation.** For each volatility in the register, imagine it happening. List
   the components that must change. Target: exactly one. Two or more means a leaky wall.
3. **Feature assembly.** Write every current feature, and two or three plausible future
   ones drawn from the register, as compositions of existing bricks. Target: zero new
   bricks for current features, at most one for a future change, inside one component.
4. **Orthogonality check.** For each brick, ask: if its requirement changed a lot, what
   else would change? Anything other than "nothing" is a hidden dependency.
5. **Rule and smell audit.** Call rules, names, sizes, and the smell list in
   `references/walls.md` and `references/bricks.md`.
6. **Trace audit.** Every wall traces to a volatility and every brick to a feature or a
   volatility. Anything that traces to neither goes on the cut list.
7. **Subsystem mode: measured coupling.** For every component pair above the coupling
   threshold in the volatility report, say whether the design puts a wall between them
   and why the coupling will fall. Name the metric to re-check after the change ships.

## Phase 6 — Write it up

1. Write `<name>.design.md` at the project root (or where the user asks), from
   `references/design-template.md`. Size the document to the problem: a one-wall
   subsystem does not need a layer diagram.
2. Show a compact summary in chat, in a code block:

   ```
   DECOMPOSE: <name> · <inception | subsystem of X>
   ══════════════════════════════════════════════════
   VOLATILITIES  <n> contained · <n> rejected
   WALLS         <n> Managers · <n> Engines · <n> ResourceAccess · <n> Utilities
   BRICKS        <n> across <n> components · contract: <name>
   ──────────────────────────────────────────────────
   USE CASES     <passed>/<total> walk through cleanly
   CHANGE SIM    <passed>/<total> volatilities touch one component
   FEATURES      <n> current assembled · <n> future with ≤1 new brick
   VERDICT       ready | <n> leaks to resolve: <short list>
   ```

3. Offer next steps: `/argue` the design doc to check it for contradictions, and
   `/quiz-plan` to turn the walls (and, in subsystem mode, the migration steps) into an
   executable change plan.

## Rules

- **Evidence over taste.** Every volatility cites evidence: the user's words, the roadmap,
  or git history. Every wall and brick traces to a volatility or a feature.
- **Never name a component after a feature.** Names come from the volatility hidden inside.
- **Contracts speak business verbs.** No CRUD, no vendor types, no storage details across
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
