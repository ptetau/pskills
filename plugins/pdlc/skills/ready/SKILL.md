---
name: ready
description: >
  Makes sure that the spec patches of a pdlc intent are clear enough to build. Asks the
  user about each unclear item, one question at a time, looks for contradictions in the
  specs, and marks requirements ready. Use when the user says "/pdlc:ready", or asks if
  an intent is ready to build.
---

# pdlc ready

## Goal

After ready, a test writer can write each check of the intent with no guess, and no spec
text still shows old behaviour. Each requirement that the intent touches is clear,
testable, and consistent, and is marked `ready`.

## Constraints

### Scope and branch

- The rules of `pdlc/README.md` hold, and "Bookkeeping on main" runs first. Each patch
  obeys "Spec patches", and each question obeys "Questions".
- The intent is the one that the user names, or else the oldest `specifying` intent.
- If the intent has a `Branch:`, ready works and commits on that branch.

### What to settle

- Before anything is `ready`, ready settles the behaviour that the intent implies but does
  not state. The items to examine, where they apply:
  - Bad and empty input. Limits and sizes. Order. What happens to existing data.
  - Unsafe input: sizes, injection, and paths.
  - Business rules that the words leave open: who is permitted to do what, what happens
    twice, and what happens when something is missing.
- Each settled item becomes acceptance lines on the requirement that it belongs to, or a
  new `proposed` requirement in the right spec. The intent lists a new requirement as
  added.
- A missing design spec (for example, the first table of the project) gets agreed through
  `pdlc:conventions`. Then ready continues.

### A requirement is clear when

- The requirement says what must be true, not how to build it.
- Each acceptance line is "Given …, when …, then …", and a check can prove it with a pass
  or a fail.
- Each line uses concrete values ("Ana", "80", "15%", a file with `b a b`), not "a user",
  "some amount", or "any file". Its "then" gives the exact output, not "the same error".
  Ready rewrites each such line that it finds in the requirements of the intent, also a
  line that intake wrote. Each value that the intent does not give is a question, or an
  `(assumed)` default.
- The words of the intent bind ("Spec patches"): each example is a line, exactly.
- Where the requirement says how something looks, a line gives the exact text and where
  the user sees it. Other lines do the same for each edge value: zero, empty, or an
  integer.
- A limit has lines just inside and just outside it (59:59 and 60:00 for one hour).
- Each input that the requirement reads has lines for each bad form: missing, empty, the
  wrong type, and too large. An input is an argument, a field, a request, or a stored file. Stored data
  also has unreadable, and written by an older version.
- The "then" of a bad-input line is a coded refusal, or a stated default for an older
  record. A crash, a hang, a stack trace, or a silent empty, zero, or null is wrong.
- A capability that reads an input for every job holds those lines one time.
- Each line checks one behaviour. Its "then" is what a caller sees (a reply, an output, a
  sent message), not a stored row.
- Each failure line names its error code, and `DES-errors` has the code. This is also true
  for an error that the app gives today. A new code goes into `DES-errors` as part of this
  intent.
- An "Interface" entry does not make a line exact. Each line still gives its own exact
  output and code.
- Each rule that a sentence states has a line, also each `(assumed)` detail. A rule with no
  line has no check, so nothing enforces it.
- Words like "fast", "easy", or "secure" have a number or a rule behind them.
- Each capability and design spec that the requirement relies on exists, or is part of this
  intent.
- The lines of a capability use only its own interface, or jobs that are built already.
  They do not use a job that this intent adds or changes. That job comes in a later
  change, so it does not exist when the checks of the capability run.

### Questions and defaults

- Each item to settle is a question for the user.
- With `defaults`, ready takes its recommended answer, marked `(assumed)`. The handoff
  lists the items. Nobody builds an item that ready omits, unless the user approves the
  item.
- The recommended answer is the plain reading of the words of the intent, for each value.
  It does not keep the old behaviour where the plain words change it. It does not change
  the result of an example in the intent. The order of two errors also comes from the
  words of the intent, not from the order of the checks in the code.

### Contradictions

- Ready compares the requirements with each other, with the other requirements of their
  specs, and with the specs that they rely on. A contradiction is two statements that
  cannot both be true: "responds within 50 ms" and "always calls a service that takes
  200 ms".
- Two cases are not contradictions. Ready fixes each one, adds a line to "Notes", and
  continues:
  - The newest words win ("Spec patches"). The older requirement changes, and the intent
    lists it as `changed`.
  - A guess gives way. When one side is `(assumed)`, that side changes to agree with the
    other side. It keeps its mark, and its line in "Notes" changes.
- Ready shows each other contradiction, and asks the user which statement to change. Ready
  does not select for the user, also with `defaults`. Both requirements stay `proposed`.

### Old wording

- When ready changes what a requirement does, ready searches `pdlc/specs/` and the README
  for the old words. Ready changes each sentence, example, and summary in `pdlc/specs/`
  that still shows them. For each README line that shows them, ready adds
  `README: "<old line>" → <requirement>` to the intent "Notes" ("No old wording" in
  `pdlc/README.md`).
- When ready decides which of two errors comes first, the sentence of each requirement that
  gives one of the two errors names the exception.

### Before the commit

- Ready runs `python3 pdlc/bin/check_handoff.py IN-xxxx --stage ready`, and fixes each
  problem that the script names. Then ready runs the script again. If the script still
  fails after three runs, ready puts the problems under "Open", stops with `ready → user`,
  and commits. The handoff title is `ready → change`, or `ready → user` at a stop.
- Each `(assumed)` mark that ready writes, or whose sentence ready changes, has its line in
  "Decided on defaults" and in the intent "Notes".

## Inputs

- `pdlc/README.md`, the shared rules.
- The intent, its "Handoff", and each `proposed` or `retiring` requirement that its
  "Requirements" lists.
- The specs that hold these requirements, the specs that they rely on, and `DES-errors`.

## Outputs

- Each answer in its requirement. A default answer has the mark `(assumed)` there, and the
  line `<requirement>: <question> → <answer> (assumed)` in the intent "Notes".
- Each clear requirement goes from `proposed` to `ready`. A `retiring` requirement stays as
  it is.
- The intent is `ready` when each of its requirements is `ready` or `retiring`.
- The handoff `ready → change`, or `ready → user` at a stop: the decisions, and what helps the plan. "Decided on
  defaults" holds each `(assumed)` line that ready adds or changes in the "Notes", with the
  same words, as the template says.
- The commit "Ready IN-xxxx: <name>" with the trailer `Intent`. Ready commits also when it
  stops for a contradiction. Keep the trailers in one block, as README "Commits" says.
- For the user: what changed, and that `/pdlc:change` is next. After a contradiction, the
  two statements, and the fact that both requirements stay `proposed`.

### Done when

- Each requirement of the intent is `ready` or `retiring`, or the run stopped at a
  contradiction that the user must settle.
- No acceptance line is vague, and no spec text shows old wording.
- `check_handoff.py` exits 0, or the run stopped after three failed runs with the problems
  under "Open". The commit exists.
