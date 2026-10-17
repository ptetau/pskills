# Walls: volatility-based decomposition

This file tells you how to decide the components, their boundaries, and which component
can call which component. After the walls, you design the bricks inside the walls (see
`bricks.md`). `sources.md` gives the sources.

## The idea in one paragraph

Decompose a system by what is likely to change, not by what the system does. Parnas
(1972): "one begins with a list of difficult design decisions or design decisions which
are likely to change. Each module is then designed to hide such a decision from the
others." Löwy (*Righting Software*, 2019) makes this idea into a method:

1. Identify the areas of possible change.
2. Encapsulate each area in a component.
3. Implement the necessary behaviour as the interaction between those components.

When a change comes, you "open the door of the appropriate vault, toss the grenade inside,
and close the door." Without the walls, a change "is like swallowing a live hand grenade."

## Why not decompose by feature or by domain

**By feature** (functional decomposition): for example, an Invoicing service, a Billing
service, and a Shipping service. The structure mirrors the requirements. Thus, each change
to a requirement becomes a change to the structure. The services become too large or too
small, and they are chained in a fixed order. The client must join the services together
("the client is no longer the client — it has become the system").

Löwy's prime directive: **never design against the requirements.** Use functional
decomposition to *find* requirements, but not to structure the design.

**By domain** (Kitchen and Bedroom, or Customers, Orders, and Products) is functional
decomposition in disguise: the kitchen is where you cook. Each domain gets a copy of the
same volatility. Then the domains talk to each other in CRUD-like state changes. Löwy
gives one exception: domain decomposition works when the domains map to areas of
volatility by chance. Domain language is still the correct source for *names*, and for the
business verbs in the API of each component.

## Finding the volatilities

### Two axes

A system gets change in only two ways:

1. **The same customer, over time.** What will this user or business need differently in
   a year, or in five?
2. **Different customers, at the same time.** What differs between users, tenants,
   regions, or markets today?

A "customer" can be a person or a complete business. Each volatility must be mainly on one
axis. Löwy calls this assignment a matter of "disproportional probability", not exclusion.

If a candidate fits no axis, do not encapsulate the candidate. A component for such a
candidate usually shows functional decomposition. If you cannot put a candidate mainly on
one axis, this "often indicates a functional decomposition in disguise." Split the
candidate until each part has a home axis.

**Factoring loop.** Start with the full system as one component. Ask: could this customer
use it forever as is? If not, put a wall around what would change. Ask: could every
customer use it right now? If not, put a wall around what differs. Repeat until the two
answers are yes.

### Prompts that surface candidates

- **Solutions disguised as requirements.** For example: "Send an email", "store it in
  Postgres", "cook dinner". For each solution, ask what other solutions exist. Cooking
  becomes feeding, and feeding becomes wellbeing. Email becomes "reach the user", and the
  volatility is the channel.
- **Named vendors, products, and formats.** Each one is a candidate.
- **"For now", "initially", "phase 1", "until".** Somebody already expects a change.
- **Numbers and thresholds.** A number or a threshold is usually a variable (a
  parameter). Sometimes the number is a sign of a volatile rule behind it.
- **Regulation and region.** Rules that are different for each jurisdiction are on the
  second axis.
- **Competitors.** If each competitor does an activity the same way, the activity needs no
  wall. Where the competitors are different, your business can change.
- **History.** Look back over a period as long as the expected life of the system. Löwy: if
  the projected lifespan is five to seven years, first list each thing that changed in
  the domain over the past seven years. Things that changed frequently will continue to
  change at about the same rate. In an existing codebase, measure the history (see
  `brownfield.md`).

Write the list **before** you design a component.

### Filters

| Candidate is | Test | Do |
|--------------|------|----|
| **Volatile** | Open-ended. If there is no wall around it, a change would ripple through many components | Give it a wall |
| **Variable** | Bounded. Data, a parameter, or a conditional in one place can easily handle it | Handle it inside a component |
| **The nature of the business** | The change is rare, *and* each attempt to encapsulate it can only give a poor result (a house that becomes a 50-storey tower) | Do not put a wall around it |
| **Speculative** | No evidence that it will change in the life of the system (SCUBA-ready high heels) | Record it. Do not put a wall around it |

