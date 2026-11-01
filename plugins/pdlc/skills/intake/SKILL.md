---
name: intake
description: >
  Takes one intent into pdlc, and makes spec patches from it: new jobs, new capabilities,
  new conventions, or changes to existing specs. Marks each new requirement as proposed.
  Does not write code. Use when the user says "/pdlc:intake", or tells you about
  something to build or change in a pdlc project. Also use when the user names an intent
  in the inbox to specify.
---

# pdlc intake

## Goal

Intake turns one intent into spec patches. Each requirement that the intent needs is in
its right spec, as `proposed`. Intake does not write code.

## Constraints

- The session model is a Sonnet 5.5 class model or above ("Core rules" in
  `pdlc/README.md`). On a lower model, intake does no work. Intake tells the user that
  pdlc needs a Sonnet 5.5 class model or above.
- The rules of `pdlc/README.md` hold, and "Bookkeeping on main" runs first.
- When a pdlc branch is unmerged, intake reads the inbox and the specs on the newest one
  ("Where pdlc commits"). The intent then gets its own branch from there, through the
  delivery port, before the first commit. `Branch:` names it.
- With no unmerged pdlc branch, intake commits on main, and the intent keeps
  `Branch: none`.
- The intent comes from the first of these sources that applies, in this order:
  - New words of the user: a new intent from the inbox port, with those words as
    "What and why". The user gets its ID.
  - An intent that the user names. The name is the approval, so an `Awaits approval:`
    line in its "Notes" goes.
  - A `.blueprint.md` file that the user names, read as the words of the intent. Its
    scope gives "What and why". Its other sections give the requirements, the error
    codes, and the signatures. Each signature becomes an entry in the "Interface" of its
    spec. Each `(assumed)` mark stays. After intake, the pdlc specs
    lead, and nobody changes the file.
  - The oldest `new` intent with no `Awaits approval:`.
- Each patch obeys "Spec patches" (where a behaviour belongs, the words of the intent, the
  newest words, no old wording) and "Questions" (the `(assumed)` mark).
- Intake writes directly into the spec files. A new spec comes from `pdlc/templates/`.
- A new requirement has the next free number in its spec, `Status: proposed`, and this
  intent in `Intents:`. It has one or two plain sentences, then "Given …, when …, then …"
  lines.
- Each new or changed requirement gets the "Interface" entries that its acceptance lines
  name, in the same spec ("Interfaces" in `pdlc/README.md`). A job gets what its user
  touches. A capability gets the calls that jobs use.
- Each new entry ends its first line with ` · proposed`. Each name that the intent does
  not give has the mark `(assumed)`.
- Each entry gives each error of the lines that use it, one error on each line. An error
  line has the code, the exact message, and the result. A command error also gives `stderr`
  or `stdout`, the stream that gets the message ("Interfaces" in `pdlc/README.md`).
  Test seams go under "Test seams".
- Each failure acceptance line gives the exact message and the result (exit code or status)
  from the words of the user, not "the error".
- An error that the app gives today, with no code in `DES-errors`, gets `no code` and its
  exact message and result. If no line of this intent uses that error, intake makes no code
  for it.
- A new code that intake makes has the mark `(assumed)` in its `DES-errors` row and in each
  entry that names it.
- A spec with no "Interface" section gets one from its template, before "Requirements".
- Each detail that the words of the intent do not give (a message, a limit, an order, a
  format) has the mark `(assumed)` where intake writes it.
- A detail that intake adds to a `built` requirement from recon also has the mark `(assumed)`.
- "Decided on defaults" in the handoff lists each `(assumed)` decision that intake wrote, one line
  for each, in the form of the template. The same lines go into the intent "Notes".
- Before the commit, intake runs `python3 pdlc/bin/check_handoff.py IN-xxxx --stage intake`,
  and fixes each problem that the script names. Then intake runs the script again. If the
  script still fails after three runs, intake puts the problems under "Open", stops with
  `intake → user`, and commits.
- An `(assumed)` detail adds to the words of the intent. It does not remove a value that
  the plain reading of those words permits. For example, "a whole number greater than
  zero" also permits `+3`, so an assumed rule such as "digits only" is not correct.
- A changed requirement changes in place, with `Status: proposed`, and this intent added
  to `Intents:`. A removed requirement gets `Status: retiring`, and this intent too.
- An "Interface" entry that only a `retiring` requirement uses gets ` · retiring` at
  the end of its first line.
- Each changed requirement gets the Note `<ID>: was "<old>", now "<new>"` in the intent.
  This rule is for each reason of the change, not only for "The newest words win".
- A new job lists the capabilities and the design specs that it relies on.
- The summary of a spec ("Who and why" in a job, "What it is for" in a capability) shows
  each requirement that intake adds, in one short sentence, for example the new option of
  a command. The specification review fails a summary that does not.
- Intake finds every requirement that the newest words change. For example, a new format
  changes every example of the old format.
- A spec with `Status: stub` first gets a deep look from `pdlc:recon`. Recon gets three
  items only: the project root, the absolute path of the spec, and the words `deep look`.
  Recon gets no request for a summary, the template, or extra detail.
- The requirements from recon go into the spec as `built`, with `Source: recon`. The
  "Interface" entries from recon go into the spec with no mark and no `Seen in` line.
  Then the spec becomes `Status: active`.
- The statuses on main can be out of date. Thus, intake lists the change branches first
  ("Where pdlc commits"). The handoff names each changed requirement that an unmerged
  change covers. The change of this intent for that spec stacks after the unmerged change.
- A requirement that is still `proposed` for another open intent is a question: how do
  the two intents fit? With `defaults`, this intent wins where they differ, and its changes
  come after the changes of the other intent.
- An intent with two possible meanings is a question before intake goes on. With
  `defaults`, intake takes the more likely meaning, marks the detail `(assumed)` in the
  spec, and writes the Note `<ID>: <question> → <answer> (assumed)`. Only two possible
  meanings make a point a question for ready.

## Inputs

- `pdlc/README.md`, the shared rules.
- The words of the user, an intent ID, or a `.blueprint.md` file.
- The inbox, `pdlc/specs/`, the README of the project, and `pdlc/templates/`.
- The change branches and their change specs.

## Outputs

- The patched specs, and each new spec.
- In the intent:
  - `Status: specifying`.
  - "Requirements": each requirement whose text intake touched, with one word for each:
    added, changed, or retiring. A `built` requirement from recon is not listed,
    unless intake changed its text (for example with an `(assumed)` detail). Then it is
    listed as changed.
  - The "Notes" lines of "Spec patches".
  - The handoff `intake → ready`: what intake wrote, what it assumed, and what looks
    unclear.
- The commit "Specify IN-xxxx: <name>" with the trailer `Intent`: the specs and the
  intent. Intake commits also when it stops early. The commit comes after `check_handoff.py`
  exits 0.
- For the user: what intake wrote, and that `/pdlc:ready` is next.
- Intake is done when the commit holds each requirement that the intent needs.
