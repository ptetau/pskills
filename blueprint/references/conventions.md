# Conventions: the default decisions

When the design leaves a detail open, the blueprint decides the detail. This file gives the
defaults, and the source of each default. Use these defaults, unless the host codebase or
the user says otherwise. List each default that you use under **Decisions added by this
spec**. The sources are in `sources.md`.

## Money

- **An integer in the minor unit of the currency, plus an ISO 4217 code.** Stripe says:
  "All API requests expect amount values in the currency's minor unit". Thus, `1000` is
  10 USD, and `10` is 10 JPY.
- **Take the exponent from ISO 4217**, not from habit. USD and EUR have 2, JPY and KRW
  have 0, and KWD and BHD have 3. Vendors can be different. For example, Stripe wants ISK
  as if ISK had two decimals. Write each such exception at the ResourceAccess that
  connects to that vendor.
- **Do not use a float.** Fowler's Money pattern gives the reasons: rounding loses
  pennies, and a plain number lets you add dollars to yen.

```ts
export type CurrencyCode = string & { readonly __brand: "CurrencyCode" }; // ISO 4217
export interface Money { units: number; currency: CurrencyCode }          // integer minor units
```

## Time

- **ISO 8601 strings in UTC** (`2026-03-02T22:30:00Z`) at each boundary, as one branded
  type. This default comes from the skill, not from a source. The purpose is to state one
  convention, and to use it everywhere.
- Local time appears only where a rule is local (quiet hours, business days), with an IANA
  time zone next to the local time.
- Inject the clock. Engines do not read the clock.
- Inject randomness in the same way. Pass a random number or a seeded generator as a
  parameter. Then Engines stay deterministic, and tests can give the randomness a fixed
  value.

## Identifiers and parsing

- **Distinct types for distinct IDs**: branded strings in TypeScript, and newtypes in Go
  and Rust. Then code cannot pass one kind of ID where the code expects a different kind.
- **"Parse, don't validate"** (Alexis King). Turn less-structured input into
  more-structured types one time, at the boundary. Make internal methods accept only the
  parsed types. "Push the burden of proof upward as far as possible, but no further."

## States

- **Make illegal states unrepresentable** (Yaron Minsky). A record with many optional
  fields becomes a union. Each variant of the union carries only its own data.
- Each `...Status` or `...State` type has a state machine in section 4.

## Invariants, fault, and HTTP status

Design by contract (Meyer, Eiffel) sorts each failure by fault:

| Broken | Meaning | Whose bug | HTTP |
|--------|---------|-----------|------|
| Precondition | what the method requires of its caller | the caller's | 4xx: "the client seems to have erred" (RFC 9110) |
| Postcondition | what the method guarantees on return | the supplier's | 5xx |
| Invariant | what must hold for every valid instance, before and after every call | the supplier's | 5xx |

Each invariant in section 2 names its enforcement point and its error code. The error
catalogue in section 3 gives the fault and the status of each code.

## Errors

- **Codes are `UPPER_SNAKE_CASE`**, in one `ErrorCode` union. Errors cross module
  boundaries as returned values.
- **Over HTTP, use RFC 9457 problem details** (`application/problem+json`). The `type` URI
  is the primary identifier of the problem type. Put the code in an extension member
  (`code`). Clients must not parse `detail`. A new problem type documents its type URI,
  title, and HTTP status. The error catalogue records these items.

## Idempotency

For each call with side effects that a client or a retry can repeat, state these items:

| Question | Default | Source |
|----------|---------|--------|
| What is the key? | Client-supplied, or derived from the identity of the request (`eventId:recipientId:channel`) | Stripe, and the IETF draft |
| How long is the key kept? | At least 24 hours. Longer if replays can arrive later | Stripe prunes keys after 24 h. The draft says that the resource should define the time |
| What does a replay return? | The saved result of the first request, success or failure | Stripe saves the first status and body, "including 500 errors" |
| Same key, different payload? | Refuse, with a named code | Stripe returns an error. The draft uses 422. Brandur uses 409. Pick one and state it |
| Same key while the first request still runs? | Refuse with 409 | The IETF draft, and Stripe |

