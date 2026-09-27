---
name: conventions
description: >
  Establishes or changes a pdlc convention with the user. Writes the agreed convention as a
  design spec, and when an existing convention changes, files one migration intent per
  affected job or capability. Use when the user says "/pdlc:conventions", wants to set or
  change how something is done across the project, or another pdlc skill finds a missing
  convention.
---

# pdlc conventions

Keeps the software consistent by writing conventions down and agreeing them with the user.
Never changes a convention without asking.

Read `pdlc/README.md` first and follow it.

## 1. Say what needs deciding

In one or two sentences: what the convention is about, and why it matters now. For
example: "This is the first table in the app. How should tables sort and page?"

## 2. Offer options

Look in the code for how it is done today. Offer two or three options, each with a short
real example from this project where one exists. Mark the one you recommend, with one line
on why. The user can reply `skip` to take the recommendation.

## 3. Write it down

- **New convention:** create `pdlc/specs/design/DES-<name>.md` from the design template.
- **Changed convention:** edit the design spec. Set `Default: no` if it was a default.

If the convention can be checked (for example by a lint rule), add requirements for it,
marked `proposed`, and file an intent to build the check.

## 4. File migrations

Only when an existing convention changed. Find the jobs and capabilities whose code
follows the old convention. Search the code maps for it.

For each one, add an intent through the inbox port:

- Name: "Migrate <spec> to <convention>".
- What and why: what changed, and a link to the design spec.

Don't start them. Tell the user how many you filed. They choose when each one runs.

## 5. Finish

Commit with the message "Convention DES-<name>" and, if another skill sent you here, that
skill's `Intent` trailer. Then go back to that skill if there was one.
