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
isn't `ready`, stop and say `/pdlc:ready` comes first.

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
- **Requirements:** copy each requirement's heading and acceptance checks. Add ` (retire)`
  to the heading of any requirement that is `retiring`.
- **Relies on:** for a job change, the capabilities it uses, marked "used, not changed".
  Always list the design specs that apply, including `DES-writing-style`,
  `DES-pdlc-check-tagging` and `DES-errors`.
- **Interface:** what the checks may call. The test writer never sees the code, so this
  must be enough to write every check: function names and arguments, commands and flags,
  routes, page elements and what they show. For each entry give the file it lives in,
  what goes in and what comes out (with types where the language has them), and every
  error it can give, by its code in `DES-errors`. Under "Test seams", say how a check
  controls the clock, randomness and outside vendors or stores, or write "none". Decide
  new names here, following the code's existing style, and mark each new name
  *(assumed)*.
- **Files:** only the app files this change needs. Start from the spec's code map. A job
  change must not list files from a capability's code map.
- **Check files:** the check files this change adds or changes, inside the check folders
  in `pdlc/config.md`.
- **Steps:** usually one per requirement. Each names its requirement, the check that
  proves it (named with the requirement ID), and "Done when". A `(retire)` requirement
  gets no check: its step removes the code and checks that only served it.
- **Manual checks:** any acceptance check that can't be automated, or "none". If one could
  be automated but the project has no check runner that can reach it (for example page
  behaviour with no browser checks), add an intent through the inbox port to add such a
  runner, unless the inbox already has one, and say so in the handoff.

## 4. Finish

- In the intent's "Changes" section, list the changes in order.
- Write the intent's "Handoff" for the tests stage: the changes, their order, and anything
  about the interface the test writer should know.
- Commit with the message "Plan IN-xxxx: <names of changes>" and the trailer
  `Intent: IN-xxxx`.
- Tell the tracker port about each new change.
- Tell the user the changes, in order, and that `/pdlc:tests` is next.
