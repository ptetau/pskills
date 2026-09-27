# Bricks: orthogonal primitives

How to design the inside of a wall. The walls (see `walls.md`) decide where change stops.
Bricks decide how features are assembled. Sources for every idea are in `sources.md`.

## The idea in one paragraph

Don't build features. Build a small number of independent parts, give them one shared
way to connect, and write each feature as a composition of parts. When a new feature
arrives, it should mostly be a new composition. This is how ALGOL 68 was designed (few
primitive concepts, applied orthogonally, for maximum expressive power), how Unix tools
work (small programs, one text-stream interface, pipes), and how AWS built its services
("primitives not frameworks").

SICP names the three things any such system needs:

1. **Primitives**: the simplest parts.
2. **A means of combination**: a way to build bigger things from smaller ones.
3. **A means of abstraction**: a way to name a combination and use it as a part.

A design has all three, or features will be built by hand.

## What "orthogonal" means

Two parts are orthogonal when changing one does not affect the other. Raymond: "each
action changes just one thing without affecting others. There is one and only one way to
change each property." Hunt and Thomas give the test: *if the requirement behind one part
changes dramatically, how many parts are affected?* The answer should be one.

The opposite is the helicopter: every control affects every other, so one small change
makes the whole thing dip and turn.

## Brick kinds

Five kinds cover most application and service design. A sixth thing, the wiring, is not
a brick; it is how bricks are put together.

| Kind | Does | Orthogonality test |
|------|------|--------------------|
| **Input** | Brings something into a flow as plain data: an event, a request, a file, a timer tick. | Can the source switch (HTTP → queue → test fixture) with no change to any Transform? |
| **Transform** | Turns data into data. Parse, validate, enrich, filter, render, calculate. Pure where possible. | Does it run with no I/O, clock, or globals, and give the same output for the same input? |
| ↳ **Policy** | A Transform that returns a decision: which channel, which price, allowed or not, retry or give up. | Does a change of business rule touch only the policy, never the mechanism that uses it? |
| **Transport** | Moves data out or between parts: a vendor API, a queue, a file, another service, an event bus. | Does changing the destination leave everything upstream untouched? Does it contain no business decisions? |
| **Store** | Keeps data over time and hands it back through business verbs. No business rules inside. | Can the storage technology change behind it without any caller noticing? |
| **State machine** | Remembers where a long-running thing is and what may happen next: states, events, guards, transitions. | Can every transition be written as a row in a table? Are its effects returned as commands, not performed inline? |
| *Wiring* | The composition that binds bricks into a feature: code, a pipeline definition, or a table. | Is a new feature new wiring plus at most one new brick, with no logic in the wiring beyond selection and parameters? |

Keep Transforms pure and push I/O to the edges (Inputs, Transports, Stores). Bernhardt
calls this a functional core inside an imperative shell. It makes most bricks testable
with no mocks.

## The shared contract

Bricks compose because they agree on one data shape: an envelope, a record, an event. It
is the equivalent of Unix text streams.

- **One shape, many bricks.** Perlis: "It is better to have 100 functions operate on one
  data structure than 10 functions on 10 data structures."
- **Plain values at the boundary**, not objects with behavior (Bernhardt, *Boundaries*).
- **Closure.** A composition of bricks is itself usable as a brick (SICP; Beam's
  composite transforms). This is what lets features be built from features.
- **Removable and reorderable stages.** Parnas (1979) warns about pipelines where a stage
  can't be removed because its neighbors' formats don't line up. A shared contract
  prevents that. Pipes and Filters (Hohpe and Woolf): add, omit, or rearrange filters
  "without having to change the filters themselves."
- **No junk, no confusion** (Raymond). The contract should not be able to represent
  situations that cannot exist, and states that differ in reality must differ in the
  contract.

Write the contract down in the design: its fields, which bricks may set each field, and
its invariants.

## Mechanism and policy

A mechanism says *how* something can be done. A policy says *what, when, or whether*.
Hydra (1974) made separating them a core rule because policy changes much faster than
mechanism, and hard-wiring them together makes policy rigid and mechanism unstable
(Raymond).

In practice: bricks are mechanism. "Which channel for this user", "which discount wins",
"how many retries" are policy, supplied as data or as a Policy brick. If a brick has an
`if customer == …` inside it, a policy is trapped in a mechanism.

## Deriving bricks from features

1. **Start from two or three real features**, not an imagined platform. AWS's compass:
   "pick real customer problems you're trying to solve."
