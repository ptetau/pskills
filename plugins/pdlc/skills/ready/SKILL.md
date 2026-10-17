---
name: ready
description: >
  Makes sure that the spec patches of a pdlc intent are clear enough to build. Asks the
  user about each unclear item, one question at a time. Looks for contradictions in the
  specs, and marks requirements ready. Use when the user says "/pdlc:ready", or asks if
  an intent is ready to build.
---

# pdlc ready

Ready makes sure that each requirement that an intent touches is clear, testable, and
consistent.

Read `pdlc/README.md` first, and follow its instructions. Start with its "Before any
work" step.

## 1. Gather

If the user named no intent, take the oldest intent with status `specifying`. Read the
intent and its "Handoff". Then collect these items:

- Each requirement in the "Requirements" section of the intent that is `proposed` or
  `retiring`.
- The specs that hold these requirements.

## 2. Check each requirement

A requirement is clear when these conditions are true:

- The requirement says what must be true, not how to build it.
- Each acceptance check is a "Given …, when …, then …" line that a check can prove with a
  pass or a fail.
- Each line uses concrete values ("Ana", "80", "15%"), not "a user" or "some amount".
- Where there is a limit, there are lines just inside and just outside the limit (59:59
  and 60:00 for a one-hour limit).
- Each line checks one behaviour. The "then" of the line is something that a caller can
  see: a reply, an output, or a sent message. A stored row is not a correct "then".
- Each failure line names its error code, and `DES-errors` has that code. For a new code,
  add the code to `DES-errors` as part of this intent.
- Words like "fast", "easy" or "secure" have a number or a rule behind them.
- Each capability spec and design spec that the requirement relies on exists, or is part
  of this intent.

## 3. Ask about what is unclear

Follow "Asking questions" in `pdlc/README.md`. If the user gave `defaults`, do not ask.
Take your recommended answer.

Write each answer into the requirement. If you took the answer by default, mark the
answer *(assumed)* where it appears in the requirement. Add a line to the "Notes" of the
intent: `<requirement>: <question> → <answer>`.

If a design spec is missing (for example, the first time that the project shows a table),
use the `pdlc:conventions` skill to agree a design spec. Then continue with this step.

## 4. Look for contradictions

Compare the requirements with each other. Then compare the requirements with the other
requirements in the same specs, and in the specs that they rely on. A contradiction is two
statements that cannot both be true. For example: "responds within 50 ms" and "always
calls a service that takes 200 ms".

For each contradiction that you find, show the two statements. Ask the user which
statement to change. Do not select for the user, also when the user gave `defaults`.
Leave the two requirements `proposed`, and tell the user that they stay `proposed`.

## 5. Finish

1. Set each clear requirement from `proposed` to `ready`. Keep each `retiring`
   requirement as it is.
2. If each requirement of the intent is now `ready` or `retiring`, set the intent to
   `ready`.
3. Write the "Handoff" of the intent for change: the decisions, and anything that is
   useful for the plan.
4. Commit with the message "Ready IN-xxxx: <name>" and the trailer `Intent: IN-xxxx`.
5. Tell the tracker port.
6. Tell the user what changed, and that `/pdlc:change` is next.
