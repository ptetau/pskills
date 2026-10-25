---
name: change
description: >
  Makes one or more change specs from a ready pdlc intent. Each change covers exactly one
  job, one capability, or one design spec. Each change lists the interface that its checks
  are permitted to call, and lists only the files that the change is permitted to touch.
  A change comes after the changes that it needs, and capability changes come before the
  jobs that need them. Use when the user says
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
stop. If the intent has a `Branch:`, switch to that branch. Commit on that branch.

Read every requirement that the intent lists. Then read the specs that hold the
requirements, and the specs that those specs rely on. Then read the code in their code
maps.

## 2. Divide the intent into changes

Put the requirements into groups by the spec that each requirement is in. Each group is
one change. A change must not cover two specs.

Put the changes in the order of what each change needs. A change whose acceptance lines
use the interface or the output of a second change comes after that second change. For
example, a line of `JOB-pay-invoice` (pay an invoice) says "then `invoices` shows invoice 7
as paid". That line uses the `invoices` command. Thus, the change that builds `invoices`
comes first.

Where that rule gives no order, put design specs first, then capabilities, then jobs. If a
capability relies on a second capability, put the second capability first.

## 3. Write each change spec

Use the next free change number. Make the folder `pdlc/changes/CH-xxxx-<short-name>/`.
In that folder, write `change.md` from `pdlc/templates/change.md`.

- **Header:** the intent, the one spec that the change covers as `Scope`,
  `Status: planned`, the ticket of the intent, `Branch: none`, and `Base: main`. The tests
  skill sets the real base when it starts the branch.
- **Requirements:** copy the heading and the acceptance lines of each requirement, in
  number order. Copy nothing else. If a requirement is `retiring`, add ` (retire)` to its
  heading.
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

  If the "when" part of an acceptance line is something that the user does (a click, a
  command, or a request), list that surface. Then the checks drive that surface, and not
  only a helper below the surface. Select the new names here. Use the style of the existing
  code, and mark each new name `(assumed)`.
- **Test seams:** how a check controls what an acceptance line depends on. A seam can
  control the clock (for any line that depends on the current date or time), randomness,
  and external vendors or stores. Give each seam at the outermost interface that the checks
  call. Then a check of the user's surface can reach the seam. For a command, the seam is
  an environment variable or a flag, and the README names the seam. Do not give a seam only
  as an argument deep inside the code.

  The check runner can be unable to drive the user's surface itself. For example, the
  surface is a page, and the runner has no browser. Then the seam is a stand-in. Do these
  steps:
  1. Load the real page and its script into a stub page. The stub page has the same
     element IDs and standard properties.
  2. Stub only the network.
  3. Act as the user, and read what shows.

  Write "none" only if no acceptance line needs a seam.
- **Files:** only the app files that this change needs. Start from the code map of the
  spec. List a shared file with the parts of this spec, as the code map names them. The
  change edits only those parts (see "Code maps" in `pdlc/README.md`). A job change must
  not list the files or the parts of a capability.

  A capability map can hold an entry point of a job. Then move the entry point to the job
  map, as a part. Write a note about the move in the "Notes" of the intent. Then continue
  to plan. Do not stop for this.

  A job change always lists the README of the project. Another change lists the README if
  the change alters what the README tells a user. If `.gitignore` lacks the folders that
  the checks will write, list `.gitignore` too.
- **Check files:** the check files that this change adds or changes. These files are in
  the check folders that `pdlc/config.md` gives. Name a new check file after the spec, as
  `DES-pdlc-check-tagging` says.
- **Steps:** usually one step for each requirement. Each step gives its requirement, the
  check that proves the requirement (with the requirement ID in its name), and "Done
  when". A `(retire)` requirement gets no check. The step for a `(retire)` requirement
  removes the code and the checks that were only for that requirement.

  If "Files" lists the README, add a last step for the README. In that step, "Done when"
  gives all of these conditions:
  - The README tells what this change adds.
  - The README no longer shows anything that the change removes or changes. This includes
    each `README:` line in the "Notes" of the intent for these requirements.
  - The README names any seam that a user can set.
  - The README says how to run the app and the checks, with the "all" command from
    `pdlc/config.md`.
- **Manual checks:** only what no check can see, such as how a page looks, or "none".
  Write one line for each manual check, in the form of the template. The "Check" of its
  step says `manual check`. A missing runner or tool is not a reason for a manual check.
  It is also not a reason to stop. Use a stand-in seam instead.

## 4. Finish

- In the "Changes" section of the intent, list the changes in order.
- Write the "Handoff" section of the intent for the tests stage. Give the changes, their
  order, and anything about the interface that helps the test writer.
- Commit with the message "Plan IN-xxxx: <names of changes>" and the trailer
  `Intent: IN-xxxx`.
- Tell the tracker port about each new change.
- Tell the user the changes, in order. Also tell the user that `/pdlc:tests` is the next
  step.
