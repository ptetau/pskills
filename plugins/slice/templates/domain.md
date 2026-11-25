# Domain: <name>

This design document holds no code.

## Entities and value objects

- <Name> (entity): <what it is, and what identifies it>
- <Name> (value object): <what it holds, and why it has no identity>

## Relationships

- <A> has many <B>: <the rule>

## Invariants

- I1 (<topic>): <a rule that always holds>

## State machines

One `### Machine: <Object>` section for each object that has a lifecycle. For none, write the line `- Machines: none`. `slice.py status` reads these lines: the start state, each state reachable from it, each transition cited by a requirement.
### Machine: <Object>

- States: <all states, comma separated>
- Start: <state>
- End: <states, or none>
- T1: <from> -> <to> on <trigger> [<guard>] / <effect>
- X1: <from> on <trigger> refused: <error form>

## Bounded contexts and boundary

- Inside: <what the system owns>
- Outside: <what it does not own>
- Actors: <each external actor or system, and the public boundary (endpoints, CLI, or module calls) it uses>

## Requirement map

One line for each requirement of the spec. Write `GAP` when no part of the model meets it. A requirement that changes state cites its transitions as `Object.Tn` or `Object.Xn`. Each transition of each machine is cited by a requirement.

- R1: <entities, invariants, and boundary parts that meet it>, <Object.T1 or Object.X1 for each transition that it needs>
