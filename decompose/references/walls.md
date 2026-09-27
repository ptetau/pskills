# Walls: volatility-based decomposition

How to decide the components, their boundaries, and who may call whom. The bricks (see
`bricks.md`) are designed inside these walls afterwards. Sources are in `sources.md`.

## The idea in one paragraph

Decompose a system by what is likely to change, not by what it does. Parnas (1972): "one
begins with a list of difficult design decisions or design decisions which are likely to
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
verbs in each component's API.

## Finding the volatilities

### Two axes

There are only two ways a system faces change:

1. **The same customer, over time.** What will this user or business need differently in
   a year, or in five?
2. **Different customers, at the same time.** What differs between users, tenants,
   regions, or markets today?

A "customer" can be a person or a whole business. Each volatility should sit mainly on
one axis; Löwy calls the assignment a matter of "disproportional probability", not
exclusion. If a candidate fits neither axis, don't encapsulate it: building a component for
it usually signals functional decomposition. If a candidate can't be placed mainly on one
axis, that "often indicates a functional decomposition in disguise." Split it until each
part has a home axis.

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
- **History.** Look back as far as the system is expected to live. Löwy: if the projected
  lifespan is five to seven years, start by listing everything that changed in the domain
  over the past seven. Things that changed often will keep changing at about the same rate. In an existing codebase,
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
| **Client** | who calls, and the technology they call with: UI, API, scheduler, other systems | who | Löwy: ideally a single point of entry into the system, and at least as few as possible, because every entry point is another place to handle authentication, authorization, scalability, and hosting |
| **Manager** | the volatile *sequence* of a family of related use cases (a workflow) | what | Mostly composition. Should be "almost expendable" |
| **Engine** | a volatile *activity*: a business rule, calculation, or algorithm | how | Löwy: essentially the Strategy pattern. May be shared between Managers |
| **ResourceAccess** | volatile *access* to a resource, including resources in other systems | how (to reach it) | Exposes **atomic business verbs**, not CRUD or I/O |
| **Resource** | the physical store or external system | where | Call it Storage, not Database: the kind may change |
| **Utility** | infrastructure common to all components: security, logging, diagnostics, pub/sub, message bus, hosting | — | Test: could it be used in a completely different system, such as a smart cappuccino machine? If not, it is not a Utility |

**Atomic business verbs.** A bank's ResourceAccess exposes `Credit` and `Debit`, not
`UpdateBalance` or `ExecuteSql`. Those verbs relate to the nature of the business, so they
are nearly immutable, while the storage behind them can change freely.

A new workflow step that reorders or reuses existing facts changes only the Manager. A
step that records a *new kind* of business fact needs a new verb; that is a new activity,
not just a new sequence, so touching ResourceAccess is expected. Don't dodge it with a
generic verb such as `RecordEvent`: that is CRUD by another name.

**Vendors that reach the Client.** Some vendors touch the edge directly: an embedded
widget, an inbound webhook. Keep the vendor-specific part in a thin Client adapter that
hands the Manager a vendor-neutral result (a token, a normalized event). Everything
after that goes through ResourceAccess.

**Volatilities map to components, not one to one.** A component may hold several related
volatilities. Some volatilities map to an operational concept (a queue, published events)
or to a third-party service rather than to your own component.

## Call rules

Default to a **closed architecture**: each component calls only the layer directly below.
Löwy sanctions four relaxations:

1. Anyone may call Utilities.
2. Managers and Engines may call ResourceAccess.
3. Managers may call Engines.
4. A Manager may **queue** a call to another Manager. Löwy counts this as calling down:
   "the proxy is a ResourceAccess to the underlying Resource, the queue; that is, the call
   actually goes down, not sideways." If more than one Manager must react, publish an
   event through the pub/sub Utility instead of queuing to each.

And these don'ts:

- **Never call up.** The worst violation: it imports the volatility of a higher layer into
  a lower one.
- **Never call sideways**, except queued Manager-to-Manager calls. Engines never call
  Engines. ResourceAccess components never call each other.
- Clients call **one** Manager per use case, and never call Engines directly.
- A Manager queues calls to at most one other Manager per use case.
- Engines and ResourceAccess never receive queued calls.
- Only Managers publish events. Clients and Managers may subscribe. Engines,
  ResourceAccess, and Resources neither publish nor subscribe.

| Caller ↓ may call → | Manager | Engine | ResourceAccess | Resource | Utility |
|---------------------|---------|--------|----------------|----------|---------|
| Client | one per use case | no | no | no | yes |
| Manager | queued only | yes | yes | no | yes |
| Engine | no | no | yes | no | yes |
| ResourceAccess | no | no | no | yes | yes |

When a rule is broken, don't wave it through and don't just demand compliance. Find out
why the design wanted the call, then move the responsibility, or use a queue or an event.

## Naming

- Managers, Engines, and ResourceAccess: two-part PascalCase, a prefix plus the type as
  suffix. `TradeManager`, `PricingEngine`, `MembersAccess`. Clients and Utilities are named
  for what they are (`AdminPortal`, `Scheduler`, `Logging`).
