---
name: conventions
description: >
  Makes or changes a pdlc convention together with the user, and writes it as a design
  spec. When an existing convention changes, adds one migration intent for each job or
  capability that the change has an effect on. Use when the user says
  "/pdlc:conventions", or wants to set or change how the project does a thing everywhere.
  Also use when a different pdlc skill finds a missing convention.
---

# pdlc conventions

## Goal

Conventions keeps the software consistent. Each convention is a design spec that the user
agreed, and the code that does not obey it gets a migration intent.

## Constraints

- The rules of `pdlc/README.md` hold, and "Bookkeeping on main" runs first. Each question
  obeys "Questions".
- No convention changes before the user agrees.
- The user first hears the subject of the convention, and why it is important now, in one
  or two sentences. For example: "This is the first table in the app. How do you want
  tables to sort and page?"
- The two or three options come from the current method in the code. Each option has a
  short real example from this project, when one exists. The recommended option has one
  line on why. With `defaults`, the skill takes it and does not ask.
- A new convention is `pdlc/specs/design/DES-<name>.md` from the design template. A
  changed convention edits its design spec, and a default gets `Default: no`.
- A convention that a check can examine (for example, a lint rule) gets `proposed`
  requirements, and an intent to build the check.
- Code that does not obey the agreed convention occurs when a convention changes. It also
  occurs when a new convention records a thing that the code does in more than one way.
  The skill finds each such job and capability through the code maps.
- Each such job or capability gets an intent through the inbox port. Its name is
  "Migrate <spec> to <convention>". Its "What and why" gives what changed, and a link to
  the design spec.
- The skill does not start these intents. The user selects when each one runs.

## Inputs

- `pdlc/README.md`, the specs and their code maps, and the code.
- The subject of the convention, from the user or from the skill that sent the work here.
- The design template in `pdlc/templates/`.

## Outputs

- The new or changed design spec, and each migration intent.
- The commit "Convention DES-<name>". When a different skill sent the work here, the
  commit has the `Intent` trailer of that skill.
- For the user: how many migration intents the skill added.
- When a different skill sent the work here, that skill continues.