2. **Break each feature down with Hickey's questions.** Map each answer to a brick kind:

   | Question | Maps to |
   |----------|---------|
   | *What* happens to the data? | Transforms |
   | *Who* or what starts it? | Inputs |
   | *When and where* does it go? | Transports (put a queue between A and B instead of A calling B) |
   | *Why* this outcome? | Policies, as rules or data |
   | *What must be remembered?* | Stores |
   | *Where is it in its life?* | State machines |

3. **Pull out the verbs that repeat across features.** Those are the brick candidates.
4. **Define the shared contract** from the data every candidate needs to read or write.
5. **Split anything that does two things.** AWS's 2003 definition: primitives are
   indivisible; "if they can be functionally split into two they must."
6. **Write every feature as wiring**: `Input → Transform → … → Transport`. A feature that
   cannot be written this way needs a new brick (justify it) or reveals a wrong wall.

## Choosing the composition medium

Use the least powerful medium that works (W3C, *Rule of Least Power*).

| Medium | Use when |
|--------|----------|
| Plain code calling bricks | Default. Compositions change at the same pace as the code. |
| A table (rows of parameters) | Many variants of the same composition that differ only in values. |
| A pipeline or state-machine definition as data | The composition itself is a recorded volatility, for example flows that differ per customer or change weekly without a deploy. |
| A rules engine or a DSL | Almost never. |

Hadlow's *Configuration Complexity Clock*: hard-coded values become config, config
becomes a rules engine, the rules engine becomes a DSL, and you end up "hard coding
everything, except now in a much crappier language." This is the Inner-Platform Effect.
If the wiring needs loops or conditionals, write it in code.

## Tests every brick must pass

| Test | Question | Pass |
|------|----------|------|
| Change count | If this brick's requirement changed dramatically, what else would change? | Nothing |
| Swap | Can this brick be replaced by another of the same kind without touching its neighbors? | Yes |
| Remove or reorder | Can this stage be removed or moved without reshaping its neighbors? | Yes |
| Purity (Transforms) | Does it run with no I/O, clock, or globals? | Yes |
| Depth | Is the interface small relative to what it hides? (Ousterhout: "deep modules") | Yes |
| Easy for today | Is it easy to use for the current features? (If not, it is too general.) | Yes |
| Earned | Does it serve at least one current feature or recorded volatility? | Yes |

Ousterhout's three questions for a brick's interface:

1. What is the simplest interface that covers all my current needs?
2. In how many situations will this be used?
3. Is it easy to use for my current needs?

He calls the target **somewhat general-purpose**: the functionality reflects today's
needs, but the interface is not tied to one caller.

## Guardrails against over-building

Bricks go wrong in one direction: too general, too early.

- **Rule of three.** Do it once. Duplicate it the second time. Extract a brick the third
  time.
- **Prefer duplication over the wrong abstraction** (Metz). The warning sign is passing
  parameters and adding conditional paths through shared code. The remedy is to inline
  the brick back into each caller, delete what each caller doesn't use, and extract again.
- **YAGNI applies to features, not to changeability** (Fowler). Don't build a capability
  nobody uses yet. Do keep the code easy to change.
- **Future features are tests, not tasks.** Use them to check that the design would absorb
  them. Don't build them.
- **Watch the public surface.** Every observable behavior of a brick will be depended on
  by somebody (Hyrum's law). Expose as little as possible.

## Smells

| Smell | What it means | Fix |
|-------|---------------|-----|
| A `mode`, `type`, or `kind` flag that switches behavior | Two or more bricks in one | Split it |
| A brick named after a feature (`SendWelcomeEmail`) | Feature code posing as a brick | Split into general bricks (`Render`, `Send`) plus wiring |
| A brick that calls another brick directly to hand off work | When and where are tangled with what | Put the hand-off in the wiring or on a Transport |
| Business rules inside a Transport or Store | Policy trapped in mechanism | Move the rule to a Policy |
| Flags and conditionals scattered to track progress | A hidden state machine | Make the state machine explicit |
| Each brick takes its own input shape | No shared contract | Define one, adapt at the edges |
| A brick with one caller and no volatility behind it | Speculative | Inline it |
| Config with loops, conditionals, or variables | The configuration clock has struck | Move that logic back to code |
| Changing one brick forces changes in its neighbors | Not orthogonal | Find the shared hidden decision and give it one home |
