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

Ready makes each requirement that an intent touches clear, testable, and consistent, and
then marks it `ready`.

## Constraints

- The rules of `pdlc/README.md` hold, and "Bookkeeping on main" runs first. Each patch
  obeys "Spec patches", and each question obeys "Questions".
- The intent is the one that the user names, or else the oldest `specifying` intent. If
  the intent has a `Branch:`, ready works and commits on that branch.
- The behaviour that the intent implies, but does not state, is settled before anything
  is `ready`. The items to examine, where they apply:
  - Bad and empty input. Limits and sizes. Order. What happens to existing data.
  - Unsafe input: sizes, injection, and paths.
  - Business rules that the words leave open: who is permitted to do what, what happens
    twice, and what happens when something is missing.
- Each settled item becomes acceptance lines on the requirement that it belongs to, or a
  new `proposed` requirement in the right spec. The intent lists a new requirement as
  added.
- Each item is a question for the user. With `defaults`, ready takes its recommended
  answer, marked `(assumed)`. The handoff lists the items. Nobody builds an item that
  ready omits, unless the user approves the item.
- The recommended answer is the plain reading of the words of the intent, for each value.
  It does not keep the old behaviour where the plain words change it. It does not change
  the result of an example in the intent. The order of two errors also comes from the
  words of the intent, not from the order of the checks in the code.
- A requirement is clear when all of these are true:
  - The requirement says what must be true, not how to build it.
  - Each acceptance line is "Given …, when …, then …", and a check can prove it with a
    pass or a fail. Each line uses concrete values ("Ana", "80", "15%"), not "a user",
    "some amount", or "any file". Its "then" gives the exact output, not "the same
    error".
  - The words of the intent bind ("Spec patches"): each example is a line, exactly.
  - Where the requirement says how something looks, a line gives the exact text and where
    the user sees it. Other lines do the same for each edge value: zero, empty, or an
    integer.
  - A limit has lines just inside and just outside it (59:59 and 60:00 for one hour).
  - Each input that the requirement reads (an argument, a field, a request, a stored file)
    has lines for each bad form: missing, empty, the wrong type, and too large. Stored
    data also has unreadable, and written by an older version.
  - The "then" of a bad-input line is a coded refusal, or a stated default for an older
    record. A crash, a hang, a stack trace, or a silent empty, zero, or null is wrong.
  - A capability that reads an input for every job holds those lines one time.
  - Each line checks one behaviour. Its "then" is what a caller sees (a reply, an output,
    a sent message), not a stored row.
  - Each failure line names its error code, and `DES-errors` has the code. This is also
    true for an error that the app gives today. A new code goes into `DES-errors` as part
    of this intent.
  - Each "Interface" entry of the spec that a line names lists each error code of the
    lines that use it. Ready does not add a missing entry or a missing "Interface"
    section. The change stage adds it ("Interfaces"). An entry does not make a line exact:
    each line still gives its own exact output and error code.
  - Each rule that a sentence states has a line, also each `(assumed)` detail. A rule with
    no line has no check, so nothing enforces it.
  - Words like "fast", "easy", or "secure" have a number or a rule behind them.
  - Each capability and design spec that the requirement relies on exists, or is part of
    this intent.
  - The lines of a capability use only its own interface, or jobs that are built already.
    They do not use a job that this intent adds or changes. That job comes in a later
    change, so it does not exist when the checks of the capability run.
- A missing design spec (for example, the first table of the project) gets agreed through
  `pdlc:conventions`, and then ready continues.
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

## Inputs

- `pdlc/README.md`, the shared rules.
- The intent, its "Handoff", and each `proposed` or `retiring` requirement that its
  "Requirements" lists.
- The specs that hold these requirements, the specs that they rely on, and `DES-errors`.

## Outputs

- Each answer in its requirement. A default answer has the mark `(assumed)` there, and the
  line `<requirement>: <question> → <answer> (assumed)` in the intent "Notes".
- Each clear requirement goes from `proposed` to `ready`. A `retiring` requirement stays
  as it is.
- The intent is `ready` when each of its requirements is `ready` or `retiring`.
- The handoff `ready → change`: the decisions, and what helps the plan.
- The commit "Ready IN-xxxx: <name>" with the trailer `Intent`. Ready commits also when it
  stops for a contradiction.
- For the user: what changed, and that `/pdlc:change` is next. After a contradiction, the
  two statements, and the fact that both requirements stay `proposed`.