The nature of the business applies at each scale: company, division, and application. A
design with many walls for speculative change is "a clear sign of a bad design."

## Component types

A use case can change in only two ways: its **sequence** changes, or an **activity** in it
changes. Managers hold the sequence. Engines hold the activity.

| Type | Encapsulates | Answers | Notes |
|------|--------------|---------|-------|
| **Client** | who calls, and the technology that they call with: UI, API, scheduler, other systems | who | Löwy: ideally one point of entry into the system, or at least as few as possible. Each entry point is one more place to handle authentication, authorisation, scalability, and hosting |
| **Manager** | the volatile *sequence* of a family of related use cases (a workflow) | what | Mostly composition. The target is "almost expendable" |
| **Engine** | a volatile *activity*: a business rule, calculation, or algorithm | how | Löwy: essentially the Strategy pattern. Managers can share an Engine. Pure by default (the Manager passes the data in). If an Engine must read, it calls ResourceAccess, and the design says so |
| **ResourceAccess** | volatile *access* to a resource, also to resources in other systems | how (to reach it) | Exposes **atomic business verbs**, not CRUD or I/O |
| **Resource** | the physical store or external system | where | Call it Storage, not Database, because the kind can change |
| **Utility** | infrastructure common to all components: security, logging, diagnostics, pub/sub, message bus, hosting | — | Test: can a completely different system use it, for example a smart cappuccino machine? If not, it is not a Utility |

**Stable business rules** (the nature of the business, for example the rules of a game or
a fixed calculation) get no wall of their own. Put these rules in a domain module. The
domain module is pure, with no volatility of its own and no dependencies. Each component
that needs the rules uses the domain module. The domain module is not a component, and it
is not a Utility (it fails the cappuccino test). With the rules in the domain module,
Managers stay pure orchestration, also when a Manager is the only component that needs
the rules.

The domain-module rule comes from this skill. Löwy does not say where unwalled logic
lives.

**Atomic business verbs.** The ResourceAccess of a bank exposes `Credit` and `Debit`, not
`UpdateBalance` or `ExecuteSql`. `Credit` and `Debit` relate to the nature of the
business. Thus, these verbs are nearly immutable, but the storage behind them can change
freely.

A new workflow step that reorders or reuses existing facts changes only the Manager. A
step that records a *new kind* of business fact needs a new verb. This step is a new
activity, not only a new sequence. Thus, a change to ResourceAccess is expected. Do not
use a generic verb such as `RecordEvent` in place of the new verb. A generic verb is CRUD
by another name.

**Vendors that reach the Client.** Some vendors touch the edge directly, for example an
embedded widget or an inbound webhook. Keep the vendor-specific part in a thin Client
adapter. The adapter gives the Manager a vendor-neutral result (a token, a normalised
event). After that point, everything goes through ResourceAccess.

**Volatilities map to components, but not one to one.** A component can hold several
related volatilities. Some volatilities map to an operational concept (a queue, published
events) or to a third-party service, not to your own component.

## Call rules

The default is a **closed architecture**: each component calls only the layer directly
below it. Löwy gives four relaxations:

1. All components can call Utilities.
2. Managers and Engines can call ResourceAccess.
3. Managers can call Engines.
4. A Manager can **queue** a call to a different Manager. Löwy counts this as a call
   down: "the proxy is a ResourceAccess to the underlying Resource, the queue; that
   is, the call actually goes down, not sideways." If more than one Manager must react,
   publish an event through the pub/sub Utility. Do not queue a call to each Manager.

Also obey these rules:

- **Do not call up.** A call up is the worst violation. The call imports the volatility of
  a higher layer into a lower layer.
- **Do not call sideways**, except for queued Manager-to-Manager calls. An Engine does not
  call an Engine. A ResourceAccess component does not call a different ResourceAccess
  component.
- A Client calls **one** Manager for each use case. A Client does not call Engines
  directly.
- A Manager queues calls to a maximum of one other Manager for each use case.
- Engines and ResourceAccess do not receive queued calls.
- Only Managers publish events. Clients and Managers can subscribe. Engines,
  ResourceAccess, and Resources do not publish and do not subscribe.

