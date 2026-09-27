---
name: ready
description: >
  Checks that a pdlc intent's spec patches are clear enough to build. Asks the user about
  anything unclear, one question at a time, checks the specs for contradictions, and marks
  requirements ready. Use when the user says "/pdlc:ready", or asks if an intent is ready
  to build.
---

# pdlc ready

Makes sure every requirement an intent touches is clear, testable and consistent.

Read `pdlc/README.md` first and follow it. Start with its "Before any work" step.

## 1. Gather

Read the intent and its "Handoff". If none was named, take the oldest intent with status
`specifying`.
Collect every requirement in its "Requirements" section that is `proposed` or `retiring`,
and the specs they sit in.

## 2. Check each requirement

A requirement is clear when:

- It says what must be true, not how to build it.
- Each acceptance check is a "Given …, when …, then …" line that a check could prove with a
  pass or fail.
- Each line uses concrete values ("Ana", "80", "15%"), not "a user" or "some amount".
- Where there is a limit, there are lines just inside and just outside it (59:59 and
  60:00 for a one-hour limit).
- Each line checks one behaviour, and its "then" is something a caller can see: a reply,
  an output, a message sent. Never a stored row.
- Each failure line names its error code, and the code is in `DES-errors`. For a new
  code, add it to `DES-errors` as part of this intent.
- Words like "fast", "easy" or "secure" have a number or a rule behind them.
- Every capability and design spec it relies on exists, or is part of this intent.

## 3. Ask about what is unclear

Follow "Asking questions" in `pdlc/README.md`. If run with `defaults`, don't ask: take
your recommended answer.

Write each answer into the requirement. When the answer was taken by default, mark it
*(assumed)* where it appears in the requirement. Add a line to the intent's "Notes":
`<requirement>: <question> → <answer>`.

If a design spec is missing (for example, the first time the project shows a table), use
the `pdlc:conventions` skill to agree one, then come back.

## 4. Look for contradictions

Compare the requirements against each other and against the other requirements in the same
specs, and in the specs they rely on. A contradiction is two statements that can't both be
true, for example "responds within 50 ms" and "always calls a service that takes 200 ms".

For each one found, show both statements and ask the user which should change. Don't pick
for them, even with `defaults`: leave both requirements `proposed` and say so.

## 5. Finish

- Set each clear requirement from `proposed` to `ready`. Leave `retiring` as it is.
- If every requirement for the intent is now `ready` or `retiring`, set the intent to
  `ready`.
- Write the intent's "Handoff" for change: what was decided, and anything the plan should
  know.
- Commit with the message "Ready IN-xxxx: <name>" and the trailer `Intent: IN-xxxx`.
- Tell the tracker port.
- Tell the user what changed, and that `/pdlc:change` is next.
