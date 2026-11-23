# `/decompose` — Software Design by Volatility and Primitives

`/decompose` designs a new system (inception), or a new subsystem in an existing codebase.
`/decompose` makes the design in two passes, and then proves the result:

1. **Walls** — volatility-based decomposition. `/decompose` finds the items that are
   likely to change. Then `/decompose` puts each item behind one component:
   - Managers, for workflows that change.
   - Engines, for rules that change.
   - ResourceAccess, for storage and third parties that change.

   Thus, a change occurs in one place.
2. **Bricks** — orthogonal primitives. In each wall, `/decompose` builds a small set of
   independent parts (inputs, transforms, transports, stores, state machines). The parts
   share one contract. `/decompose` assembles each feature as a combination of the parts.
3. **Proof** — `/decompose` walks the core use cases through the walls. Then
   `/decompose` simulates each likely change (target: one component touched). Last,
   `/decompose` assembles current and future features from existing bricks (target: a
   maximum of one new brick).

`/decompose` draws its result as C4 diagrams:

- A system context diagram.
- A component diagram with one band for each layer. Each arrow in this diagram is an
  allowed call.

In an existing codebase, `/decompose` measures volatility from the git history, and does
not guess. `decompose/scripts/volatility.py` reports component churn, change coupling, and
hotspots. The script is standard-library Python, and works on Windows.

The output of `/decompose` is a `<name>.design.md` file. The file has the volatility
register, walls, bricks, feature assembly, and validation results. For a subsystem, the
file also has the seam and the migration steps.

**Example**

```
/decompose a notifications service: welcome emails, password-reset SMS, daily
digests, Slack alerts, channel preferences, quiet hours, retries, localization
```

**Output (excerpt)**

```
DECOMPOSE: notifications · inception
══════════════════════════════════════════════════
VOLATILITIES  5 contained · 3 rejected
WALLS         9 components: 3 Clients · 1 Manager · 2 Engines · 3 ResourceAccess · plus 3 Utilities
BRICKS        12 across 7 components · contracts: Envelope
──────────────────────────────────────────────────
USE CASES     3/3 walk through cleanly
CHANGE SIM    5/5 volatilities touch one component
FEATURES      8 current assembled · 3 future with ≤1 new brick
VERDICT       ready
```

Give the `<name>.design.md` file to one of these skills for the next step:

- `/argue`, to find contradictions in the design.
- `/blueprint`, to make the design agent-ready.
- `/quiz-plan`, to make a change plan from the design.
