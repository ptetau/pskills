---
name: conventions
description: >
  Establishes or changes a pdlc convention with the user. Writes the agreed convention as a
  design spec. When an existing convention changes, files one migration intent per
  affected job or capability. Use when the user says "/pdlc:conventions", or wants to set
  or change how something is done across the project. Also use when another pdlc skill
  finds a missing convention.
---

# pdlc conventions

Keeps the software consistent by writing conventions down and agreeing them with the user.
Never changes a convention without asking.

Read `pdlc/README.md` first and follow it. Start with its "Before any work" step.

## 1. Say what needs deciding

Say in one or two sentences what the convention is about, and why it matters now. For
example: "This is the first table in the app. How should tables sort and page?"

## 2. Offer options

Look in the code to see how the project does this today. Offer two or three options, each
with a short real example from this project where one exists. Mark the one you recommend,
with one line on why. Follow "Asking questions" in `pdlc/README.md`. With `defaults`, take
the recommendation without asking.

## 3. Write it down

- **New convention:** create `pdlc/specs/design/DES-<name>.md` from the design template.
- **Changed convention:** edit the design spec. If the convention was a default, set
  `Default: no`.

If a tool can check the convention (for example a lint rule), add requirements for the
convention, marked `proposed`. Then file an intent to build the check.

## 4. File migrations

Search the code maps. Find the jobs and capabilities whose code doesn't follow the
convention as agreed. Such code exists in two cases:

- the convention changed;
- a new convention writes down something the code does in more than one way.

For each job or capability you find, add an intent through the inbox port:

- Name: "Migrate <spec> to <convention>".
- What and why: what changed, and a link to the design spec.

Don't start the migration intents. The user chooses when each one runs. Tell the user how
many you filed.

## 5. Finish

Commit with the message "Convention DES-<name>". If another skill sent you here:

- give the commit that skill's `Intent` trailer;
- after the commit, go back to that skill.