- Manager prefix: a noun for the volatility of its use cases (`Enrollment`, `Notification`).
- Engine prefix: a gerund or activity noun (`Pricing`, `Routing`, `Rendering`). Gerunds
  belong to Engines only; a gerund elsewhere hints at functional decomposition. If the
  prefix is also a feature's name (`Suggestion`), ask what activity would survive a
  redesign of the feature (`Prediction`, `Matching`) and use that.
- ResourceAccess prefix: a noun for the resource or its data (`Members`, `Payments`).
- Never name a component after a feature (`BlackFridayDiscountService`) or a verb
  (`SendEmail`). The business verbs belong in the API, not the name.

## Concerns that touch every component

**Cross-cutting business concerns** (audit trail, authorization, tenancy) touch every
write but fail the cappuccino test, because they carry business meaning. Split each into
three parts:

| Part | Where it goes |
|------|---------------|
| The mechanism (a journal, a permission check, a tenant context) | a Utility |
| The business policy (what is audited, who may do what) | a policy brick in an Engine, or data |
| The enforcement point | the ResourceAccess verb, when it must hold atomically with the write; the Manager, when it is a workflow-level check |

Security is stricter. IDesign's rule is to authenticate and authorize at every crossing
of a service boundary, with each tier authenticating its immediate callers. Tenant and
caller identity travel in the call context, not as a parameter on every verb.

This three-way split is the skill's synthesis; Löwy places security in Utilities and says
little about audit or tenancy.

**Writes that must be atomic across resources.** ResourceAccess components never call
each other, so a write that spans two of them becomes the Manager's problem. First try to
avoid it: put the facts that must change together behind one ResourceAccess, with one
verb for the whole business action. When that is impossible, the Manager runs the steps
as a State machine, and each step has a compensating verb that undoes it (a saga).

## Size and shape

Löwy's experience (heuristics, not studies):

- About ten building blocks, in order of magnitude. "Even in a large system you are
  commonly looking at two to five Managers, two to three Engines, three to eight
  ResourceAccess and Resources, and a half-dozen Utilities."
- Fewer Engines than Managers: "If your system has two Managers, you will likely need one
  Engine. If your system has three Managers, two Engines is likely your number." Many
  Engines may mean functional decomposition.
- Eight Managers means the decomposition has already failed (it is functional).
- Volatility should **decrease** going down the layers, and reuse should **increase**.
  In the skill's reading this is about *APIs*: a ResourceAccess over a volatile vendor
  changes often inside, but its business verbs should rarely change.
- Good architectures are symmetric: similar use cases produce similar call patterns.
  Investigate any asymmetry.

**The expendability test for a Manager.** Imagine a change request against it. If you
would fight it (too big, too costly), the Manager holds more than a sequence and is likely
functional. If you would shrug (nothing to it), the Manager is expendable, which Löwy calls
"always a design flaw"; the skill's remedy is to merge it. If you would think it through and
estimate it, it is "almost expendable", which is right.

Treat all of these as smell checks. When the design falls outside them, write down why.

## Features, core use cases, and validation

**Features are integration, not implementation.** Löwy: "features are always and
everywhere aspects of integration, not implementation." A podcast exists in no single
device; it is what the devices do together. A new feature should normally mean a Manager
change or a new interaction between existing components, not new Engines, ResourceAccess,
or Resources.

**Core use cases.** Separate the core use cases, which express the essence of the
business, from everything else (variations, "fluff"). Löwy: typically two or three,
seldom more than six. His own TradeMe case study has one. They don't change unless the
nature of the business changes.

**Composable design.** Find the smallest set of components that can be put together to
satisfy all the use cases, present and future. Every non-core use case should be a
different interaction between the same components.

**Validation.** Löwy: once every core use case can be produced as an interaction between
the components, the design is valid. Draw each core use case as a call chain over
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
| CRUD verbs, SQL, or vendor types in a ResourceAccess API | Access is not encapsulated |
| A `Reporting` component with no volatility behind it, or a component named after a technology (`Database`) | A solution disguised as a requirement |
| Many components, each for a change nobody expects | Speculative design |
| More than five Managers, or more Engines than Managers | Probably functional; check against the size heuristics |
| A generic verb such as `RecordEvent` or `Save` on a ResourceAccess | CRUD by another name |
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
- **Common Closure Principle** (Martin, *Clean Architecture*): "Gather into components those classes that change
  for the same reasons and at the same times. Separate into different components those
  classes that change at different times and for different reasons."
- **Single Responsibility Principle** (Martin, *Clean Architecture*): "A module should be
  responsible to one, and only one, actor." In his 2014 essay: "the reasons for change are
  people."
- **Stable Dependencies Principle**: "Depend in the direction of stability." Löwy's
  downward calls are the same idea: volatile Managers depend on stabler Engines and
  ResourceAccess.
- **Stable Abstractions Principle** (*Clean Architecture*): "A component should be as
  abstract as it is stable."
- Parnas: "The sequence in which certain items will be processed should (as far as
  practical) be hidden within a single module." In the skill's reading, that is the
  Manager's job.
- **Change simulation** (Phase 5) is Parnas's own test. He listed changes "likely to
  change" and compared the two designs by whether each change stayed in one module: "the
  second change would result in changes in every module!"
