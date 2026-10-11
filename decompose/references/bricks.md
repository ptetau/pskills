# Bricks: orthogonal primitives

How to design the inside of a wall. The walls (see `walls.md`) decide where change stops.
Bricks decide how you assemble features. `sources.md` gives the source for every idea.

## The idea in one paragraph

Don't build features. Build a small number of independent parts that share one way to
connect. Write each feature as a composition of parts. A new feature should then be
mostly a new composition. ALGOL 68's design (few primitive concepts, applied
orthogonally, for maximum expressive power) and Unix tools (small programs, one
text-stream interface, pipes) follow this idea. So does AWS, in how it built its services
("primitives not frameworks").

SICP names the three things any such system needs:

1. **Primitives**: the simplest parts.
2. **A means of combination**: a way to build bigger things from smaller ones.
3. **A means of abstraction**: a way to name a combination and use it as a part.

The skill's reading: a design that lacks one of the three ends up building features by
hand.

## What "orthogonal" means

Two parts are orthogonal when changing one does not affect the other. Raymond: "each
action changes just one thing without affecting others. There is one and only one way to
change each property." Hunt and Thomas give the test: *if the requirement behind one part
changes dramatically, how many parts are affected?* The answer should be one.

The opposite is the helicopter: every control affects every other, so one small change
makes the whole thing dip and turn.

## Brick kinds

Five kinds cover most application and service design. A sixth thing, the wiring, is not
a brick; it is how you put bricks together.

