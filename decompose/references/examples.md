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
Clients         EventsApi        AdminPortal        Scheduler
                    \                |                /
Managers                   NotificationManager
                         /          |            \
Engines        RoutingEngine   RenderingEngine    |
                         \          |            /
ResourceAccess  RecipientsAccess  DeliveryAccess  NotificationLogAccess
                    |                |                |
Resources          DB        email / SMS / Slack      DB
Utilities: pub/sub · logging · secrets
```

`Scheduler` is a client: time is just another caller. `NotificationManager` owns the flows;
it is the only component that knows the order of steps.

**Bricks.** Shared contract: `Envelope { id, event, recipient, channel?, locale?, body?, attempts }`.
Every brick takes and returns envelopes (a policy may return zero or many), so any brick can
follow any other.

| Component | Bricks | Kind |
|-----------|--------|------|
| NotificationManager | `OnEvent(type)`, `OnSchedule(cron)` | Input |
| | `Collect(window)`, `Flush` | Transform (state kept in `NotificationLogAccess`) |
| | `Delivery`: pending → sent → delivered, or failed → retrying → dead | State machine |
| RoutingEngine | `Expand` (event → recipients), `Prefer`, `QuietHours`, `OptOut` | Transform (policy) |
| RenderingEngine | `Render(template, locale)` | Transform |
| DeliveryAccess | `Email`, `Sms`, `Slack`, `Webhook`, each `send(envelope) → receipt` | Transport |

Flows are data owned by the Manager. Routing policies are an ordered list per tenant.

**Feature assembly**

| Feature | Composition | New bricks |
|---------|-------------|------------|
| F1 | `OnEvent(user.created) → Route → Render(welcome) → Send` | 0 |
| F2 | `OnEvent(password.reset) → Route[channel=sms] → Render(reset) → Send` | 0 |
| F3 | `OnEvent(activity.*) → Route → Collect(daily)` then `OnSchedule(08:00 local) → Flush → Render(digest) → Send` | 0 |
| F4 | `OnEvent(alert.*) → Route[team] → Render(alert) → Send` | 0 |
| F5, F6 | `Prefer` and `QuietHours` inside `Route` | 0 |
| F7 | `Delivery` state machine | 0 |
| F8 | `Render`'s locale argument | 0 |
| future: WhatsApp (V1) | a `WhatsApp` transport in `DeliveryAccess` | 1 |
| future: escalate if unread in 15 min (V4) | `… → Send(push) → Wait(15m, unless read) → Send(sms)` | 1 (`Wait`, in the Manager) |
| future: no SMS to EU users at night (V2) | a policy in `RoutingEngine` | 1 |

**Change simulation**

| Volatility happens | Components that change | Result |
|--------------------|------------------------|--------|
| V1: add WhatsApp, or swap the SMS vendor | `DeliveryAccess` | pass |
| V2: new regional rule | `RoutingEngine` | pass |
| V3: new template or language | `RenderingEngine` (data only) | pass |
| V4: escalate-if-unread flow | `NotificationManager` | pass |
| V5: recipients move to a CRM | `RecipientsAccess` | pass |

**Use-case walkthrough (F1)**: `EventsApi → NotificationManager.Notify → RoutingEngine.Route →
RecipientsAccess.Find → RenderingEngine.Render → DeliveryAccess.Deliver → NotificationLogAccess.Record`.
No new component needed, no sideways or upward call. Pass.

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

**Walls, scoped to the subsystem.** The host's checkout keeps acting as the Manager.
`PricingEngine` and `PromotionsAccess` are new. A small anti-corruption layer, `QuoteAdapter`,
turns the host's `Cart` model into the engine's `Basket`, so Django model changes stop there.

**Bricks inside PricingEngine.** Shared contract:
`Quote { lines[], adjustments[], total }`.

| Brick | Kind | One thing |
|-------|------|-----------|
| `Match(condition)` | Transform (policy) | selects lines by SKU, category, customer group, date window |
| `Adjust(percent | amount | fixed_price)` | Transform | adds an adjustment to matched lines |
| `Limit(per_order | per_customer)` | Transform (policy) | caps how often an adjustment applies |
| `Stack(best_of | sequential | exclusive)` | Transform (policy) | combines competing promotions |
| `Round(currency)` | Transform | applies currency rounding once, at the end |

A promotion is data: `{match, adjust, limit}`. The engine runs all active promotions,
then `Stack`, then `Round`.

**Feature assembly**

| Feature | Composition | New bricks |
|---------|-------------|------------|
| 20% off a category | `Match(category=x) → Adjust(percent 20)` | 0 |
| Staff discount | `Match(group=staff) → Adjust(percent 30)`, `Stack(exclusive)` | 0 |
| 3-for-2 | `Match(sku in set, qty ≥ 3) → Adjust(cheapest_free)` | 1 (`Adjust` variant) |

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
