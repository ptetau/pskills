---
name: change
description: >
  Turns a ready pdlc intent into one or more change specs. Each change covers exactly one
  job, one capability, or one design spec. Its change spec lists the interface its checks
  may call and the only files it may touch. Capability changes come before the jobs that
  need them. Use when the user says "/pdlc:change", or wants to plan the work for a ready
  intent.
---

# pdlc change

Splits a ready intent into changes and writes a change spec for each.

Read `pdlc/README.md` first and follow it. Start with its "Before any work" step. Then
read the intent's "Handoff".

## 1. Gather

Read the intent the user named. If the user named none, take the oldest intent with status
`ready`. If the intent isn't `ready`, stop and say `/pdlc:ready` comes first. If the
intent has a `Branch:`, switch to that branch. Commit there.

Read:

- every requirement the intent lists;
- the specs those requirements sit in, and the specs those specs rely on;
- the code in the code maps of all those specs.

## 2. Split

Group the requirements by the spec they belong to. Each group is one change. A change
never covers two specs.

Order the changes: design specs first, then capabilities, then jobs. If one capability
relies on another, put the change for the capability relied on first.

## 3. Write each change spec

Take the next free change number. Create the folder `pdlc/changes/CH-xxxx-<short-name>/`.
Write `change.md` in that folder from `pdlc/templates/change.md`.

- **Header:** the intent, the one spec it covers as `Scope`, `Status: planned`, the intent's
  ticket, `Branch: none`, and `Base: main`. The tests skill sets the real base when it
  starts the branch.
- **Requirements:** copy each requirement's heading and acceptance lines, in number
  order, and nothing else. If a requirement is `retiring`, add ` (retire)` to its heading.
- **Relies on:** for a job change, the capabilities it uses, marked "used, not changed".
  Always list the design specs that apply, including `DES-writing-style`,
  `DES-pdlc-check-tagging` and `DES-errors`.
- **Interface:** what the checks may call. The test writer never sees the code. So the
  interface must hold enough to write every check: function names and arguments, commands
  and flags, routes, page elements and what they show. For each entry, give:
  - the file it lives in;
  - what goes in and what comes out, with types where the language has them;
  - every error it can give, by its code in `DES-errors`.

  If an acceptance line's "when" is something the user does (clicks, runs a command,
  sends a request), list that surface. Checks then drive that surface, not only a helper
  below it. Decide new names here, in the code's existing style. Mark each new name
  `(assumed)`.
- **Test seams:** how a check controls what an acceptance line depends on. Seams cover
  the clock (for any line that depends on the current date or time), randomness, and
  outside vendors or stores. Give each seam at the outermost interface the checks call.
  That way, a check of the user's surface can reach the seam. For a command, the seam is an
  environment variable or a flag, and the README names it. Never give a seam only as an
  argument deep inside.

  If the check runner can't drive the user's surface itself (a page, with no browser in
  the runner), the seam is a stand-in. The stand-in loads the real page and its script
  into a stub page with the same element ids and standard properties. It stubs only the
  network. Then it acts as the user and reads what shows. Write "none" only when no line
  needs a seam.
- **Files:** only the app files this change needs, from the spec's code map. List a
  shared file with this spec's parts, as the spec's code map names them. The change edits
  only those parts (see "Code maps" in `pdlc/README.md`). A job change never lists a
  capability's files or parts.

  If a job's entry point sits in a capability's code map, move the entry point to the
  job's map as a part. Note the move in the intent's "Notes". Then go on planning. Never
  stop for this.

  A job change always lists the project's README. Another change lists the README if the
  change alters what the README tells a user. If `.gitignore` lacks the folders the checks
  will write, list `.gitignore` too.
- **Check files:** the check files this change adds or changes, inside the check folders
  in `pdlc/config.md`. Name a new check file after the spec, as `DES-pdlc-check-tagging`
  says.
- **Steps:** usually one per requirement. Each step names its requirement, the check that
  proves it (named with the requirement ID), and "Done when". A `(retire)` requirement
  gets no check. Its step removes the code and checks that only served it. If "Files"
  lists a README, add a last step for the README. That step is done when the README:
  - describes what this change adds;
  - no longer shows anything the change removes or changes (including each `README:`
    line in the intent's "Notes" for these requirements);
  - names any seam a user can set;
  - says how to run the app and the checks, with the "all" command from `pdlc/config.md`.
- **Manual checks:** only what no check can see, such as how a page looks, or "none". One
  line each, in the template's form. Its step's "Check" says `manual check`. A missing
  runner or tool is never a reason for a manual check, and never a reason to stop. Use a
  stand-in seam instead.

## 4. Finish

- In the intent's "Changes" section, list the changes in order.
- Write the intent's "Handoff" for the tests stage. Give the changes, their order, and
  anything about the interface the test writer should know.
- Commit with the message "Plan IN-xxxx: <names of changes>" and the trailer
  `Intent: IN-xxxx`.
- Tell the tracker port about each new change.
- Tell the user the changes, in order, and that `/pdlc:tests` is next.