| Caller ↓ can call → | Manager | Engine | ResourceAccess | Resource | Utility |
|---------------------|---------|--------|----------------|----------|---------|
| Client | one per use case | no | no | no | yes |
| Manager | queued only | yes | yes | no | yes |
| Engine | no | no | yes | no | yes |
| ResourceAccess | no | no | no | yes | yes |

When the design breaks a rule, do not accept the break without a question. Also, do not
only demand compliance. Find why the design wanted the call. Then move the
responsibility, or use a queue or an event.

## Naming

- Managers, Engines, and ResourceAccess: use two-part PascalCase, a prefix plus the type as
  suffix. Examples are `TradeManager`, `PricingEngine`, and `MembersAccess`. Give Clients
  and Utilities the name of what they are (`AdminPortal`, `Scheduler`, `Logging`).
- Manager prefix: a noun for the volatility of its use cases (`Enrollment`,
  `Notification`).
- Engine prefix: a gerund or an activity noun (`Pricing`, `Routing`, `Rendering`). Use
  gerunds only for Engines. A gerund in a different name hints at functional
  decomposition. The prefix can also be the name of a feature (`Suggestion`). If so, ask
  which activity would survive a redesign of the feature (`Prediction`, `Matching`). Use
  that activity as the prefix.
- ResourceAccess prefix: a noun for the resource or its data (`Members`, `Payments`).
- Do not name a component after a feature (`BlackFridayDiscountService`) or a verb
  (`SendEmail`). The business verbs belong in the API, not in the name.

## Concerns that touch every component

**Cross-cutting business concerns** (audit trail, authorisation, tenancy) touch each write.
But these concerns fail the cappuccino test, because they carry business meaning. Split
each concern into three parts:

| Part | Where it goes |
|------|---------------|
| The mechanism (a journal, a permission check, a tenant context) | a Utility |
| The business policy (what to audit, who can do what) | a policy brick in an Engine, or data |
| The enforcement point | the ResourceAccess verb, when the check must hold atomically with the write. The Manager, when the check is a workflow-level check |

Security is stricter. The IDesign rule: authenticate and authorise at each crossing of a
service boundary. Each tier authenticates its immediate callers. Tenant and caller
identity go in the call context, not as a parameter on each verb. When the audited data
is itself the record of the system (a ledger of each balance change), do not build a
second audit trail. The record is the audit trail.

The three-way split of cross-cutting concerns is a synthesis of this skill. Löwy puts
security in Utilities, and says little about audit or tenancy.

**Writes that must be atomic across resources.** ResourceAccess components do not call
each other. Thus, a write that spans two ResourceAccess components becomes the problem of
the Manager.

First, try to prevent a write across two ResourceAccess components. Put the facts that
must change together behind one ResourceAccess, with one verb for the full business
action. If this is not possible, the Manager runs the steps as a State machine. Each step
then has a compensating verb that undoes the step (a saga).

## Size and shape

These numbers come from Löwy's experience (heuristics, not studies):

- About ten building blocks, as an order of magnitude. "Even in a large system you are
  commonly looking at two to five Managers, two to three Engines, three to eight
  ResourceAccess and Resources, and a half-dozen Utilities."
- Fewer Engines than Managers: "If your system has two Managers, you will likely need one
  Engine. If your system has three Managers, two Engines is likely your number." Many
  Engines can show functional decomposition.
- Eight Managers show that the decomposition already failed (it is functional).
- In a good design, volatility **decreases** as you go down the layers, and reuse
  **increases**. This skill reads this heuristic as a rule about *APIs*. A
  ResourceAccess over a volatile vendor changes frequently inside, but its business verbs
  change only rarely.
- Good architectures are symmetric: similar use cases make similar call patterns.
  Investigate each asymmetry.

**The expendability test for a Manager.** Imagine a change request for the Manager. Then
look at your reaction:

- If your reaction is to fight the change (too large, too costly), the Manager holds more
  than a sequence. The Manager is probably functional.
- If your reaction is a shrug (nothing to it), the Manager is expendable. Löwy calls an
  expendable Manager "always a design flaw". The remedy of this skill is to merge the
  Manager.
- If your reaction is to think about the change carefully and estimate it, the Manager is
  "almost expendable". This result is correct.

