---
name: change
description: >
  Turns a ready pdlc intent into one or more change specs. Each change covers exactly one
  job, one capability, or one design spec, lists the interface its checks may call, and
  lists only the files it may touch. Capability changes come before the jobs that need
  them. Use when the user says "/pdlc:change", or wants to plan the work for a ready
  intent.
---

# pdlc change

Splits a ready intent into changes and writes a change spec for each.

Read `pdlc/README.md` first and follow it. Start with its "Before any work" step, then read
the intent's "Handoff".

## 1. Gather

Read the intent. If none was named, take the oldest intent with status `ready`. If it
isn't `ready`, stop and say `/pdlc:ready` comes first. If it has a `Branch:`, switch to
it and commit there.

Read every requirement it lists, the specs they sit in, the specs those rely on, and the
code in their code maps.

## 2. Split

Group the requirements by the spec they belong to. Each group is one change. A change
never covers two specs.

Order the changes: design specs first, then capabilities, then jobs. If one capability
relies on another, the one relied on goes first.

## 3. Write each change spec

Take the next free change number. Create the folder `pdlc/changes/CH-xxxx-<short-name>/`
and write `change.md` in it from `pdlc/templates/change.md`.

- **Header:** the intent, the one spec it covers as `Scope`, `Status: planned`, the intent's
  ticket, `Branch: none`, and `Base: main`. The tests skill sets the real base when the
  branch is started.
- **Requirements:** copy each requirement's heading and acceptance lines, in number
  order, and nothing else. Add ` (retire)` to the heading of any requirement that is
  `retiring`.
- **Relies on:** for a job change, the capabilities it uses, marked "used, not changed".
  Always list the design specs that apply, including `DES-writing-style`,
  `DES-pdlc-check-tagging` and `DES-errors`.
- **Interface:** what the checks may call. The test writer never sees the code, so this
  must be enough to write every check: function names and arguments, commands and flags,
  routes, page elements and what they show. For each entry give the file it lives in,
  what goes in and what comes out (with types where the language has them), and every
  error it can give, by its code in `DES-errors`. Where a line's "when" is something the
  user does (clicks, runs a command, sends a request), list that surface, so checks
  drive it and not only a helper below it. Decide new names here, following the code's
  existing style, and mark each new name `(assumed)`.
- **Test seams:** how a check controls what a line depends on: the clock (for any line
  that depends on the current date or time), randomness, outside vendors or stores.
  Give each seam at the outermost interface the checks call, so a check of the user's
  surface can reach it: for a command, an environment variable or a flag, which the
  README names; never only an argument deep inside. If the check runner can't drive the
  user's surface itself (a page, with no browser in the runner), the seam is a stand-in:
  load the real page and its script into a stub page with the same element ids and
  standard properties, stub only the network, then act as the user and read what shows.
  Write "none" only when no line needs a seam.
- **Files:** only the app files this change needs, from the spec's code map. List a
  shared file with this spec's parts, as its code map names them; the change edits only
  those parts (see "Code maps" in `pdlc/README.md`). A job change never lists a
  capability's files or parts. If a job's entry point sits in a capability's code map,
  move it to the job's map as a part, note that in the intent's "Notes", and plan on:
  never stop for this. A job change always lists the project's README; another change
  lists it if it alters what the README tells a user. Also list `.gitignore` if it lacks
  the folders the checks will write.
- **Check files:** the check files this change adds or changes, inside the check folders
  in `pdlc/config.md`. A new one is named after the spec, as `DES-pdlc-check-tagging`
  says.
- **Steps:** usually one per requirement. Each names its requirement, the check that
  proves it (named with the requirement ID), and "Done when". A `(retire)` requirement
  gets no check: its step removes the code and checks that only served it. A README in
  "Files" gets a last step. Done when the README describes what this change adds, no
  longer shows anything it removes or changes (including each `README:` line in the
  intent's "Notes" for these requirements), names any seam a user can set, and says how
  to run the app and the checks, with the "all" command from `pdlc/config.md`.
- **Manual checks:** only what no check can see, such as how a page looks, or "none". One
  line each, in the template's form, and its step's "Check" says `manual check`. A
  missing runner or tool is never a reason, and never a stop: use a stand-in seam.

## 4. Finish

- In the intent's "Changes" section, list the changes in order.
- Write the intent's "Handoff" for the tests stage: the changes, their order, and anything
  about the interface the test writer should know.
- Commit with the message "Plan IN-xxxx: <names of changes>" and the trailer
  `Intent: IN-xxxx`.
- Tell the tracker port about each new change.
- Tell the user the changes, in order, and that `/pdlc:tests` is next.
