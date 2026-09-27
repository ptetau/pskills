# Worked examples

Two compact runs of the method. The first starts from a brainstormed feature list. The
second adds a subsystem to an existing codebase, where volatility is measured, not guessed.

---

## Example 1 — Inception: a notifications service

**Brainstormed features**

| ID | Feature |
|----|---------|
| F1 | Welcome email when someone signs up |
| F2 | Password-reset code by SMS |
| F3 | Daily digest email of activity |
| F4 | Ops alerts posted to Slack |
| F5 | Each user picks their preferred channel |
| F6 | Quiet hours: nothing non-urgent at night |
| F7 | Failed deliveries are retried |
| F8 | Messages in the user's language |

**The trap.** Functional decomposition gives one service per feature: `WelcomeEmailService`,
`DigestService`, `SlackAlertService`, `RetryService`. Each one re-implements "pick a channel,
render a message, send it, record it". Adding WhatsApp then touches every service.

**Core use cases.** The eight features collapse into three:
UC1 notify recipients about an event now (F1, F2, F4, F7, F8);
UC2 notify recipients about accumulated events later (F3);
UC3 recipients choose how and when they are reached (F5, F6).

**Nature of the business** (not walled off): the system tells people about events. A
message has a recipient and content. If that stops being true, it is a different system.

**Volatility register**

| ID | What changes | Axis | Contained by |
|----|--------------|------|--------------|
| V1 | Which channels exist, and which vendor delivers each | over time | `DeliveryAccess` |
| V2 | Who gets what, when: preferences, quiet hours, opt-outs, regional rules | both | `RoutingEngine` |
| V3 | Message content, templates, languages | over time | `RenderingEngine` |
| V4 | Delivery flows: immediate, digest, escalate-if-unread | over time | `NotificationManager` |
| V5 | Where recipient data lives (own DB today, a CRM later) | over time | `RecipientsAccess` |

Rejected: *number of retries* (variable: a parameter, not a wall); *fax support*
(speculative); *stop notifying people* (nature of the business).

**Walls**

```
Clients          EventsApi   AdminPortal   Scheduler
Managers         NotificationManager
Engines          RoutingEngine   RenderingEngine
ResourceAccess   RecipientsAccess   DeliveryAccess   OutboxAccess
Resources        Storage   email / SMS / Slack vendors
Utilities        pub/sub · logging · secrets
```

| Component | Calls |
|-----------|-------|
| each Client | `NotificationManager` only |
| `NotificationManager` | `RoutingEngine`, `RenderingEngine`, `DeliveryAccess`, `OutboxAccess`, `RecipientsAccess` |
| `RoutingEngine` | `RecipientsAccess` |
| `RenderingEngine` | nothing (templates ship with it as files) |

`Scheduler` is a client: time is just another caller. `NotificationManager` owns the flows;
it is the only component that knows the order of steps. `OutboxAccess` has no row in the
register: it hides the system's own storage, which the trace audit counts on its own.

**Size check.** Two departures from Löwy's heuristics, both kept on purpose. One Manager
is below his usual two to five: this service has a single family of use cases. Two
Engines for one Manager is one more than his usual ratio: routing rules and message
content change for different reasons and are owned by different people (product and
compliance versus content writers). Merging them would put two volatilities behind one
wall.

**Bricks.** Shared contract: `Envelope { id, event, recipient, channel?, locale?, body?, attempts }`.
Inputs produce envelopes, Transforms and policies take and return them (a policy may return
zero or many), and Transports consume them. So any Transform can follow any other.

| Component | Bricks | Kind |
|-----------|--------|------|
| EventsApi | `OnEvent(type)`: other systems post events to it over HTTP | Input |
| Scheduler | `OnSchedule(cron)` | Input |
| NotificationManager | `Delivery`: pending → sent → delivered, or failed → retrying → dead | State machine |
| RoutingEngine | `Expand` (event → recipients), `Prefer`, `QuietHours` | Transform (policy) |
| RenderingEngine | `Render(template, locale)` | Transform |
| DeliveryAccess | `Email`, `Sms`, `Slack`, each `send(envelope) → receipt` | Transport |
| OutboxAccess | `Hold(key, window)`, `Release(due)` | Store |