Treat the size heuristics and the expendability test as smell checks. When the design is
outside these checks, write the reason.

## Features, core use cases, and validation

**Features are integration, not implementation.** Löwy: "features are always and
everywhere aspects of integration, not implementation." A podcast does not exist in one
device. A podcast is what the devices do together. In a good design, a new feature is
usually a change to a Manager or a new interaction between existing components. A new
feature is usually not new Engines, ResourceAccess, or Resources.

**Core use cases.** The core use cases express the essence of the business. Separate the
core use cases from all other use cases (variations, "fluff"). Löwy: typically two or
three, and seldom more than six. His own TradeMe case study has one. The core use cases do
not change unless the nature of the business changes.

**Composable design.** Find the smallest set of components that you can assemble to
satisfy all the use cases, present and future. The goal is that each non-core use case is
a different interaction between the same components.

**Validation.** Löwy: when you can make each core use case as an interaction between the
components, the design is valid. Draw each core use case as a call chain over the layer
diagram. Write one line for each call, so that the direction of each call is visible:

```
UC1 notify about an event
  EventsApi           → NotificationManager.Notify
  NotificationManager → RoutingEngine.RecipientsFor
  NotificationManager → RecipientsAccess.Find
  NotificationManager → RoutingEngine.Route
  NotificationManager → RenderingEngine.Render
  NotificationManager → DeliveryAccess.Deliver
```

If you cannot compose a core use case, or if the validation is ambiguous, go back to the
walls.

## Smells

| Smell | Likely cause |
|-------|--------------|
| Components named after features, reports, or screens | Functional decomposition |
| Components named after business nouns, each with its own full set of parts | Domain decomposition |
| A Client that calls several Managers to complete one use case | The Client became the system |
| Services chained A → B → C, and each service passes the parameters of the next service | Decomposition by time (a flowchart) |
| CRUD verbs, SQL, or vendor types in a ResourceAccess API | Access is not encapsulated |
| A `Reporting` component with no volatility behind it, or a component named after a technology (`Database`) | A solution disguised as a requirement |
| Many components, each for a change that nobody expects | Speculative design |
| More than five Managers, or more Engines than Managers | Probably functional. Compare the design with the size heuristics |
| A generic verb such as `RecordEvent` or `Save` on a ResourceAccess | CRUD by another name |
| An Engine that calls a different Engine | A hidden sequence. The sequence belongs in a Manager |
| A lower layer that calls or subscribes to a higher layer | A call up |
| One likely change that touches several components | A volatility spread across walls |

## Limits of the method

- The numbers (component counts, ratios, core use-case counts) come from the experience
  of one practitioner. The numbers are not empirical results. Löwy himself gives a
  warning: do not use his case study as a template.
- The method is opinionated, also about names. The method rejects domain decomposition in
  cases where DDD practitioners accept it. Keep the language of the domain for names and
  verbs, also where the structure follows volatility.
- The method says little about how to implement a Manager or an Engine. The bricks in
  `bricks.md` fill that gap.

## Related principles

- **Encapsulate what varies** (Gang of Four, 1994): "consider what you want to be able to
  change without redesign… encapsulating the concept that varies."
- **Common Closure Principle** (Martin, *Clean Architecture*): "Gather into components
  those classes that change for the same reasons and at the same times. Separate into
  different components those classes that change at different times and for different
  reasons."
- **Single Responsibility Principle** (Martin, *Clean Architecture*): "A module should be
  responsible to one, and only one, actor." In his 2014 essay: "the reasons for change are
  people."
- **Stable Dependencies Principle**: "Depend in the direction of stability." The downward
  calls of Löwy are the same idea: volatile Managers depend on more stable Engines and
  ResourceAccess.
- **Stable Abstractions Principle** (*Clean Architecture*): "A component should be as
  abstract as it is stable."
- Parnas: "The sequence in which certain items will be processed should (as far as
  practical) be hidden within a single module." In the reading of this skill, to hide the
  sequence is the work of the Manager.
- **Change simulation** (Phase 5) is Parnas's own test. Parnas listed changes "likely to
  change". Then he compared the two designs: did each change stay in one module? Parnas
  found that "the second change would result in changes in every module!"
