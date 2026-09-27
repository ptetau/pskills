# Walls: volatility-based decomposition

How to decide the components, their boundaries, and who may call whom. The bricks (see
`bricks.md`) are designed inside these walls afterwards. Sources are in `sources.md`.

## The idea in one paragraph

Decompose a system by what is likely to change, not by what it does. Parnas (1972):
"begin with a list of difficult design decisions or design decisions which are likely to
change. Each module is then designed to hide such a decision from the others." Löwy
(*Righting Software*, 2019) turns this into a method: identify areas of potential change,
encapsulate each in a component, then implement the required behavior as the
interaction between those components. When a change comes, you "open the door of the
appropriate vault, toss the grenade inside, and close the door." Without the walls, a
change "is like swallowing a live hand grenade."

## Why not decompose by feature or by domain

**By feature** (functional decomposition): an Invoicing service, a Billing service, a
Shipping service. The structure mirrors the requirements, so every requirement change
becomes a structural change. Services end up too big or too small, get chained in a
fixed order, and the client has to stitch them together ("the client is no longer the
client — it has become the system"). Löwy's prime directive: **never design against the
requirements.** Functional decomposition is fine for *discovering* requirements, never
for structuring the design.

**By domain** (Kitchen, Bedroom; Customers, Orders, Products) is functional decomposition
in disguise: the kitchen is where you cook. The same volatility gets copied into every
domain, and the domains end up talking to each other in CRUD-like state changes. Löwy's
one exception: domain decomposition works when the domains happen to map to areas of
volatility. Domain language is still the right source for *names* and for the business
verbs in contracts.

## Finding the volatilities

### Two axes

There are only two ways a system faces change:

1. **The same customer, over time.** What will this user or business need differently in
   a year, or in five?
2. **Different customers, at the same time.** What differs between users, tenants,
   regions, or markets today?

A "customer" can be a person or a whole business. Most volatilities sit mainly on one
axis. If a candidate fits neither, don't encapsulate it; building a component for it
usually signals functional decomposition.

**Factoring loop.** Start with the whole system as one component. Ask: could this
customer use it forever as is? If not, wall off what would change. Ask: could every
customer use it right now? If not, wall off what differs. Repeat until both answers are
yes.

### Prompts that surface candidates

- **Solutions disguised as requirements.** "Send an email", "store it in Postgres",
  "cook dinner". For each, ask what other solutions exist. Cooking becomes feeding becomes
  wellbeing; email becomes "reach the user"; the volatility is the channel.
- **Named vendors, products, and formats.** Each one is a candidate.
- **"For now", "initially", "phase 1", "until".** Someone already expects change.
- **Numbers and thresholds.** Usually variables (a parameter), sometimes a sign of a
  volatile rule behind them.
- **Regulation and region.** Rules that differ by jurisdiction sit on the second axis.
- **Competitors.** If every competitor does an activity the same way, it needs no wall.
  Where they differ is where your business may change.
- **History.** What changed in this domain over the last five to seven years? Things
  that changed often will keep changing at about the same rate. In an existing codebase,
  measure it (see `brownfield.md`).

Write the list down **before** designing any component.

### Filters

| Candidate is | Test | Do |
|--------------|------|----|
| **Volatile** | Open-ended; if left unwrapped, a change would ripple through many components | Give it a wall |
| **Variable** | Bounded; easily handled with data, a parameter, or a conditional in one place | Handle it inside a component |
| **The nature of the business** | The change is rare, *and* any attempt to encapsulate it could only be done poorly (a house becoming a 50-story tower) | Don't wall it off |
| **Speculative** | No evidence it will change within the life of the system (SCUBA-ready high heels) | Record it; don't wall it off |

The nature of the business applies at every scale: company, division, application. A
design with many walls built for speculative change is "a clear sign of a bad design."

## Component types

A use case can change in only two ways: its **sequence** changes, or an **activity**
within it changes. Managers hold the first, Engines the second.

| Type | Encapsulates | Answers | Notes |
|------|--------------|---------|-------|
| **Client** | who calls, and the technology they call with: UI, API, scheduler, other systems | who | Prefer a single point of entry into the system |
| **Manager** | the volatile *sequence* of a family of related use cases (a workflow) | what | Mostly composition. Should be "almost expendable" |
| **Engine** | a volatile *activity*: a business rule, calculation, or algorithm | how | Löwy: essentially the Strategy pattern. May be shared between Managers |
| **ResourceAccess** | volatile *access* to a resource, including resources in other systems | how (to reach it) | Exposes **atomic business verbs**, not CRUD or I/O |
| **Resource** | the physical store or external system | where | Call it Storage, not Database: the kind may change |
| **Utility** | infrastructure common to all components: security, logging, diagnostics, pub/sub, message bus, hosting | — | Test: could it be used in a completely different system, such as a smart cappuccino machine? If not, it is not a Utility |

**Atomic business verbs.** A bank's ResourceAccess exposes `Credit` and `Debit`, not
`UpdateBalance` or `ExecuteSql`. Those verbs relate to the nature of the business, so they
are nearly immutable, while the storage behind them can change freely.

**Volatilities map to components, not one to one.** A component may hold several related
volatilities. Some volatilities map to an operational concept (a queue, published events)
or to a third-party service rather than to your own component.

## Call rules

Default to a **closed architecture**: each component calls only the layer directly below.
Löwy sanctions four relaxations:

1. Anyone may call Utilities.
2. Managers and Engines may call ResourceAccess.
3. Managers may call Engines.
4. A Manager may **queue** a call to another Manager. This counts as calling down: the
   queue is a resource, reached through its own access layer.

And these don'ts:

- **Never call up.** The worst violation: it imports the volatility of a higher layer into
  a lower one.
- **Never call sideways**, except queued Manager-to-Manager calls. Engines never call
  Engines. ResourceAccess components never call each other.
- Clients call **one** Manager per use case, and never call Engines directly.
- A Manager queues calls to at most one other Manager per use case.
- Engines and ResourceAccess never receive queued calls.
- Only Managers publish or subscribe to events. Clients, Engines, ResourceAccess, and
  Resources do neither.

| Caller ↓ may call → | Manager | Engine | ResourceAccess | Resource | Utility |
|---------------------|---------|--------|----------------|----------|---------|
| Client | one per use case | no | no | no | yes |
| Manager | queued only | yes | yes | no | yes |
| Engine | no | no | yes | no | yes |
| ResourceAccess | no | no | no | yes | yes |

When a rule is broken, don't wave it through and don't just demand compliance. Find out
why the design wanted the call, then move the responsibility, or use a queue or an event.

## Naming

- Two-part PascalCase: a prefix plus the type as suffix. `TradeManager`, `PricingEngine`,
  `MembersAccess`.
- Manager prefix: a noun for the volatility of its use cases (`Enrollment`, `Notification`).
- Engine prefix: a gerund or activity noun (`Pricing`, `Routing`, `Rendering`). Gerunds
  belong to Engines only; a gerund elsewhere hints at functional decomposition.
- ResourceAccess prefix: a noun for the resource or its data (`Members`, `Payments`).
- Never name a component after a feature (`BlackFridayDiscountService`) or a verb
  (`SendEmail`). The business verbs belong in the contract, not the name.

## Size and shape

Löwy's experience (heuristics, not studies):

- A typical system needs about ten building blocks, in order of magnitude: two to five
  Managers, two to three Engines, three to eight ResourceAccess and Resources, and around
  six Utilities. A dozen or two at most.
- Fewer Engines than Managers: two Managers, likely one Engine; three Managers, likely two.
- Eight Managers means the decomposition has already failed (it is functional).
- Volatility should **decrease** going down the layers, and reuse should **increase**.
- Good architectures are symmetric: similar use cases produce similar call patterns.
  Investigate any asymmetry.

**The expendability test for a Manager.** Imagine a change request against it. If you
would fight it (too big, too costly), the Manager holds more than a sequence and is likely
functional. If you would shrug (nothing to it), the Manager is a pass-through and should be
merged. If you would think it through and estimate it, it is right.

Treat all of these as smell checks. When the design falls outside them, write down why.

## Features, core use cases, and validation

**Features are integration, not implementation.** Löwy: "features are always and
everywhere aspects of integration, not implementation." A podcast exists in no single
device; it is what the devices do together. A new feature should normally mean a Manager
change or a new interaction between existing components, not new Engines, ResourceAccess,
or Resources.

**Core use cases.** Separate the core use cases, which express the essence of the
business, from everything else (variations, "fluff"). Most systems have two or three, and
seldom more than six. They don't change unless the nature of the business changes.

**Composable design.** Find the smallest set of components that can be put together to
satisfy all the use cases, present and future. Every non-core use case should be a
different interaction between the same components.

**Validation.** "Once you can produce an interaction between your services for each core
use case, you have produced a valid design." Draw each core use case as a call chain over
the layer diagram, one line per call, so the direction of each call is visible:

```
UC1 notify about an event
  EventsApi         → NotificationManager.Notify
  NotificationManager → RoutingEngine.Route
  RoutingEngine       → RecipientsAccess.Find
  NotificationManager → RenderingEngine.Render
  NotificationManager → DeliveryAccess.Deliver
```

If a core use case can't be composed, or the validation is ambiguous, go back to the
walls.

## Smells

| Smell | Likely cause |
|-------|--------------|
| Components named after features, reports, or screens | Functional decomposition |
| Components named after business nouns, each with its own everything | Domain decomposition |
| A Client calling several Managers to complete one use case | The Client has become the system |
| Services chained A → B → C, each passing the next one's parameters | Decomposition by time (a flowchart) |
| CRUD verbs, SQL, or vendor types in a ResourceAccess contract | Access is not encapsulated |
| A "Reporting" or "Database" component with no volatility behind it | A solution disguised as a requirement |
| Many components, each for a change nobody expects | Speculative design |
| Five or more Managers, or more Engines than Managers | Probably functional; check against the size heuristics |
| An Engine that calls another Engine | A hidden sequence; it belongs in a Manager |
| A lower layer that calls or subscribes to a higher one | Calling up |
| One likely change touching several components | A volatility smeared across walls |

## Limits of the method

- The numbers (component counts, ratios, core use-case counts) are one practitioner's
  experience, not empirical findings. Löwy himself warns against using his case study as
  a template.
- It is opinionated, down to naming, and it rejects domain decomposition where DDD
  practitioners would not. Keep the domain's language for names and verbs even where the
  structure follows volatility.
- It says little about how to implement a Manager or an Engine. That gap is what the
  bricks in `bricks.md` fill.

## Related principles

- **Encapsulate what varies** (Gang of Four, 1994): "consider what you want to be able to
  change without redesign… encapsulating the concept that varies."
- **Common Closure Principle** (Martin): "Gather into components those classes that change
  for the same reasons and at the same times. Separate into different components those
  classes that change at different times and for different reasons."
- **Single Responsibility Principle** (Martin): "A module should be responsible to one,
  and only one, actor." The reasons for change are people.
- **Stable Dependencies Principle**: "Depend in the direction of stability." Löwy's
  downward calls are the same idea: volatile Managers depend on stabler Engines and
  ResourceAccess.
- **Stable Abstractions Principle**: "A component should be as abstract as it is stable."
- Parnas also said the order in which items are processed should be hidden in a single
  module. That is the ancestor of the Manager.
