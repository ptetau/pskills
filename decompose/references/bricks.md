# Bricks: orthogonal primitives

This file tells you how to design the inside of a wall. The walls (see `walls.md`) decide
where a change stops. The bricks decide how you assemble features. `sources.md` gives the
source of each idea.

## The idea in one paragraph

Do not build features. Build a small number of independent parts. Give the parts one
shared way to connect. Then write each feature as a composition of parts. The goal is that
a new feature is mostly a new composition. These designs use the same idea:

- ALGOL 68: few primitive concepts, applied orthogonally, for maximum expressive power.
- Unix tools: small programs, one text-stream interface, and pipes.
- The services of AWS: "primitives not frameworks".

SICP gives the three things that each such system must have:

1. **Primitives**: the simplest parts.
2. **A means of combination**: a way to build bigger things from smaller things.
3. **A means of abstraction**: a way to give a name to a combination, and to use the
   combination as a part.

This skill reads SICP as follows: a design that does not have one of the three things
builds features by hand.

## What "orthogonal" means

Two parts are orthogonal when a change to one part does not affect the other part.
Raymond: "each action changes just one thing without affecting others. There is one and
only one way to change each property."

Hunt and Thomas give a test for orthogonality. Ask: *if the requirement behind one part
changes dramatically, how many parts are affected?* The correct answer is one.

The opposite is a helicopter. In a helicopter, each control affects each other control.
Thus, one small change makes the full helicopter dip and turn.

## Brick kinds

Five kinds of brick cover most designs of applications and services. A sixth item, the
wiring, is not a brick. The wiring is the way that you assemble the bricks.