The Manager's other job is the wiring: one flow per use case, calling the bricks above
through each wall's verbs. Flows are plain code for now; they become data only if V4 turns
out to change weekly. Routing policies are an ordered list per tenant.

Earned: `Expand`, `Prefer`, `QuietHours`, `Render`, `Email`, `OnEvent`, and `Delivery`
each serve two or more features. `Sms`, `Slack`, `OnSchedule`, `Hold`, and `Release` serve
one feature each; each is earned because it is a variant a recorded volatility names (a
channel in V1, the digest flow in V4).

Cut: a `Webhook` transport and an `OptOut` policy were drafted and removed. No current
feature needs them, and no volatility names them. Each would be one new brick in one
component if it arrives.

**Feature assembly**

| Feature | Composition | New bricks |
|---------|-------------|------------|
| F1 | `OnEvent(user.created) → Route → Render(welcome) → Deliver` | 0 |
| F2 | `OnEvent(password.reset) → Route[channel=sms] → Render(reset) → Deliver` | 0 |
| F3 | `OnEvent(activity.*) → Route → Hold(daily)` then `OnSchedule(08:00 local) → Release → Render(digest) → Deliver` | 0 |
| F4 | `OnEvent(alert.*) → Route[team] → Render(alert) → Deliver` | 0 |
| F5, F6 | `Prefer` and `QuietHours` inside `Route` | 0 |
| F7 | `Delivery` state machine | 0 |
| F8 | `Render`'s locale argument | 0 |
| future: WhatsApp (V1) | a `WhatsApp` transport in `DeliveryAccess` | 1 |
| future: escalate if unread in 15 min (V4) | `… → Deliver(push) → Wait(15m, unless read) → Deliver(sms)` | 1 (`Wait`, in the Manager) |
| future: no SMS to EU users at night (V2) | a policy in `RoutingEngine` | 1 |

**Change simulation**

| Volatility happens | Components that change | Result |
|--------------------|------------------------|--------|
| V1: add WhatsApp, or swap the SMS vendor | `DeliveryAccess` | pass |
| V2: new regional rule | `RoutingEngine` | pass |
| V3: new template or language | `RenderingEngine` (data only) | pass |
| V4: escalate-if-unread flow | `NotificationManager` (one new flow, one new `Wait` step) | pass |
| V5: recipients move to a CRM | `RecipientsAccess` | pass |

**Use-case walkthroughs**

```
UC1 notify about an event now
  EventsApi           → NotificationManager.Notify
  NotificationManager → RoutingEngine.Route
  RoutingEngine       → RecipientsAccess.Find
  NotificationManager → RenderingEngine.Render
  NotificationManager → DeliveryAccess.Deliver
  NotificationManager → OutboxAccess.Record

UC2 notify about accumulated events later
  EventsApi           → NotificationManager.Notify        (flow ends in Hold)
  NotificationManager → RoutingEngine.Route
  RoutingEngine       → RecipientsAccess.Find
  NotificationManager → OutboxAccess.Hold
  Scheduler           → NotificationManager.SendDigests
  NotificationManager → OutboxAccess.Release
  NotificationManager → RenderingEngine.Render
  NotificationManager → DeliveryAccess.Deliver

UC3 choose how and when to be reached
  AdminPortal         → NotificationManager.SetPreferences
  NotificationManager → RecipientsAccess.SavePreferences
```

No new component, no call upward or sideways, one Manager per use case. Pass.

---

## Example 2 — Subsystem: promotions in an established shop

**Request:** "Add promotions (percent off, staff discount, 3-for-2) to our Django shop."

**Measure first.**

```
python volatility.py --path shop --depth 1 --since "18 months ago"
```

| component | commits | days since change |
|-----------|---------|-------------------|
| shop/checkout | 140 | 2 |
| shop/cart | 95 | 5 |
| shop/catalog | 60 | 11 |
| shop/payments | 20 | 94 |

Component coupling: `shop/cart ↔ shop/checkout` 62%. Hotspots: `checkout/totals.py`
(58 commits, 900 lines) and `cart/pricing.py` (41 commits). Their commit messages read
"black friday 20% off", "staff discount", "fix rounding on bundle", "NZ GST change".

**Reading the evidence.** Price adjustment rules are the volatility, and they are smeared
across two modules. That is why cart and checkout keep changing together. The checkout
*flow* itself is stable (`checkout/flow.py`: 4 commits in 18 months), so it needs no new wall.

