# Design: <system or subsystem name>

**Mode:** inception | subsystem of `<host system>` · **Status:** draft | reviewed
**Date:** <YYYY-MM-DD> · **Scope:** <one line: what is inside the walls, what is not>

> Walls come from volatility (where change is contained). Bricks come from orthogonal
> primitives (how features are assembled). Every component below traces to a volatility
> (V-id); every brick traces to a volatility or a current feature (F-id). Anything that
> traces to neither was cut.

## 1. Frame

- **Problem:** <what this system does, in two sentences>
- **Users:** <who uses it and who calls it: people, systems, schedules>
- **Nature of the business:** <what will not change while this system exists. These are
  deliberately NOT encapsulated.>
- **Constraints:** <deadlines, team, platform, compliance, host-system conventions>
- **Host system (subsystem mode):** <language, framework, where it attaches, owners>
- **Assumptions** (made instead of asking; each one is a question to confirm):
  - <assumption> — <what changes in the design if it is wrong>

## 2. Features and use cases

| ID | Feature (as the user would say it) | Core use case? |
|----|--------------------------------------|----------------|
| F1 | <...> | yes |
| F2 | <...> | no — variation of F1 |

Core use cases (the few that express the essence of the system; everything else is a
variation of these): <UC1 — ...>, <UC2 — ...>

## 3. Volatility register

| ID | What changes | Axis | Evidence | Likelihood | Contained by |
|----|--------------|------|----------|------------|--------------|
| V1 | <e.g. which channels exist and which vendor delivers each> | over time / across customers | <interview, roadmap, git hotspot, ticket> | high / med / low | <component> |

**Rejected candidates** (considered and deliberately not walled off):

| Candidate | Why not a wall |
|-----------|----------------|
| <...> | variable, not volatile: handled by data/parameters inside one component |
| <...> | nature of the business: if this changes, it is a different system |
| <...> | speculative: no evidence it will change |

## 4. Walls (architecture)

```mermaid
flowchart TB
  subgraph Clients
    C1[<Client>]
  end
  subgraph Business logic
    M1[<Noun>Manager]
    E1[<Noun>Engine]
  end
  subgraph Resource access
    RA1[<Noun>Access]
  end
  subgraph Resources
    R1[(<store or external system>)]
  end
  U[[Utilities: <logging, security, pub/sub>]]
  C1 --> M1
  M1 --> E1
  M1 --> RA1
  E1 --> RA1
  RA1 --> R1
```

| Component | Type | Encapsulates | API (business verbs) | May call |
|-----------|------|--------------|---------------------------|----------|
| <Client> | Client | V1 (who calls, and how) | entry points: `<Verb>`: `POST /route`, a screen, a command | one Manager per use case |
| <Noun>Manager | Manager | V2 (workflow order) | `<Verb>(...)` | Engines, Access, Utilities; other Managers only via queue |

For a Client, the API column lists its entry points (routes, screens, commands), so the
blueprint types them instead of inventing them.

## 5. Bricks (implementation inside the walls)

Shared contracts (one per wall, or one shared by walls on the same flow):

- `<Name>` used by <components>: <fields, which bricks may set each, invariants>

Composition medium: code | pipeline definition | state-machine table | config — <why>

### <Component name>

| Brick | Kind | Does exactly one thing | In → Out | Serves |
|-------|------|------------------------|----------|--------|
| <Render> | Transform | <fills a template for a locale> | Envelope → Envelope | F1, F3, V3 |

State machines (if any). Draw only the legal transitions: anything not drawn is refused.
Mark terminal states, if there are any.

```
<state> --event [guard] / effect--> <state>
```

## 6. Feature assembly

Every feature, now and plausible future, written as a composition of existing bricks.

| Feature | Composition | New bricks needed |
|---------|-------------|-------------------|
| F1 | `<Input> → <Transform> → <Transport>` | 0 |
| future: <V1 happens> | `<same, one brick swapped>` | 1 (inside <component>) |

## 7. Validation

**Use-case walkthroughs** (each core use case as a call chain, one call per line):

```
UC1 <name>
  <Client>        → <Noun>Manager.<Verb>
  <Noun>Manager   → <Noun>Engine.<Verb>
  <Noun>Engine    → <Noun>Access.<Verb>
  <Noun>Manager   → <Noun>Access.<Verb>
```

Result: <pass, or which rule broke and how the walls changed>

**Change simulation** (each volatility happening; target is one existing component touched):

| Volatility | Components that must change | Result |
|------------|-----------------------------|--------|
| V1 | <Component> | pass |

A new ResourceAccess for a genuinely new resource, or a Client change for a new human
step, is not a leak; note it in the Result column.

**Orthogonality check:** <for each brick whose requirement could change a lot, what else
would change; anything other than "nothing" and how it was fixed>

**Rule audit:** <call rules, naming, sizing, smells found and how they were fixed>

**Trace audit:** <any component without a V-id, any brick without an F-id or V-id, and
what happened to it>

**Measured coupling (subsystem mode):** <component pairs from volatility.py above 30%
that a wall now separates, and why the design removes that coupling>

**Cut list:** <walls or bricks considered and removed because nothing traced to them>

**Revisions during validation:** <each failed check, the change made, and the re-run
result, e.g. "V3 touched RenderingEngine and PracticeApp; moved template choice into
RenderingEngine; re-run passes">

## 8. Seams and migration (subsystem mode)

In inception mode, write "Not applicable: inception" and keep the number.

- **Attach point:** <the seam in the host where the subsystem plugs in>
- **Translation at the seam:** <anti-corruption layer where the subsystem calls the host;
  open-host service where the host calls in. Host types stop here>
- **Steps** (each one shippable on its own; old path deleted last):
  1. <put an abstraction in front of the existing behavior (branch by abstraction)>
  2. <route callers through it>
  3. <build the new implementation behind it>
  4. <switch over, observe, delete the old path>

## 9. Risks and open questions

- <the riskiest assumption in this design, and the cheapest way to test it first>
- <open question — who decides>

## 10. Next steps

- `/argue` this document to check it for contradictions.
- `/blueprint` to turn it into an agent-ready spec: typed contracts, state machines,
  signatures, and Gherkin scenarios.
- `/quiz-plan` to turn the walls and migration steps into an executable change plan.