| Kind | Does | Orthogonality test |
|------|------|--------------------|
| **Input** | Brings something into a flow as plain data: an event, a request, a file, a timer tick. | Can the source change (HTTP → queue → test fixture) with no change to a Transform? |
| **Transform** | Changes data into data, for example parse, validate, enrich, filter, render, or calculate. Pure where possible. | Does the Transform run with no I/O, clock, or globals? Does it give the same output for the same input? |
| ↳ **Policy** | A Transform that returns a decision: which channel, which price, allowed or not, retry or stop. | Does a change to a business rule change only the policy, and not the mechanism that uses the policy? |
| **Transport** | Moves data out, or between parts: a vendor API, a queue, a file, a different service, an event bus. | If the destination changes, does all of the upstream stay the same? Does the Transport contain no business decisions? |
| **Store** | Keeps data over time, and gives the data back through business verbs. Has no business rules inside. | Can the storage technology behind the Store change with no effect on a caller? |
| **State machine** | Remembers where a long-running thing is, and what can occur next: states, events, guards, and transitions. | Are the states, events, and transitions explicit? Does the machine return effects as commands, and not do them inline? (For many states, use Harel's statecharts, with nested and parallel states, not a flat table.) |
| *Wiring* | The composition that connects bricks into a feature: code, a pipeline definition, or a table. | Is a new feature only new wiring plus a maximum of one new brick? Does the wiring have no logic other than selection and parameters? |

Keep Transforms pure. Move I/O to the edges (Inputs, Transports, Stores). Bernhardt calls
this design a functional core inside an imperative shell. With this design, you can test
most bricks with no mocks.

**A Store keeps data beyond one flow**, behind ResourceAccess. Some state lives only while
a process runs (the current game, a request in progress). That state belongs to a State
machine, and the Manager holds the state.

**The kind is about the role. The location is about the wall.** For example, a pull from a
bank feed is an Input, because the pull brings data into a flow. The pull lives in a
ResourceAccess, because the vendor is volatile. A timer tick is an Input that lives in a
Client (the scheduler).

## The shared contract

Bricks compose because they agree on one data shape: an envelope, a record, or an event.
The shared contract is the equivalent of Unix text streams. The contract is not the API of
a component. The API is the business verbs that callers use. The contract is the data that
the bricks pass to each other inside the wall.

- **One shape, many bricks.** Perlis: "It is better to have 100 functions operate on one
  data structure than 10 functions on 10 data structures."
- **Plain values at the boundary**, not objects with behaviour (Bernhardt, *Boundaries*).
- **Closure.** You can use a composition of bricks as a brick (SICP, and Beam's composite
  transforms). Thus, you can build features from features.
- **Removable and reorderable stages.** Parnas (1979) gives a warning about pipelines where
  you cannot remove a stage, because the formats of its neighbours do not agree. A shared
  contract prevents this problem. Pipes and Filters (Hohpe and Woolf): add, omit, or
  rearrange filters "without having to change the filters themselves."
- **No junk, no confusion** (Raymond). The contract must not be able to show a situation
  that cannot exist. Two states that are different in reality must also be different in
  the contract.

**Scope.** Each wall has one shared contract for its bricks. Walls that pass data along the
same flow can share one contract (the notifications example shares an `Envelope`). Each
other wall keeps its own contract (in the shop example, `Quote` stays inside
`PricingEngine`).

**Shapes at the edges.** Most bricks are `contract → contract`. The bricks at the edges
are different, and this difference is correct:

| Kind | Shape |
|------|-------|
| Input | outside data → contract |
| Transform, policy | contract → contract (a policy can return zero or many) |
| Transport | contract → receipt |
| Store | business verbs that take and return the contract |
| State machine | (state, event) → (next state, commands to run) |

**When the contract itself changes.** The contract is the least changeable item inside a
wall, because a new shape of the contract changes each brick. This cost is the price of
composition. Thus, keep the contract small.

If the register says that the shape of the data will change (split transactions, a new
currency field), make the change additive. Add new optional fields. Do not rename a field,
and do not give a field a new purpose.

Write the contract in the design: its fields, the bricks that can set each field, and its
invariants.

## Mechanism and policy

A mechanism tells *how* to do something. A policy tells *what, when, or whether*. Hydra
(1974) made the separation of the two a core design rule. Thus, one kernel of mechanisms
could support many policies on top of the kernel.

Raymond wrote about X, and he tells why the separation of mechanism and policy is good in
general. Policy changes much faster than mechanism. If you hard-wire the two together, the
policy becomes rigid and the mechanism becomes unstable.

In practice, bricks are mechanism. "Which channel for this user", "which discount wins",
and "how many retries" are policy. Supply each policy as data or as a Policy brick. If a
brick has an `if customer == …` inside it, a policy is trapped in a mechanism.

## Deriving bricks from features

1. **Start from two or three real features**, not from an imagined platform. The compass
   of AWS: "pick real customer problems you're trying to solve."
2. **Divide each feature with Hickey's questions** ("Simple Made Easy"). Keep each answer
   separate from the other answers:

   | Hickey's question | What he means | In brick terms |
   |-------------------|---------------|----------------|
   | *What* | the operations: small sets of function specifications | the small interface of each brick |
   | *Who* | the entities, built from subcomponents that you give as arguments | wiring that gives bricks to each other, not bricks that find each other |
   | *How* | the implementation, kept strictly apart from *what* | the internals of a brick, hidden behind its interface |
   | *When and where* | "stick a queue in there", not a direct call from A to B | Transports |
   | *Why* | policy and rules | Policies, as rules or data |

   The skill adds two questions of its own: *what must the system remember?* (Stores) and
   *where is this thing in its life?* (State machines). Hickey gives a warning that state
   complects all that it touches. Thus, keep state in few, explicit places.

3. **Find the verbs that repeat across features.** These verbs are the brick candidates.
4. **Define the shared contract** from the data that each candidate must read or write.
5. **Split each part that does two independent things.** The 2003 vision of AWS for its
   public services: primitives are indivisible, and "if they can be functionally split
   into two they must." Inside a codebase, balance this rule with Ousterhout's warning
   against *classitis*. Keep pieces together in these conditions:
   - The pieces share information.
   - A combination of the pieces makes the interface simpler.
   - A split would duplicate code.
6. **Write each feature as wiring**: `Input → Transform → … → Transport`. If you cannot
   write a feature this way, the feature needs a new brick (give the reason for the
   brick). Or, the feature shows a wrong wall.

## Choosing the composition medium

Use the least powerful medium that works. This rule is an adaptation of the W3C's *Rule of
Least Power*. The W3C wrote that rule for publication on the Web.

| Medium | Use when |
|--------|----------|
| Plain code that calls bricks | Default. Compositions change at the same speed as the code. |
| A table (rows of parameters) | Many variants of the same composition that are different only in values. |
| A pipeline definition or stored workflow | The composition itself is a recorded volatility, *and* one of these conditions is true: it is different for each kind of item, customer, or locale, or it runs long across sessions and devices (Löwy's reasons to store workflows, which a workflow tool runs), or it changes faster than you can deploy (the skill's addition). |
| A rules engine or a DSL | Only in very rare conditions, for your own wiring. |

Hadlow's *Configuration Complexity Clock* gives this sequence. Hard-coded values become
config. Then config becomes a rules engine, and the rules engine becomes a DSL. At the end,
you are "hard coding everything, except now in a much crappier language."

The end state of Hadlow's clock is similar to the Inner-Platform Effect (Papadimoulis): a
poor copy of the platform that you started with. If the wiring needs loops or
conditionals, write the wiring in code.

**User-written rules are different.** Sometimes end users write rules as a feature (the
categorisation rules of an accountant, the promotions of a marketer). These rules are
customer data, not your wiring. The small language of these rules belongs to an Engine, as
a set of condition and action bricks. Keep that language as small as the feature needs (a
list of conditions and actions, with no loops or variables). Make the language larger only
when you have evidence.

## Tests every brick must pass

| Test | Question | Pass |
|------|----------|------|
| Change count | If the requirement of this brick changes dramatically, what else must change? | Nothing |
| Swap | Can you replace this brick with a different brick of the same kind, and not change its neighbours? | Yes |
| Remove or reorder | Can you remove or move this stage, and not change the shape of its neighbours? | Yes |
| Purity (Transforms) | Does the Transform run with no I/O, clock, or globals? | Yes |
| Depth | Is the interface small, compared with what the interface hides? (Ousterhout: "deep modules") | Yes |
| Easy for today | Is the brick easy to use for the current features? (If not, the brick is too general.) | Yes |
| Earned | Does the brick serve two or more current features? Or does it serve one current feature as a variant that a recorded volatility names? | Yes |

Ousterhout gives three questions for the interface of a brick:

1. What is the simplest interface that covers all my current needs?
2. In how many situations will callers use this interface?
3. Is it easy to use for my current needs?

Ousterhout calls the target **somewhat general-purpose**. The functionality agrees with the
needs of today, but the interface is not tied to one caller.

## Guardrails against over-building

The usual problem with bricks is that they are too general, too early. A different problem
is bricks that are too small. Ousterhout calls this problem *classitis*: many shallow
pieces with interfaces that cost more than they hide.

- **Earn every brick** (the skill's own rule). A Transform, policy, or Store must serve two
  or more current features. Or, the brick must serve one current feature as one of the
  variants that a recorded volatility names (one channel, one kind of discount). If not,
  keep the logic inline in the composition.
  - Inputs and Transports at the edges are exempt, because each feature needs a way in and
    a way out.
  - Do not merge bricks to obey this rule. A merged brick with a mode flag is the first
    smell in the table below.
  - This rule is looser than the rule of three on purpose. At design time, you decide
    where new code goes. You do not extract duplication that exists.
- **Rule of three** (Roberts, through Fowler). Use this rule when you extract a brick from
  existing code, also from host code in subsystem mode. The first time, write the code.
  The second time, duplicate the code. The third time, extract the brick. Two similar
  pieces are not yet a reason for a brick.
- **Prefer duplication over the wrong abstraction** (Metz). The warning sign: callers pass
  parameters and add conditional paths through shared code. The remedy has three steps.
  Inline the brick back into each caller. Delete what each caller does not use. Then
  extract again.
- **YAGNI** (Fowler) applies to presumptive features *and* to abstractions that you add for
  future flexibility: "any abstraction that makes it harder to understand the code for
  current requirements is presumed guilty." Refactoring is exempt. Refactoring is work
  that makes the code easier to modify. Thus, build bricks for the features of today. Do
  not build a brick that only a future feature needs.
- **Future features are tests, not tasks.** Use a future feature to make sure that the
  design can absorb it. Do not build the future feature.
- **Watch the public surface.** Hyrum's law: when an API has sufficient users, somebody
  depends on each observable behaviour. A brick that many compositions use gets to this
  point quickly. Thus, expose as little as possible.

## Smells

| Smell | What it means | Fix |
|-------|---------------|-----|
| A `mode`, `type`, or `kind` flag that switches between different behaviours | Two or more bricks in one | Split the brick. (A parameter that the same behaviour uses, for example a predicate or a threshold, is correct.) |
| Many tiny bricks, each with an interface almost as large as its body | Classitis (Ousterhout) | Merge pieces that share information or that always change together |
| A brick named after a feature (`SendWelcomeEmail`) | Feature code that looks like a brick | Split it into general bricks (`Render`, `Send`) plus wiring |
| A brick that calls a different brick directly to give it work | *When* and *where* are tangled with *what* | Put the hand-off in the wiring or on a Transport |
| Business rules inside a Transport or Store | Policy trapped in mechanism | Move the rule to a Policy. Exception: an invariant that must hold atomically with the write (no writes to a locked period) belongs in the verb of the Store, as a guard |
| Flags and conditionals in many places that track progress | A hidden state machine | Make the state machine explicit |
| Each brick takes its own input shape | No shared contract | Define one shared contract. Adapt at the edges |
| A brick with one caller and no volatility behind it | Speculative | Inline the brick |
| Config with loops, conditionals, or variables | The configuration clock struck | Move that logic back to code |
| A change to one brick forces changes in its neighbours | Not orthogonal | Find the shared hidden decision, and give that decision one home |