| Kind | Does | Orthogonality test |
|------|------|--------------------|
| **Input** | Brings something into a flow as plain data: an event, a request, a file, a timer tick. | Can the source switch (HTTP → queue → test fixture) with no change to any Transform? |
| **Transform** | Turns data into data. Parse, validate, enrich, filter, render, calculate. Pure where possible. | Does it run with no I/O, clock, or globals, and give the same output for the same input? |
| ↳ **Policy** | A Transform that returns a decision: which channel, which price, allowed or not, retry or give up. | Does a change of business rule touch only the policy, never the mechanism that uses it? |
| **Transport** | Moves data out or between parts: a vendor API, a queue, a file, another service, an event bus. | Does changing the destination leave everything upstream untouched? Does it contain no business decisions? |
| **Store** | Keeps data over time and hands it back through business verbs. No business rules inside. | Can the storage technology change behind it without any caller noticing? |
| **State machine** | Remembers where a long-running thing is and what may happen next: states, events, guards, transitions. | Are the states, events, and transitions explicit, and are effects returned as commands rather than performed inline? (For many states, use Harel's statecharts, with nested and parallel states, rather than a flat table.) |
| *Wiring* | The composition that binds bricks into a feature: code, a pipeline definition, or a table. | Is a new feature new wiring plus at most one new brick, with no logic in the wiring beyond selection and parameters? |

Keep Transforms pure and push I/O to the edges (Inputs, Transports, Stores). Bernhardt
calls this a functional core inside an imperative shell. It makes most bricks testable
with no mocks.

**A Store keeps data beyond one flow**, behind ResourceAccess. State that lives only while
a process runs (the current game, a request in progress) is a State machine's own state.
The Manager holds it.

**Kind is about role; location is about the wall.** A pull from a bank feed is an Input,
because it brings data into a flow. It lives in a ResourceAccess because the vendor is
volatile. A timer tick is an Input that lives in a Client (the scheduler).

## The shared contract

Bricks compose because they agree on one data shape: an envelope, a record, an event. The
shared contract is the equivalent of Unix text streams. (Don't confuse it with a
component's API, which is the business verbs callers use. The contract is what the bricks
pass around inside.)

- **One shape, many bricks.** Perlis: "It is better to have 100 functions operate on one
  data structure than 10 functions on 10 data structures."
- **Plain values at the boundary**, not objects with behaviour (Bernhardt, *Boundaries*).
- **Closure.** A composition of bricks is itself usable as a brick (SICP; Beam's
  composite transforms). This is what lets you build features from features.
- **Removable and reorderable stages.** Parnas (1979) warns about pipelines where you
  can't remove a stage because its neighbours' formats don't line up. A shared contract
  prevents that. Pipes and Filters (Hohpe and Woolf): add, omit, or rearrange filters
  "without having to change the filters themselves."
- **No junk, no confusion** (Raymond). The contract should not be able to represent
  situations that cannot exist, and states that differ in reality must differ in the
  contract.

**Scope.** Each wall has one shared contract for its bricks. Walls that pass data along
the same flow may share one (the notifications example shares an `Envelope`). Otherwise
each wall keeps its own (the shop example's `Quote` stays inside `PricingEngine`).

**Shapes at the edges.** Most bricks are `contract → contract`. The edges differ, and
that's fine:

| Kind | Shape |
|------|-------|
| Input | outside data → contract |
| Transform, policy | contract → contract (a policy may return zero or many) |
| Transport | contract → receipt |
| Store | business verbs that take and return the contract |
| State machine | (state, event) → (next state, commands to run) |

**When the contract itself changes.** The contract is the least changeable thing inside a
wall: reshaping it touches every brick. That is the price of composition, so keep it
small. If the register says the data's shape will change (split transactions, a new
currency field), keep the change additive. Add new optional fields; never rename or
repurpose fields.

Write the contract down in the design: its fields, which bricks may set each field, and
its invariants.

## Mechanism and policy

A mechanism says *how* something can be done. A policy says *what, when, or whether*.
Hydra (1974) made separating them a core design rule, so that one kernel of mechanisms
could support many policies built on top of it. Raymond, writing about X, adds why the
rule pays off in general. Policy changes much faster than mechanism, and hard-wiring them
together makes policy rigid and mechanism unstable.

In practice: bricks are mechanism. "Which channel for this user", "which discount wins",
"how many retries" are policy, supplied as data or as a Policy brick. If a brick has an
`if customer == …` inside it, a policy is trapped in a mechanism.

## Deriving bricks from features

1. **Start from two or three real features**, not an imagined platform. AWS's compass:
   "pick real customer problems you're trying to solve."
2. **Break each feature down with Hickey's questions** ("Simple Made Easy"), keeping each
   answer separate from the others:

   | Hickey's question | What he means | In brick terms |
   |-------------------|---------------|----------------|
   | *What* | the operations: small sets of function specifications | each brick's small interface |
   | *Who* | the entities, built from subcomponents passed in as arguments | wiring that hands bricks to each other, rather than bricks reaching for each other |
   | *How* | the implementation, kept strictly apart from *what* | a brick's internals, hidden behind its interface |
   | *When and where* | "stick a queue in there" instead of A calling B | Transports |
   | *Why* | policy and rules | Policies, as rules or data |

   The skill adds two questions of its own: *what must be remembered?* (Stores) and
   *where is this thing in its life?* (State machines). Hickey warns that state complects
   everything it touches, so keep it in few, explicit places.

3. **Pull out the verbs that repeat across features.** Those are the brick candidates.
4. **Define the shared contract** from the data every candidate needs to read or write.
5. **Split anything that does two independent things.** AWS's 2003 vision for its public
   services: primitives are indivisible; "if they can be functionally split into two they
   must." Inside a codebase, balance this with Ousterhout's warning against *classitis*.
   Keep pieces together when they share information, when combining them simplifies the
   interface, or when splitting would duplicate code.
6. **Write every feature as wiring**: `Input → Transform → … → Transport`. If you can't
   write a feature this way, it needs a new brick (justify it), or it reveals a wrong
   wall.

## Choosing the composition medium

Use the least powerful medium that works. This rule adapts the W3C's *Rule of Least
Power*, which the W3C wrote for publishing on the Web.

| Medium | Use when |
|--------|----------|
| Plain code calling bricks | Default. Compositions change at the same pace as the code. |
| A table (rows of parameters) | Many variants of the same composition that differ only in values. |
| A pipeline definition or stored workflow | The composition itself is a recorded volatility *and* it differs by kind of item, customer, or locale, or runs long across sessions and devices (Löwy's reasons for storing workflows, run by a workflow tool), or changes faster than you can deploy (the skill's addition). |
| A rules engine or a DSL | Almost never, for your own wiring. |

Hadlow's *Configuration Complexity Clock* goes like this. Hard-coded values become config,
config becomes a rules engine, and the rules engine becomes a DSL. Then you end up "hard
coding everything, except now in a much crappier language." The end state resembles the
Inner-Platform Effect (Papadimoulis): a poor copy of the platform you started with. If the
wiring needs loops or conditionals, write it in code.

**User-written rules are different.** When end users author rules as a feature (an
accountant's categorisation rules, a marketer's promotions), the rules are customer data,
not your wiring. The small language that users write them in belongs to an Engine, as a
set of condition and action bricks. Keep that language as small as the feature needs: a
list of conditions and actions, no loops or variables. Grow it only on evidence.

## Tests every brick must pass

| Test | Question | Pass |
|------|----------|------|
| Change count | If this brick's requirement changed dramatically, what else would change? | Nothing |
| Swap | Can another brick of the same kind replace this one without touching its neighbours? | Yes |
| Remove or reorder | Can you remove or move this stage without reshaping its neighbours? | Yes |
| Purity (Transforms) | Does it run with no I/O, clock, or globals? | Yes |
| Depth | Is the interface small relative to what it hides? (Ousterhout: "deep modules") | Yes |
| Easy for today | Is it easy to use for the current features? (If not, it is too general.) | Yes |
| Earned | Does it serve two or more current features, or one current feature as a variant a recorded volatility names? | Yes |

Ousterhout's three questions for a brick's interface:

1. What is the simplest interface that covers all my current needs?
2. In how many situations will this be used?
3. Is it easy to use for my current needs?

He calls the target **somewhat general-purpose**: the functionality reflects today's
needs, but the interface is not tied to one caller.

## Guardrails against over-building

Bricks usually go wrong by being too general, too early. They can also go wrong by being
too small: Ousterhout's *classitis*, many shallow pieces whose interfaces cost more than
they hide.

- **Earn every brick** (the skill's own rule):
  - A Transform, policy, or Store serves two or more current features. Failing that, it
    serves one current feature as one of the variants a recorded volatility names (one
    channel, one kind of discount). Otherwise, leave the logic inline in the composition.
  - Inputs and Transports at the edges are exempt: every feature needs a way in and out.
  - Never merge bricks to satisfy this rule. A merged brick with a mode flag is the smell
    below.
  - This rule is looser than the rule of three on purpose. At design time you are
    deciding where new code goes, not extracting existing duplication.
- **Rule of three** (Roberts, via Fowler). Use it whenever you would extract a brick from
  existing code, including host code in subsystem mode. Do it once, duplicate it the
  second time, and extract it the third time. Two similar pieces don't yet justify a
  brick.
- **Prefer duplication over the wrong abstraction** (Metz). The warning sign is passing
  parameters and adding conditional paths through shared code. The remedy is to inline
  the brick back into each caller, delete what each caller doesn't use, and extract again.
- **YAGNI** (Fowler) covers presumptive features *and* abstractions added for future
  flexibility. Fowler: "any abstraction that makes it harder to understand the code for
  current requirements is presumed guilty." Its exemption is refactoring, effort that
  makes the code easier to modify. So build bricks for today's features, and never a brick
  that only a future feature needs.
- **Future features are tests, not tasks.** Use them to check that the design would absorb
  them. Don't build them.
- **Watch the public surface.** Hyrum's law: with enough users of an API, somebody will
  depend on every observable behaviour. A brick used by many compositions
  gets there quickly, so expose as little as possible.

## Smells

| Smell | What it means | Fix |
|-------|---------------|-----|
| A `mode`, `type`, or `kind` flag that switches between different behaviours | Two or more bricks in one | Split it. (A parameter the same behaviour uses, such as a predicate or a threshold, is fine.) |
| Many tiny bricks, each with an interface nearly as big as its body | Classitis (Ousterhout) | Merge pieces that share information or always change together |
| A brick named after a feature (`SendWelcomeEmail`) | Feature code posing as a brick | Split into general bricks (`Render`, `Send`) plus wiring |
| A brick that calls another brick directly to hand off work | When and where are tangled with what | Put the hand-off in the wiring or on a Transport |
| Business rules inside a Transport or Store | Policy trapped in mechanism | Move the rule to a Policy. Exception: an invariant that must hold atomically with the write (no writes to a locked period) belongs in the Store's verb, as a guard |
| Flags and conditionals scattered to track progress | A hidden state machine | Make the state machine explicit |
| Each brick takes its own input shape | No shared contract | Define one, adapt at the edges |
| A brick with one caller and no volatility behind it | Speculative | Inline it |
| Config with loops, conditionals, or variables | The configuration clock has struck | Move that logic back to code |
| Changing one brick forces changes in its neighbours | Not orthogonal | Find the shared hidden decision and give it one home |
