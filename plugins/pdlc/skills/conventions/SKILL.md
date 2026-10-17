---
name: conventions
description: >
  Makes or changes a pdlc convention together with the user. Writes the agreed convention
  as a design spec. When an existing convention changes, adds one migration intent for
  each job or capability that the change has an effect on. Use when the user says
  "/pdlc:conventions", or wants to set or change how the project does a thing everywhere.
  Also use when a different pdlc skill finds a missing convention.
---

# pdlc conventions

This skill keeps the software consistent. The skill writes each convention, and gets the
agreement of the user for each convention. The skill does not change a convention before
it asks the user.

Read `pdlc/README.md` first. Obey the instructions in that file, and start with its
"Before any work" step.

## 1. Tell the user what to decide

In one or two sentences, tell the user the subject of the convention, and why the
convention is important now. For example: "This is the first table in the app. How do you
want tables to sort and page?"

## 2. Give options

Examine the code to find the current method for the subject of the convention. Give two
or three options. For each option, give a short real example from this project, if one
exists. Mark the option that you recommend, and give one line about the reason. Obey
"Asking questions" in `pdlc/README.md`. With `defaults`, use the recommended option, and
do not ask the user.

## 3. Write the convention

- **New convention:** make `pdlc/specs/design/DES-<name>.md` from the design template.
- **Changed convention:** edit the design spec. If the design spec was a default, set
  `Default: no`.

If a check can examine the convention (for example, a lint rule), add requirements for
the convention. Mark the requirements `proposed`. Add an intent to build the check.

## 4. Add the migration intents

Find the jobs and capabilities whose code does not obey the agreed convention. Such code
occurs when a convention changes. Such code also occurs when a new convention records a
thing that the code does in more than one way. Search the code maps.

For each job or capability that you find, add an intent through the inbox port:

- Name: "Migrate <spec> to <convention>".
- What and why: what changed, and a link to the design spec.

Do not start these intents. Tell the user how many intents you added. The user selects
when each intent runs.

## 5. Finish

Commit with the message "Convention DES-<name>" and, if a different skill sent you here,
the `Intent` trailer of that skill.

Then, if a different skill sent you here, go back to that skill.
