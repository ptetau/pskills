# Conventions: the default decisions

When the design leaves a detail open, the blueprint decides it. These are the defaults,
with where each comes from. Use them unless the host codebase or the user says otherwise,
and list every one you apply under **Decisions added by this spec**. Sources are in
`sources.md`.

## Money

- **An integer in the currency's minor unit, plus an ISO 4217 code.** Stripe: "All API
  requests expect amount values in the currency's minor unit": `1000` is 10 USD, `10` is
  10 JPY.
- **Take the exponent from ISO 4217**, not from habit: USD and EUR have 2, JPY and KRW 0,
  KWD and BHD 3. Vendors can differ: Stripe wants ISK as if it had two decimals. Note any
  such exception at the ResourceAccess that talks to that vendor.
- **Never a float.** Fowler's Money pattern: rounding loses pennies, and a plain number lets
  you add dollars to yen.

```ts
export type CurrencyCode = string & { readonly __brand: "CurrencyCode" }; // ISO 4217
export interface Money { units: number; currency: CurrencyCode }          // integer minor units
```

## Time

- **ISO 8601 strings in UTC** (`2026-03-02T22:30:00Z`) at every boundary, as one branded
  type. This is the skill's default, not a sourced rule; the point is to state one
  convention and use it everywhere.
- Local time appears only where a rule is local (quiet hours, business days), with an IANA
  time zone next to it.
- The clock is injected. Engines never read it.

## Identifiers and parsing

- **Distinct types for distinct IDs**: branded strings in TypeScript, newtypes in Go and
  Rust, so one kind of ID can't be passed where another is expected.
- **Parse, don't validate** (Alexis King): turn less-structured input into more-structured
  types once, at the boundary, and have internal methods accept only the parsed types.
  "Push the burden of proof upward as far as possible, but no further."

## States

- **Make illegal states unrepresentable** (Yaron Minsky). A record full of optional fields
  becomes a union whose variants each carry only their own data.
- Every `...Status` or `...State` type has a state machine in section 4.

## Invariants, fault, and HTTP status

Design by contract (Meyer, Eiffel) sorts every failure by fault:

| Broken | Meaning | Whose bug | HTTP |
|--------|---------|-----------|------|
| Precondition | what the method requires of its caller | the caller's | 4xx: "the client seems to have erred" (RFC 9110) |
| Postcondition | what the method guarantees on return | the supplier's | 5xx |
| Invariant | what must hold for every valid instance, before and after every call | the supplier's | 5xx |

Each invariant in section 2 names its enforcement point and its error code; the error
catalog in section 3 gives each code its fault and status.

## Errors

- **Codes are `UPPER_SNAKE_CASE`**, one `ErrorCode` union, errors returned as values across
  module boundaries.
- **Over HTTP, use RFC 9457 problem details** (`application/problem+json`). The `type` URI
  is the problem type's primary identifier; put the code in an extension member (`code`).
  Clients must never parse `detail`. A new problem type documents its type URI, title,
  and HTTP status, which is what the error catalog records.

## Idempotency

For every call with side effects that a client or a retry might repeat, state:

| Question | Default | Source |
|----------|---------|--------|
| What is the key? | Client-supplied, or derived from the request's identity (`eventId:recipientId:channel`) | Stripe; IETF draft |
| How long is it kept? | At least 24 hours; longer if replays can arrive later | Stripe prunes keys after 24 h; the draft says the resource should define it |
| What does a replay return? | The first request's saved result, success or failure | Stripe saves the first status and body, "including 500 errors" |
| Same key, different payload? | Refuse, with a named code | Stripe errors; the draft uses 422; Brandur uses 409. Pick one and state it |
| Same key while the first is still running? | Refuse with 409 | IETF draft; Stripe |

Keep local state changes in atomic phases between foreign calls, with named recovery
points a retry can resume from (Brandur Leach, "Implementing Stripe-like Idempotency Keys
in Postgres").

Note Stripe's consequence: because a replay returns the saved result, retrying a failed
request with the *same* key won't recover it. A retry after a server error needs a new key,
or a design where failures aren't saved.

## Timeouts and retries

From Marc Brooker (AWS) and RFC 9110:

- **Every remote call has a timeout**, set from the downstream latency at the false-timeout
  rate you accept (for example its p99.9). Before that is measured, state a number and
  mark it assumed.
- **Retry only what is safe to repeat.** "APIs with side effects aren't safe to retry
  unless they provide idempotency." RFC 9110: don't automatically retry a non-idempotent
  request.
- **Retry on** timeouts, 408, 429, 503, and other 5xx. **Don't retry** other 4xx.
  **Honor `Retry-After`** on 429 and 503.
- **Retry at one layer only.** Retries multiply: five layers each trying three times make
  243 times the load.
- **Capped exponential backoff with full jitter:**
  `sleep = random_between(0, min(cap, base * 2 ** attempt))`. Put jitter on every timer
  and periodic job too.
- **Cap attempts, and budget retries** (a token bucket) so a failing dependency isn't
  flooded.

State all of this per component under **Failure & retry**.

## State machine diagrams

Mermaid `stateDiagram-v2`:

```
stateDiagram-v2
  [*] --> pending: claim [new key]
  pending --> sending: startAttempt
  sending --> delivered: confirmDelivery
  delivered --> [*]
```

- `[*]` is the start and the end; label transitions `verb [guard] / outcome`.
- Name each transition after the API verb that performs it, so section 4 and section 5
  use the same words.
- **Any transition not drawn is illegal**, and raises the illegal-transition code.
- For many states, use composite states (`state Name { … }`) and concurrent regions: Harel's
  statecharts add hierarchy and concurrency to flat state diagrams. Mermaid can't draw a
  transition between inner states of different composite states.

## Gherkin

From the Cucumber reference and Cucumber's own guidance:

- **Keywords:** `Feature`, `Rule`, `Background`, `Scenario` (or `Example`),
  `Scenario Outline` with `Examples`, and the steps `Given`, `When`, `Then`, `And`, `But`.
- **Given** puts the system in a known state (the preconditions). **When** is one event or
  action. **Then** asserts an observable outcome, "not a behaviour deeply buried inside the
  system (like a record in a database)."
- **3–5 steps per scenario.** "Having too many steps will cause the example to lose its
  expressive power."
- **One behavior per scenario.** Testing several things "can blur the essence of your
  scenario."
- **Declarative, not imperative**: "what, not how." If a step would change when the
  implementation changes, rewrite it.
- **Background** only for shared context; if it runs past four lines, move detail into
  higher-level steps.
- **Scenario Outline** for the same behavior with different values.
- **Key examples** (Gojko Adzic): a few simple, concrete scenarios, with boundary values
  where a rule has a threshold, rather than exhaustive combinations.

## Open questions

GitHub spec-kit's rule: mark at most three questions `[NEEDS CLARIFICATION: the specific
question]`, chosen by impact (scope, then security and privacy, then user experience, then
technical detail). Make informed choices for everything else and record them as
assumptions. A blueprint with open questions is a draft.

## Definition of done

- **Give the agent a check it can run.** Claude Code's best practices: the most useful specs
  "name the files and interfaces involved, state what is out of scope, and end with an
  end-to-end verification step."
- **Done means**: the scenarios in section 6 fail before the work and pass after it, and
  the existing tests still pass. SWE-bench judges a fix the same way, with its
  FAIL_TO_PASS and PASS_TO_PASS tests.
- Section 6 ends with the exact command that runs the scenarios.
