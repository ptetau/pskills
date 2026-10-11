---
name: ready
description: >
  Checks that a pdlc intent's spec patches are clear enough to build. Asks the user about
  anything unclear, one question at a time. Checks the specs for contradictions and marks
  requirements ready. Use when the user says "/pdlc:ready", or asks if an intent is ready
  to build.
---

# pdlc ready

Makes sure every requirement an intent touches is clear, testable and consistent.

Read `pdlc/README.md` first and follow it. Start with its "Before any work" step.

## 1. Gather

Read the intent the user named, and its "Handoff". If the user named none, take the oldest
intent with status `specifying`. If the intent has a `Branch:`, switch to that branch.
Commit there.

Collect every requirement in the intent's "Requirements" section that is `proposed` or
`retiring`. Also collect the specs those requirements sit in.

## 2. Settle what the intent implies

Before you mark anything ready, list the behaviour the intent implies but doesn't state.
Go through this list. Skip what doesn't apply:

- bad and empty input;
- limits and sizes;
- order;
- what happens to existing data;
- input that could be unsafe: sizes, injection, paths;
- business rules the words leave open: who may do what, what happens twice, what
  happens when something is missing.

Settle each one as a requirement with acceptance lines. Either:

- add lines to the requirement it belongs to; or
- write a new `proposed` requirement in the right spec, and list it in the intent's
  "Requirements" as added.

Ask about each one as step 4 (ask about what is unclear) says. With `defaults`, take your
recommended answer and mark it `(assumed)`. Put the list in the handoff. Without the
user's approval, pdlc never builds what you leave out here.

## 3. Check each requirement

A requirement is clear when:

- It says what must be true, not how to build it.
- Each acceptance check is a "Given …, when …, then …" line that a check could prove with a
  pass or fail.
- Each line uses concrete values ("Ana", "80", "15%"), not "a user" or "some amount".
- Every example in the intent's own words is an acceptance line, exactly as given.
- Where a requirement says how something looks to the user, a line gives the exact text
  the user sees, and where. Lines also cover an edge value (zero, empty, a whole number).
- Where there is a limit, there are lines just inside and just outside it (59:59 and
  60:00 for a one-hour limit).
- Every input the requirement reads (an argument, a field, a request, a stored file) has
  lines for its bad forms. The bad forms are missing, empty, the wrong type and too large.
  Stored data has two more: unreadable, and written by an older version. The "then" is a
  coded refusal, or a stated default for an older record. Never a crash, a hang, a stack
  trace, or a silent empty, zero or null.
- Each line checks one behaviour, and its "then" is something a caller can see: a reply,
  an output, a message sent. Never a stored row.
- Each failure line names its error code, and the code is in `DES-errors`. For a new
  code, add it to `DES-errors` as part of this intent.
- Every rule the requirement's sentences state has an acceptance line, including each
  `(assumed)` detail. A rule with no line has no check, so nothing holds it.
- Words like "fast", "easy" or "secure" have a number or a rule behind them.
- Every capability and design spec the requirement relies on exists, or is part of this
  intent.

## 4. Ask about what is unclear

Follow "Asking questions" in `pdlc/README.md`. With `defaults`, don't ask. Take your
recommended answer instead. Recommend the plain reading of the intent's words, for every
value. Never recommend a reading that keeps the old behaviour when the plain words change
it. Never recommend a reading that makes one of the intent's examples come out
differently.

Write each answer into the requirement. If you took the answer by default:

- mark the answer `(assumed)` where it appears in the requirement;
- add a line to the intent's "Notes": `<requirement>: <question> → <answer> (assumed)`.

If a design spec is missing (for example, the first time the project shows a table), use
the `pdlc:conventions` skill to agree one. Then come back here.

## 5. Look for contradictions

Compare the requirements with each other. Also compare them with the other requirements in
the same specs, and in the specs they rely on. A contradiction is two statements that
can't both be true, for example "responds within 50 ms" and "always calls a service that
takes 200 ms".

Two cases are not contradictions. Fix each one, and add a line to "Notes" for it. Then go
on:

- This intent's words ask for something an older requirement rules out. The newest words
  win. Change the older requirement, as intake does. List the older requirement as
  `changed`.
- One side is `(assumed)`. A guess gives way. Change the guessed side to fit. Keep its
  mark. Update its line in "Notes".

For any other contradiction, show both statements. Ask the user which one should change.
Don't pick for the user, even with `defaults`. Leave both requirements `proposed`, and say
so.

Each time you change or retire a requirement here, leave no old wording. Follow "Leave no
old wording" in intake's step 4 (write the patches). Fix every title, summary, example,
cross-reference and note in the specs that still shows the old behaviour. List old README
lines in "Notes".

## 6. Finish

- Set each clear requirement from `proposed` to `ready`. Leave each `retiring` requirement
  as it is.
- If every requirement for the intent is now `ready` or `retiring`, set the intent to
  `ready`.
- Write the intent's "Handoff" for change: the decisions, and anything the plan should
  know.
- Commit with the message "Ready IN-xxxx: <name>" and the trailer `Intent: IN-xxxx`. Even
  when you stop for a contradiction, commit.
- Tell the tracker port.
- Tell the user what changed, and that `/pdlc:change` is next.
