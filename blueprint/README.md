# `/blueprint` — Agent-Ready Spec from a Design

`/blueprint` is the companion to `/decompose`. A design document tells *why* the system
has its shape. But a coding agent must know *what exactly* to build. `/blueprint` rewrites
a design (a `name.design.md`, or any architecture doc) into an **Agent System Design
Document**. A person can skim this document, and an agent can implement it with no
guesses. The document has six sections:

1. **Header and boundary box**: purpose, target mode, in scope, out of scope.
2. **System invariants**: 4–7 enforceable rules. Each rule has the place where the system
   enforces the rule, and its error code.
3. **Core data contracts**: exact types (TypeScript, Go, or Rust).
4. **State machines**: each lifecycle, with guards, terminal states, and illegal moves.
5. **Module boundaries and signatures**: typed methods, constraints, and the failure and
   retry behaviour of each component.
6. **Verification suite**: 3–5 Gherkin scenarios that exercise each invariant.

Some details can stay open in a design, for example a retry count, a key format, or a
storage engine. `/blueprint` decides each open detail one time. Then `/blueprint` marks
the detail *(assumed)*, and lists the detail for review. Thus, an agent gets each detail,
and does not guess.

`blueprint/scripts/check_blueprint.py` checks the result for these conditions:

- The structure is correct.
- Each invariant has an enforcement point and an error code.
- A scenario exercises each error code.
- Each state type has a state machine.
- No design ID stays in the result (for example, `V1`).

With `--compile`, `check_blueprint.py` also type-checks the TypeScript.

**Example**

```
/blueprint notifications.design.md
```

**Output (excerpt)**

```
BLUEPRINT: notifications · TypeScript · modular monolith
══════════════════════════════════════════════════
SCOPE        8 in · 4 out
INVARIANTS   6 · codes: IDEMPOTENCY_CONFLICT, QUIET_HOURS_DEFERRED, …
CONTRACTS    19 types · 2 state machines
MODULES      9 components: 3 Clients · 1 Manager · 2 Engines · 3 ResourceAccess
SCENARIOS    5 · every invariant exercised
DECISIONS    11 added for review + 0 carried from the design · 0 open questions
CHECK        PASS
```

`/blueprint` draws a C4 container diagram (what runs, and which parts each container
holds). `/blueprint` also draws a C4 component diagram (who calls whom).
`check_blueprint.py` makes sure that the two diagrams agree with the text. `--render`
renders each diagram with Mermaid.

Give the output of `/blueprint` to `/quiz-plan` to get a change plan. Then run
`/quiz-plan-execute`. `/quiz-plan-execute` uses the Gherkin scenarios as its failing
tests.

**`/blueprint` and `/decompose` obey the writing guidelines.** The two skills write for a
bright 10-year-old, at a reading grade of 7 or lower. The sentences are short, and the
words are common. Each technical word is in a "Words used here" list. Names, types, and
error codes stay the same.

`check_writing.py` is the linter for the guidelines. `/blueprint` and `/decompose` each
have a copy of the linter. The linter measures the sentence length and the reading grade.
The linter also lists each technical word that has no entry in the "Words used here"
list.
