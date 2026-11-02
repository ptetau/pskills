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

Each convention is a design spec that the user agreed. Code that does not obey it gets a
migration intent.

## Inputs

- `pdlc/README.md`: "Bookkeeping on main", "Questions", "Spec patches", "Commits", "Ports".
- The subject, from the user or the sending skill. The argument `defaults`.
- The specs, code maps, code, and template in `pdlc/templates/`.

## Outputs

- A new `pdlc/specs/design/DES-<name>.md`, or the edited spec. A changed default gets `Default: no`.
- A checkable convention: `proposed` requirements, and one intent to build the check.
- One intent, through the inbox port, for each job or capability that disobeys it: "Migrate <spec> to <convention>". Its "What and why" links the spec.
- The commit "Convention DES-<name>", with the `Intent` trailer of the sending skill.
- The reply: the spec, and the migration intent count.

## Constraints

- Ask first: subject, why now, and two or three options from the code, with real examples, if any. Recommend one.
- Change nothing before the user agrees. Start no intent.
- A new convention that records a thing done in several ways also gets migration intents.

## Done when

Spec and intents are committed. The sending skill continues.
