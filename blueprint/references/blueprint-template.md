# {System name}: Agent System Design Document

**Source design:** `{name}.design.md` · **Language:** {TypeScript | Go | Rust} · **Status:** draft

## 1. Header & Boundary Box

**System:** {one line: what it does, for whom}
**Target mode:** {modular monolith | event-driven services | …} in {language}, {runtime}, {storage} *(assumed, if the design did not say)*

### In scope

- {feature, in the user's words}

### Out of scope (non-goals)

- {rejected candidate, future change, or tempting side quest}

### Decisions added by this spec

Each item was open in the design and is decided here. Review these first.

- {decision}: {chosen value}. If wrong: {what changes}.

## 2. System Invariants

1. **{Rule name}.** {One checkable sentence.} Enforced by `{Component.method}` {in the same
   transaction as {write}}. Violation: `{ERROR_CODE}`.
2. …

(4–7 invariants. Cover idempotency, immutability, and the hard rejections that apply.)

## 3. Core Domain Data Contracts

Conventions: {IDs are branded strings · money is integer minor units plus ISO 4217 code ·
timestamps are ISO 8601 UTC strings · optional fields are marked `?`}.

```ts
// Identifiers
export type {Thing}Id = string & { readonly __brand: "{Thing}Id" };

// Enumerations and states
export type {Thing}Status = "{a}" | "{b}" | "{c}";

// Records
export interface {Thing} {
  id: {Thing}Id;
  status: {Thing}Status;
  {optionalField}?: string;
}

// Errors
export type ErrorCode = "{ERROR_A}" | "{ERROR_B}";
export type Result<T> = { ok: true; value: T } | { ok: false; error: ErrorCode; detail?: string };
```

## 4. State Machines

### {Thing}Status

```mermaid
stateDiagram-v2
  [*] --> {a}
  {a} --> {b}: {event} [{guard}]
  {b} --> [*]
```

Stored by `{Component}`. Each transition is a compare-and-set in `{Component.method}`.
Any other transition: `{INVALID_TRANSITION}`. Terminal: {states}.

## 5. Module Boundaries & Interface Signatures

### Module map

```
src/
  contracts/          types from section 3
  {component}/        one folder per component
tests/
  features/           the scenarios from section 6
```

### Orchestration (Managers)

#### {Noun}Manager

- **Purpose:** {one line}
- **Absorbs change:** {the likely change it contains, in plain words}
- **Constraints:** orchestration only; no business rules.
- **May call:** {Engines, ResourceAccess, Utilities}

```ts
export interface {Noun}Manager {
  {verb}(input: {Input}): Promise<Result<{Output}>>; // errors: {CODE_A}, {CODE_B}
}
```

- **Flow of `{verb}`:**
  1. `{Engine.verb}` …
  2. `{Access.verb}` …
- **Failure & retry:** {retryable vs final errors, timeouts, idempotency on retry, races}

### Business rules (Engines)

#### {Activity}Engine

- **Purpose:** …
- **Absorbs change:** …
- **Constraints:** pure and in-memory: no network, storage, clock, or randomness (injected).
- **May call:** {ResourceAccess, Utilities}

```ts
export interface {Activity}Engine { … }
```

- **Failure & retry:** deterministic; returns errors as values; never retried.

### Resource access (ResourceAccess)

#### {Noun}Access

- **Purpose:** …
- **Absorbs change:** {the vendor or storage that may change}
- **Constraints:** the only code that touches {vendor or storage}; exposes business verbs,
  never CRUD or vendor types.
- **May call:** {Resources, Utilities}

```ts
export interface {Noun}Access { … }
```

- **Failure & retry:** {timeouts, which vendor errors are retried, backoff, idempotency key}

## 6. Agent Verification Suite

```gherkin
Feature: {capability}

  Scenario: {one behavior}
    Given {context with concrete values}
    When {one action}
    Then {observable outcome, with the error code where one applies}

  Scenario Outline: {a family of rejections}
    Given {context}
    When {action with <input>}
    Then the request is rejected with <code>

    Examples:
      | input | code |
      | {x}   | {ERROR_A} |
```
