---
name: change
description: >
  Makes one or more change specs from a ready pdlc intent. Each change covers exactly one
  job, one capability, or one design spec. Each change lists the interface that its checks
  are permitted to call, and lists only the files that the change is permitted to touch.
  Capability changes come before the jobs that need them. Use when the user says
  "/pdlc:change", or wants to plan the work for a ready intent.
---

# pdlc change

This skill divides a ready intent into changes. Then the skill writes a change spec for
each change.

Read `pdlc/README.md` first. Obey the instructions in that file, and start with its
"Before any work" step. Then read the "Handoff" section of the intent.

## 1. Collect the information

Read the intent. If the user did not name an intent, use the oldest intent with the status
`ready`. If the intent is not `ready`, tell the user that `/pdlc:ready` comes first. Then
stop.

Read every requirement that the intent lists. Then read the specs that hold the
requirements, and the specs that those specs rely on. Then read the code in their code
maps.

## 2. Divide the intent into changes

Put the requirements into groups by the spec that each requirement is in. Each group is
one change. A change must not cover two specs.

Put the changes in this order: design specs first, then capabilities, then jobs. If a
capability relies on a second capability, put the second capability first.

## 3. Write each change spec

Use the next free change number. Make the folder `pdlc/changes/CH-xxxx-<short-name>/`.
In that folder, write `change.md` from `pdlc/templates/change.md`.

- **Header:** the intent, the one spec that the change covers as `Scope`,
  `Status: planned`, the ticket of the intent, `Branch: none`, and `Base: main`. The tests
  skill sets the real base when it starts the branch.
- **Requirements:** copy the heading and the acceptance checks of each requirement. If a
  requirement is `retiring`, add ` (retire)` to its heading.
- **Relies on:** for a job change, list the capabilities that the job uses, each with the
  mark "used, not changed". Always list the design specs that apply. These include
  `DES-writing-style`, `DES-pdlc-check-tagging`, and `DES-errors`.
- **Interface:** the items that the checks are permitted to call. The test writer does not
  see the code. Thus, the interface must be sufficient to write each check. Give the function
  names and arguments, the commands and flags, the routes, and the page elements and what
  they show. For each entry, give these items:
  - The file that contains the entry.
  - What goes in and what comes out, with types if the language has types.
  - Each error that the entry can give, by its code in `DES-errors`.

  Under "Test seams", tell how a check controls the clock, randomness, and external
  vendors or stores. If the checks need no seams, write "none". Select the new names here.
  Use the style of the existing code, and mark each new name *(assumed)*.
- **Files:** only the app files that this change needs. Start from the code map of the
  spec. A job change must not list files from the code map of a capability.
- **Check files:** the check files that this change adds or changes. These files are in
  the check folders that `pdlc/config.md` gives.
- **Steps:** usually one step for each requirement. Each step gives its requirement, the
  check that proves the requirement (with the requirement ID in its name), and "Done
  when". A `(retire)` requirement gets no check. The step for a `(retire)` requirement
  removes the code and the checks that were only for that requirement.
- **Manual checks:** each acceptance check that you cannot automate, or "none". Sometimes
  you can automate a check, but no check runner of the project can get to the check. For
  example, the check examines page behaviour, and the project has no browser checks. In
  that condition, do these steps:
  1. Add an intent through the inbox port to add such a runner. If the inbox has such an
     intent, do not add a second one.
  2. Say so in the handoff.

## 4. Finish

- In the "Changes" section of the intent, list the changes in order.
- Write the "Handoff" section of the intent for the tests stage. Give the changes, their
  order, and anything about the interface that helps the test writer.
- Commit with the message "Plan IN-xxxx: <names of changes>" and the trailer
  `Intent: IN-xxxx`.
- Tell the tracker port about each new change.
- Tell the user the changes, in order. Also tell the user that `/pdlc:tests` is the next
  step.