**Volatility register**

| ID | What changes | Evidence | Contained by |
|----|--------------|----------|--------------|
| V1 | Price adjustment rules: promotions, staff and bundle discounts | hotspots + commit messages | `PricingEngine` (new) |
| V2 | Where promotions are defined (admin today, a marketing tool later) | roadmap | `PromotionsAccess` (new) |
| V3 | Tax rules per region | commit messages | out of scope; recorded as the next candidate |

Rejected: *rounding rules* (variable: a per-currency parameter); *checkout step order*
(measured as stable).

**Walls, scoped to the subsystem.** The host's cart and checkout keep acting as Managers:
they own the sequence, and the sequence is stable. New components:

| Component | Type | API |
|-----------|------|----------|
| `PricingEngine` | Engine (V1) | `Quote(basket) → quote` |
| `PromotionsAccess` | ResourceAccess (V2) | `ActivePromotions(at)`, `Define(promotion)` |

**Seam and anti-corruption layer.** The seam is the existing `compute_total(cart)` in
`checkout/totals.py`, which both cart and checkout already call. It becomes one line that
translates the host's `Cart` into the engine's `Basket` (SKU, category, quantity, unit
price, customer group) and asks `PricingEngine` for a quote. That translator is the
anti-corruption layer: Django model changes stop there. If the engine ever needs to read
more from the host, it goes through a ResourceAccess over the host, never through direct
model imports.

```
checkout            → compute_total(cart)        seam: translate Cart → Basket
compute_total       → PricingEngine.Quote
PricingEngine       → PromotionsAccess.ActivePromotions
```

**Bricks inside PricingEngine.** Shared contract:
`Quote { lines[], adjustments[], total }`.

| Brick | Kind | One thing |
|-------|------|-----------|
| `Match(condition)` | Transform (policy) | selects lines by SKU, category, customer group, date window |
| `PercentOff(n)`, `FixedPrice(x)`, `CheapestFree` | Transform | each adds one kind of adjustment to matched lines |
| `BestOf`, `Exclusive` | Transform (policy) | decide which competing promotions survive |
| `Round(currency)` | Transform | applies currency rounding once, at the end |

A promotion is data: `{match, adjustment}`. The engine runs all active promotions,
then the stacking policy (`BestOf` unless a promotion is `Exclusive`), then `Round`.

The first draft had one `Adjust(kind)` brick. Its `kind` flag switched between three
calculations, which is the mode-flag smell, so it became three bricks. `Match(condition)`
stays one brick: its condition is a predicate that the same code evaluates, a parameter
rather than a switch. An `AmountOff` brick, a `Limit` policy (per order or per customer),
and a `Sequential` stacking policy were drafted and cut: no current feature needs them.
`FixedPrice`, `CheapestFree`, and `Exclusive` serve one feature each; each is a kind of
price adjustment that V1 names.

**Feature assembly**

| Feature | Composition | New bricks |
|---------|-------------|------------|
| 20% off a category | `Match(category=x) → PercentOff(20)` | 0 |
| Staff discount | `Match(group=staff) → PercentOff(30)`, marked `Exclusive` | 0 |
| 3-for-2 | `Match(sku in set, qty ≥ 3) → CheapestFree` | 0 |
| Existing bundle price (migrated from host code) | `Match(sku in bundle) → FixedPrice(x)` | 0 |
| future: $10 off orders over $100 (V1) | `Match(order_total ≥ 100) → AmountOff(10)` | 1 (`AmountOff`, inside `PricingEngine`) |

**Migration** (each step ships on its own):

1. Pin today's totals with characterization tests over real baskets.
2. Put `PricingEngine.quote(basket)` in front of the existing calculation, unchanged
   (branch by abstraction).
3. Route both cart and checkout through it. The duplicate calculation goes away.
4. Rebuild the existing discounts as promotion data, one at a time, behind a flag.
   Run old and new side by side and compare quotes before switching.
5. Delete the old code paths.

**Validation.** Change simulation: a new promotion type touches `PricingEngine` only; moving
promotion setup to a marketing tool touches `PromotionsAccess` only. Re-run
`volatility.py` a quarter later: `cart ↔ checkout` coupling should fall below 30%. If it
has not, the wall leaks and the design gets revisited.
