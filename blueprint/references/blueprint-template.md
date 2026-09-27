# {System name}: Agent System Design Document

**Source design:** `{name}.design.md` · **Language:** {TypeScript | Go | Rust} · **Status:** draft

## 1. Header & Boundary Box: what gets built, and what doesn't

**System:** {one line: what it does, for whom}
**Target mode:** {modular monolith | event-driven services | …} in {language}, {runtime}, {storage} *(assumed, if the design did not say)*

A C4 container diagram: what runs, and which components each container holds (see
`c4.md`). With a single container, say "Everything runs in one container: {name}" instead.

```mermaid
C4Container
  title Container diagram for {System}
  Person(user, "{Who uses it}", "{what they do}")
  System_Boundary(sys, "{System}") {
    Container(app, "{App name}", "{runtime, language}", "Holds {Component}, {Component}, …")
    ContainerDb(db, "{Database}", "{technology}", "{what it stores}")
  }
  System_Ext(ext, "{Another system}", "{what it does}")
  Rel(user, app, "{Does what with}", "{protocol}")
  Rel(app, db, "Reads and writes", "{protocol}")
  Rel(app, ext, "{Does what through}", "{protocol}")
```

Key: blue boxes run inside our system; grey boxes are other systems; the figure is a
person. Each container lists the components it holds.

### In scope

- {feature, in the user's words}

### Out of scope (non-goals)

- {rejected candidate, future change, or tempting side quest}

### Decisions carried from the design

- {the design's own assumption, as stated there}

### Decisions added by this spec

Each item was open in the design and is decided here. Review these first.

- {decision}: {chosen value}. If wrong: {what changes}.

Open questions, at most three, also appear inline where they apply:
`[NEEDS CLARIFICATION: {the specific question}]`. Answer them before an agent builds.

### Words used here

One line per technical word this blueprint uses, explained in plain words (see
`plain-language.md`). For example:

- **Invariant**: a rule that must always be true, no matter what happens.
- **Idempotent**: safe to do twice; the second time changes nothing.

## 2. System Invariants: rules that must always hold

1. **{Rule name}.** {One checkable sentence.} Enforced by `{Component.method}` {in the same
   transaction as {write}}. Violation: `{ERROR_CODE}`.
2. …

(4–7 invariants for most systems; fewer for a small domain. Never pad. Cover
idempotency, immutability, and the hard rejections where they apply.)

## 3. Core Domain Data Contracts: the exact shape of the data

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

### Error catalog

One row per code in `ErrorCode`. Fault follows design by contract: a broken precondition is
the caller's fault (4xx); a broken postcondition or invariant is the supplier's (5xx). Over
HTTP, errors are RFC 9457 problem details (`application/problem+json`) with the code in a
`code` member.

| Code | Meaning | Fault | HTTP | Retry helps? |
|------|---------|-------|------|--------------|
| `{ERROR_A}` | {what went wrong} | caller | {409} | no |
| `{ERROR_B}` | {what went wrong} | supplier | {503} | yes, with backoff |

(No HTTP boundary? Drop the HTTP column.)

## 4. State Machines: how things move from one state to the next

### {Thing}Status

```mermaid
stateDiagram-v2
  [*] --> StateA
  StateA --> StateB: eventName [guard]
  StateB --> [*]
```

Stored by `{Component}`. Each transition is performed by the verb on its arrow, as a
compare-and-set. Anything not drawn is refused: `{INVALID_TRANSITION}`. Terminal:
{states, or "none"}.

## 5. Module Boundaries & Interface Signatures: the parts and how to call them

### Module map

```
src/
  contracts/          types from section 3
  {component}/        one folder per component
tests/
  features/           the scenarios from section 6
```

### Component diagram

The design's component diagram, redrawn inside its container, with technology added
(`[Component: Manager, TypeScript]`). Required when there are more than three parts.

```mermaid
---
title: "Component diagram for {App name}: who calls whom"
---
flowchart TB
  subgraph app["{App name} [container]"]
    subgraph managers["Managers: the steps, in order"]
      m1["<b>{Noun}Manager</b><br/>[Component: Manager, {language}]<br/>{the steps it runs}"]
    end
    subgraph engines["Engines: the rules"]
      e1["<b>{Activity}Engine</b><br/>[Component: Engine, {language}]<br/>{the rule it applies}"]
    end
  end
  m1 -->|Verb| e1
```

Key: light blue, a component; arrows are calls, labelled with the verbs used.

### Orchestration (Managers)

#### {Noun}Manager

- **Purpose:** {one line}
- **Encapsulates:** {the likely change it contains, in plain words}
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
- **Encapsulates:** …
- **Constraints:** pure and in-memory: no network, storage, clock, or randomness. The
  Manager passes in what it needs.
- **May call:** {Utilities; a read-only ResourceAccess only if the design records one}

```ts
export interface {Activity}Engine { … }
```

- **Failure & retry:** deterministic; returns errors as values; never retried.

### Resource access (ResourceAccess)

#### {Noun}Access

- **Purpose:** …
- **Encapsulates:** {the vendor or storage that may change}
- **Constraints:** the only code that touches {vendor or storage}; exposes business verbs,
  never CRUD or vendor types.
- **May call:** {Resources, Utilities}

```ts
export interface {Noun}Access { … }
```

- **Failure & retry:** {timeouts, which vendor errors are retried, backoff, idempotency key}

## 6. Agent Verification Suite: tests that say when it's done

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

**Verify:** `{npm test -- tests/features}`

**Done when:** every scenario above passes (they fail before the work starts), and every
existing test still passes.
