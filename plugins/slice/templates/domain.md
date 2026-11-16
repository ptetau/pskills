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

One section for each object that has a lifecycle.

### <Object>

- States: <all states>. Start: <state>. End: <states>.
- T1 <from> to <to>: trigger <what starts it>, guard <what must hold>, effect <what changes>.
- Not allowed: <from> to <to> gives the error <error form>.

## Bounded contexts and boundary

- Inside: <what the system owns>
- Outside: <what it does not own>
- Actors: <each external actor or system, and how it talks to the system>

## Requirement map

One line for each requirement of the spec. Write `GAP` when no part of the model meets it.

- R1: <entities, invariants, and boundary parts that meet it>. Transitions: <T1, if it changes state>.
