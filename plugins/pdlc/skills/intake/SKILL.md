---
name: intake
description: >
  Takes one intent into pdlc and makes spec patches from it: new jobs, new capabilities,
  new conventions, or changes to existing specs. Marks each new requirement as proposed.
  Does not write code. Use when the user says "/pdlc:intake", or tells you about
  something to build or change in a pdlc project. Also use when the user names an intent
  in the inbox to specify.
---

# pdlc intake

Intake makes changes to the specs from an intent. Intake does not write code.

Read `pdlc/README.md` first, and follow its instructions. Start with its "Before any
work" step.

## 1. Get the intent

- If the user described something new, add it through the inbox port. Use the words of
  the user for "What and why". Tell the user the ID of the new intent.
- If the user named an intent, read that intent.
- If neither is true, take the oldest intent with status `new`.

Set the status of the intent to `specifying`.

## 2. Decide what it touches

Read the specs in `pdlc/specs/`. For each thing that the intent needs, decide where the
thing belongs:

- What a user does → a **job** spec.
- What the system can do, for use by jobs → a **capability** spec.
- How we do something in all places → a **design** spec.

Prefer an existing spec. Create a new spec only when no spec fits. When you create a
capability, put its boundary around a thing that is likely to change (a vendor, a set of
rules, a store). Name the capability for that thing, not for a feature: `CAP-payments`,
not `CAP-checkout-button`.

If the intent has two possible meanings, ask the user before you continue (see "Asking
questions" in `pdlc/README.md`). With `defaults`, take the more likely meaning, and write
a note about it.

## 3. Deepen stub specs

If a spec that you will change says `Status: stub`, start the `pdlc:recon` agent. Ask
recon for a **deep look** at the code map of that spec. Write the requirements from recon
into the spec. These requirements come back as `built`, with `Source: recon`. Set the
spec to `Status: active`.

## 4. Write the patches

Write directly into the spec files. For a new spec, use `pdlc/templates/`.

- **New requirement:** use the next free number in that spec. Set `Status: proposed`, and
  set `Intents:` to this intent. Write one or two plain sentences. Then write the
  acceptance checks as "Given …, when …, then …" lines.
- **Changed requirement:** edit the requirement in place. Set `Status: proposed`. Add this
  intent to `Intents:`.
- **Removed requirement:** set `Status: retiring`, and add this intent to `Intents:`.
- **New job:** list the capabilities and the design specs that the job relies on.

If a requirement that you must change is already `proposed` for a different intent, and
that intent is not done, stop. Ask the user how to fit the two intents together.

## 5. Record and finish

1. In the "Requirements" section of the intent, list each requirement that you added,
   changed, or retired. Give one word for each requirement: added, changed, or retiring.
2. Write the "Handoff" of the intent for ready (see `pdlc/templates/handoff.md`): what you
   wrote, what you assumed, and what looks unclear.
3. Commit the spec and intent files with the message "Specify IN-xxxx: <name>" and the
   trailer `Intent: IN-xxxx`.
4. Tell the tracker port.
5. Tell the user what you wrote, and that `/pdlc:ready` is next.
