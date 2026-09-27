---
name: change
description: >
  Turns a ready pdlc intent into one or more change specs. Each change covers exactly one
  job, one capability, or one design spec, and lists only the files it may touch.
  Capability changes come before the jobs that need them. Use when the user says
  "/pdlc:change", or wants to plan the work for a ready intent.
---

# pdlc change

Splits a ready intent into changes and writes a change spec for each.

Read `pdlc/README.md` first and follow it. Start with its "Before any work" step.

## 1. Gather

Read the intent. If none was named, take the oldest intent with status `ready`. If it
isn't `ready`, stop and say `/pdlc:ready` comes first.

Read every requirement it lists, the specs they sit in, and the specs those rely on.

## 2. Split

Group the requirements by the spec they belong to. Each group is one change. A change
never covers two specs.

Order the changes: design specs first, then capabilities, then jobs. If one capability
relies on another, the one relied on goes first.

## 3. Write each change spec

Use `pdlc/templates/change.md`. Take the next free change number. Name the file
`pdlc/changes/CH-xxxx-<short-name>.md`.

- **Header:** the intent, the one spec it covers as `Scope`, `Status: planned`, the intent's
  ticket, and `Branch: none`.
- **Requirements:** copy each requirement's heading and acceptance checks. Add ` (retire)`
  to the heading of any requirement that is `retiring`.
- **Relies on:** for a job change, the capabilities it uses, marked "used, not changed".
  Always list the design specs that apply, including `DES-writing-style` and
  `DES-pdlc-check-tagging`.
- **Files:** only the files this change needs. Start from the spec's code map. For a new
  file, put it inside the code map's folders. A job change must not list files from a
  capability's code map.
- **Steps:** small steps, usually one per requirement. Each names its requirement, the
  check that proves it (named with the requirement ID), and "Done when".
- **Manual checks:** any acceptance check that can't be automated, or "none".

## 4. Finish

- In the intent's "Changes" section, list the changes in order.
- Commit with the message "Plan IN-xxxx: <names of changes>" and the trailer
  `Intent: IN-xxxx`.
- Tell the tracker port about each new change.
- Tell the user the changes, in order, and that `/pdlc:build` builds the first one.
