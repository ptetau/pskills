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
intent and its "Handoff". If the intent has a `Branch:`, switch to that branch. Make each
commit on that branch. Then collect these items:

- Each requirement in the "Requirements" section of the intent that is `proposed` or
  `retiring`.
- The specs that hold these requirements.

## 2. Settle what the intent implies

Before you mark anything ready, list the behaviour that the intent implies but does not
state. Examine each item in this list. Skip each item that does not apply:

- Bad and empty input.
- Limits and sizes.
- Order.
- What happens to existing data.
- Input that can be unsafe: sizes, injection, and paths.
- Business rules that the words leave open: who is permitted to do what, what happens
  twice, and what happens when something is missing.

Settle each item as a requirement with acceptance lines. Keep each sentence at 25 words or
fewer, also in an acceptance line. A line that lists many values is often too long. Write
two lines instead, or end the "then" part with a full stop and add a second short
sentence. Give each ID in a sentence a short description, as in `R5 (usage line)`. Do one
of these:

- Add lines to the requirement that the item belongs to.
- Write a new `proposed` requirement in the right spec. List the new requirement as added
  in the "Requirements" section of the intent.

Ask about each item, as step 4 (ask about what is unclear) says. If the user gave
`defaults`, take your recommended answer and mark the answer `(assumed)`. Put the list in
the handoff. Do not build an item that you omit here, unless the user approves the
item.

## 3. Check each requirement

A requirement is clear when these conditions are true:

- The requirement says what must be true, not how to build it.
- Each acceptance check is a "Given …, when …, then …" line that a check can prove with a
  pass or a fail.
- Each line uses concrete values ("Ana", "80", "15%"), not "a user" or "some amount".
- Each example in the words of the intent is an acceptance line. The line gives the
  example exactly as written.
- Where the requirement says how something looks to the user, a line gives the exact text
  and where the user sees the text. Other lines do the same for an edge value (zero,
  empty, or an integer).
- Where there is a limit, there are lines just inside and just outside the limit (59:59
  and 60:00 for a one-hour limit).
- Each input that the requirement reads (an argument, a field, a request, or a stored
  file) has lines for the bad forms of the input. The bad forms are missing, empty, the
  wrong type, and too large. Stored data has two more bad forms: unreadable, and written
  by an older version. The "then" of such a line is a coded refusal, or a stated default
  for an older record. A crash, a hang, a stack trace, or a silent empty, zero, or null is
  not a correct "then".
- Each line checks one behaviour. The "then" of the line is something that a caller can
  see: a reply, an output, or a sent message. A stored row is not a correct "then".
- Each failure line names its error code, and `DES-errors` has that code. For a new code,
  add the code to `DES-errors` as part of this intent.
- Each rule that a sentence of the requirement states has an acceptance line, including
  each `(assumed)` detail. A rule with no line has no check, so nothing enforces the rule.
- Words like "fast", "easy" or "secure" have a number or a rule behind them.
- Each capability spec and design spec that the requirement relies on exists, or is part
  of this intent.

## 4. Ask about what is unclear

Follow "Asking questions" in `pdlc/README.md`. If the user gave `defaults`, do not ask.
Take your recommended answer.

Recommend the plain reading of the words in the intent, for each value. Do not recommend
a reading that keeps the old behaviour when the plain words change the behaviour. Do not
recommend a reading that gives a different result for an example in the intent.

Write each answer into the requirement. If you took the answer by default, mark the
answer `(assumed)` where it appears in the requirement. Add a line to the "Notes" of the
intent: `<requirement>: <question> → <answer> (assumed)`.

If a design spec is missing (for example, the first time that the project shows a table),
use the `pdlc:conventions` skill to agree a design spec. Then continue with this step.

## 5. Look for contradictions

Compare the requirements with each other. Then compare the requirements with the other
requirements in the same specs, and in the specs that they rely on. A contradiction is two
statements that cannot both be true. For example: "responds within 50 ms" and "always
calls a service that takes 200 ms".

Two cases are not contradictions. For each case, fix the problem. Add a line to "Notes"
for the case. Then continue. The two cases are these:

- The words of this intent ask for something that an older requirement rules out. The
  newest words win. Change the older requirement, as intake does, and list the older
  requirement as `changed`.
- One side is `(assumed)`. A guess gives way. Change the guessed side to agree with the
  other side. Keep the mark of the guessed side, and update its line in "Notes".

For any other contradiction, show the two statements. Ask the user which statement to
change. Do not select for the user, also when the user gave `defaults`. Leave the two
requirements `proposed`, and tell the user that they stay `proposed`.

Each time that you change or retire a requirement here, leave no old wording. Follow
"Leave no old wording" in step 4 (write the patches) of intake. Fix each title, summary,
example, cross-reference, and note in the specs that still shows the old behaviour. List
the old lines of the README in "Notes".

## 6. Finish

1. Set each clear requirement from `proposed` to `ready`. Keep each `retiring`
   requirement as it is.
2. If each requirement of the intent is now `ready` or `retiring`, set the intent to
   `ready`.
3. Write the "Handoff" of the intent for change: the decisions, and anything that is
   useful for the plan.
4. Commit with the message "Ready IN-xxxx: <name>" and the trailer `Intent: IN-xxxx`. Also
   commit when you stop for a contradiction.
5. Tell the tracker port.
6. Tell the user what changed, and that `/pdlc:change` is next.