Keep local state changes in atomic phases between foreign calls. Give the phases named
recovery points, where a retry can resume (Brandur Leach, "Implementing Stripe-like
Idempotency Keys in Postgres").

Note a consequence of the Stripe method. A replay returns the saved result. Thus, a retry
of a failed request with the *same* key does not recover the request. A retry after a
server error needs a new key, or a design that does not save failures.

## Timeouts and retries

From Marc Brooker (AWS) and RFC 9110:

- **Each remote call has a timeout.** Set the timeout from the downstream latency at the
  false-timeout rate that you accept (for example, the p99.9 of the latency). Before you
  measure the latency, state a number and mark it assumed.
- **Retry only what is safe to repeat.** "APIs with side effects aren't safe to retry
  unless they provide idempotency." RFC 9110 says: do not automatically retry a
  non-idempotent request.
- **Retry on** timeouts, 408, 429, 503, and other 5xx. **Do not retry** other 4xx.
  **Obey `Retry-After`** on 429 and 503.
- **Retry at one layer only.** Retries multiply. If five layers each try three times, the
  load becomes 243 times the original load.
- **Use capped exponential backoff with full jitter:**
  `sleep = random_between(0, min(cap, base * 2 ** attempt))`. Also put jitter on each
  timer and each periodic job.
- **Cap attempts, and budget retries** (a token bucket). Then retries do not flood a
  failing dependency.

State all of these items for each component, under **Failure & retry**.

## State machine diagrams

Mermaid `stateDiagram-v2`:

```
stateDiagram-v2
  [*] --> pending: claim [new key]
  pending --> sending: startAttempt
  sending --> delivered: confirmDelivery
  delivered --> [*]
```

- `[*]` is the start and the end. Label each transition `verb [guard] / outcome`.
- Name each transition after the API verb that does the transition. Then section 4 and
  section 5 use the same words.
- **Any transition not drawn is illegal**, and raises the illegal-transition code.
- For many states, use composite states (`state Name { … }`) and concurrent regions.
  Harel's statecharts add hierarchy and concurrency to flat state diagrams. Mermaid cannot
  draw a transition between inner states of different composite states.

## Gherkin

From the Cucumber reference and the guidance of Cucumber:

- **Keywords:** `Feature`, `Rule`, `Background`, `Scenario` (or `Example`),
  `Scenario Outline` with `Examples`, and the steps `Given`, `When`, `Then`, `And`, `But`.
- **Given** puts the system in a known state (the preconditions). **When** is one event or
  action. **Then** asserts an observable outcome, "not a behaviour deeply buried inside the
  system (like a record in a database)."
- **3–5 steps in each scenario.** "Having too many steps will cause the example to lose
  its expressive power."
- **One behaviour in each scenario.** A test of more than one thing "can blur the essence
  of your scenario."
- **Declarative, not imperative**: "what, not how." If a step changes when the
  implementation changes, write the step again.
- **Background** only for shared context. If the Background has more than four lines, move
  detail into higher-level steps.
- **Scenario Outline** for the same behaviour with different values.
- **Key examples** (Gojko Adzic): a few simple, concrete scenarios, not all the
  combinations. Where a rule has a threshold, use boundary values.

## Open questions

The rule of GitHub spec-kit: mark a maximum of three questions `[NEEDS CLARIFICATION: the
specific question]`. Select the questions by impact: scope, then security and privacy,
then user experience, then technical detail. Make an informed decision for each other
detail. Record each such decision as an assumption. A blueprint with open questions is a
draft.

## Definition of done

- **Give the agent a check that it can run.** The Claude Code best practices say that the
  most useful specs "name the files and interfaces involved, state what is out of scope,
  and end with an end-to-end verification step."
- **Done means**: the scenarios in section 6 fail before the work and pass after the work,
  and the existing tests still pass. SWE-bench judges a fix in the same way, with its
  FAIL_TO_PASS and PASS_TO_PASS tests.
- Section 6 ends with the exact command that runs the scenarios.
