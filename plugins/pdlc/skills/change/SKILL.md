---
name: change
description: >
  Makes one or more change specs from a ready pdlc intent. Each change covers exactly one
  job, one capability, or one design spec. Each change lists the interface that its
  checks are permitted to call, and only the files that it is permitted to touch.
  Capability changes come before the jobs that need them. Use when the user says
  "/pdlc:change", or wants to plan the work for a ready intent.
---

# pdlc change

## Goal

Change divides a `ready` intent into changes, in the order of what each change needs. Each
change spec is sufficient for the test writer and the builder.

## Constraints

- The rules of `pdlc/README.md` hold, and "Bookkeeping on main" runs first.
- The intent is the one that the user names, or else the oldest `ready` intent. An intent
  that is not `ready` stops the skill, and the user hears that `/pdlc:ready` comes first.
- If the intent has a `Branch:`, change works and commits on that branch.
- Each change holds the requirements of one spec, and does not cover two specs.
- A change whose acceptance lines use the interface or the output of a second change comes
  after that change. For example, a line of `JOB-pay-invoice` (pay an invoice) says "then
  `invoices` shows invoice 7 as paid", so the change that builds `invoices` comes first.
- Where that rule gives no order, design specs come first, then capabilities, then jobs.
  A capability that relies on a second capability comes after it.
- Each change has the next free number, and `pdlc/changes/CH-xxxx-<short-name>/change.md`
  from `pdlc/templates/change.md`, with these sections:
  - Header: the intent, the one spec as `Scope`, `Status: planned`, the ticket of the
    intent, `Branch: none`, and `Base: main`. The tests stage sets the real base.
  - Requirements: the heading and the acceptance lines of each requirement, in number
    order, and nothing else. Each line is a word-for-word copy, also a long line. A
    `retiring` requirement has ` (retire)` after its heading.
  - Relies on: for a job change, each capability that the job uses, marked "used, not
    changed". Always the design specs that apply, with `DES-writing-style`,
    `DES-pdlc-check-tagging`, and `DES-errors`.
  - Interface: what the checks are permitted to call. The test writer does not see the
    code, so the Interface alone is sufficient to write each check. That is functions and
    arguments, commands and flags, routes, and page elements with what they show.
  - Each Interface entry gives its file, what goes in and out (with types where the
    language has them), and each error by its code in `DES-errors`.
  - "In" gives each form of input that an acceptance line uses, for example each place
    where an option can stand. "Out" gives the full result, with its order and the order
    of equal items. Each error gives its exact text, where the text shows, and the exit
    code or status. An error with no code in `DES-errors` also gives these items.
  - When the "when" of a line is a user action (a click, a command, a request), the
    Interface lists that surface. Then the checks drive it, not only a helper below it.
  - A new name follows the style of the existing code, and has the mark `(assumed)`.
  - The Interface holds only items of this change, of earlier changes, and of existing
    code, not of a later change. The component checks call only these items. The
    acceptance checks read the Interface of every change.
  - Test seams: how a check controls the clock (for each line that depends on the date or
    time), randomness, and outside vendors or stores. "None" only when no line needs one.
  - Each seam is at the outermost interface that the checks call, so that a check of the
    surface of the user reaches it. A seam is not only an argument deep in the code. For
    a command, the seam is an environment variable or a flag, and the README names it.
  - When the check runner cannot drive the surface (a page, but no browser), the seam is a
    stand-in. The real page and its script load into a stub page with the same element IDs
    and standard properties. Only the network is a stub. The check acts as the user, and
    reads what shows.
  - Files: only the app files that the change needs, from the code map of its spec. A
    shared file has the parts of this spec, and the change edits only those parts
    ("Code maps"). A job change does not list the files or the parts of a capability.
  - A job entry point in a capability map moves to the job map as a part, with a line in
    the intent "Notes". This move is not a stop.
  - A job change always lists the README of the project. Another change lists it when the
    change alters what the README tells a user. `.gitignore` is in "Files" when it lacks
    the folders that the checks write.
  - Check files: the component check files that the change adds or changes, in the check
    folders of `pdlc/config.md`. A new file has the name of its spec, as
    `DES-pdlc-check-tagging` says. When the intent has one change and no stored-data line
    ("Acceptance checks"), the list is `- none`. Then the "Check" of each step is an
    acceptance check. A stored-data line always gets a component check.
  - Steps: one for each requirement, in number order, with its requirement, the check
    that proves it (with the requirement ID in its name), and "Done when". A `(retire)`
    requirement gets no check. Its step removes the code and the checks that only it used.
  - When "Files" lists the README, the last step is for the README. Its "Check" is
    "none", because the specification review reads the README against "Done when". The
    README is not a manual check. Its "Done when" says
    that the README tells what the change adds. It no longer shows what the change
    removes or changes, also each `README:` line in the intent "Notes" for these
    requirements.
  - That "Done when" also says that the README names each seam that a user can set. It
    tells how to run the app and the checks, with the "all" command of `pdlc/config.md`.
  - Manual checks: only what no check can see, such as how a page looks, or "none". Each
    has one line in the form of the template, and the "Check" of its step is
    `manual check`.
  - A missing runner or tool is not a reason for a manual check, or for a stop. A stand-in
    seam takes its place.

## Inputs

- `pdlc/README.md`, the intent, and its "Handoff".
- Every requirement that the intent lists, their specs, the specs that those specs rely
  on, and the code in their code maps.
- `pdlc/templates/change.md` and `pdlc/config.md`.

## Outputs

- A folder and a `change.md` for each change.
- In the intent: the changes, in order, under "Changes", and a note for each moved entry
  point.
- The handoff `change → acceptance`: the changes, their order, and what about the
  interface helps the test writer.
- The commit "Plan IN-xxxx: <names of changes>" with the trailer `Intent`.
- The tracker port knows each new change.
- For the user: the changes in order, and that `/pdlc:acceptance` is next.
