---
name: intake
description: >
  Takes one intent into pdlc and turns it into spec patches: new jobs, new capabilities,
  new conventions, or changes to existing ones. New requirements are marked proposed.
  Never writes code. Use when the user says "/pdlc:intake", describes something they want
  built or changed in a pdlc project, or names an intent in the inbox to specify.
---

# pdlc intake

Turns an intent into changes to the specs. Never writes code.

Read `pdlc/README.md` first and follow it. Start with its "Before any work" step.

## 1. Get the intent

- If the user described something new, add it through the inbox port. Use their words for
  "What and why". Tell them its ID.
- If they named an intent, read it.
- If neither, take the oldest intent with status `new`.

Set its status to `specifying`.

## 2. Decide what it touches

Read the specs in `pdlc/specs/`. For each thing the intent needs, decide where it belongs:

- What a user does → a **job** spec.
- What the system can do, used by jobs → a **capability** spec.
- How we do something everywhere → a **design** spec.

Prefer existing specs. Create a new one only when nothing fits.

If the intent could mean two different things, ask the user before going on (see "Asking
questions" in `pdlc/README.md`; with `defaults`, take the likelier meaning and note it).

## 3. Deepen stub specs

If a spec you will change says `Status: stub`, start the `pdlc:recon` agent for a **deep
look** at that spec's code map. Write its requirements into the spec (they come back as
`built`, `Source: recon`). Set the spec to `Status: active`.

## 4. Write the patches

Write straight into the spec files, using `pdlc/templates/` for new ones.

- **New requirement:** use the next free number in that spec. Set `Status: proposed` and
  `Intents:` to this intent. Write one or two plain sentences, then acceptance checks as
  "Given …, when …, then …" lines.
- **Changed requirement:** edit it in place. Set `Status: proposed`. Add this intent to
  `Intents:`.
- **Removed requirement:** set `Status: retiring` and add this intent.
- **New job:** list the capabilities and design specs it relies on.

If a requirement you need to change is already `proposed` for another intent that isn't
done, stop and ask the user how the two should fit together.

## 5. Record and finish

- In the intent's "Requirements" section, list every requirement you added, changed or
  retired, with one word for which (added, changed, retiring).
- Write the intent's "Handoff" for ready (see `pdlc/templates/handoff.md`): what you
  wrote, what you assumed, what looks unclear.
- Commit the spec and intent files with the message "Specify IN-xxxx: <name>" and the
  trailer `Intent: IN-xxxx`.
- Tell the tracker port.
- Tell the user what you wrote, and that `/pdlc:ready` is next.
