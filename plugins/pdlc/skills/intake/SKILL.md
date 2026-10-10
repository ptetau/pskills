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

First see where to work ("Where pdlc commits" in `pdlc/README.md`). If a pdlc branch is
unmerged, switch to the newest one, so the inbox and specs you read are current.

- If the user described something new, add it through the inbox port. Use their words for
  "What and why". Tell them its ID.
- If they named an intent, read it. If its "Notes" say `Awaits approval:`, naming it is
  the approval: remove that line.
- If neither, take the oldest intent with status `new` that doesn't await approval.

If you switched to a branch, start the intent's own branch from it now, through the
delivery port, before you commit anything. Write its name as the intent's `Branch:`.
Set the intent's status to `specifying`.

## 2. Decide what it touches

Read the specs in `pdlc/specs/`. For each thing the intent needs, decide where it belongs:

- What a user does → a **job** spec.
- What the system can do, used by jobs → a **capability** spec.
- How we do something everywhere → a **design** spec.
- How something looks to the user (a format, a wording, a layout) → the **job** where
  they see it, even when a capability makes the value. Add it to each place they see
  it (a page, an output, a reply).

Prefer existing specs. Create a new one only when nothing fits. When you create a
capability, draw it around something likely to change (a vendor, a set of rules, a
store) and name it for that, not for a feature: `CAP-payments`, not `CAP-checkout-button`.

If the intent could mean two different things, ask the user before going on (see "Asking
questions" in `pdlc/README.md`; with `defaults`, take the likelier meaning and note it).

## 3. Deepen stub specs

If a spec you will change says `Status: stub`, start the `pdlc:recon` agent for a **deep
look** at that spec's code map. Write its requirements into the spec (they come back as
`built`, `Source: recon`). Set the spec to `Status: active`.

## 4. Write the patches

First list the change branches, as "Where pdlc commits" in `pdlc/README.md` says.
Statuses on main may be stale. Never edit a change spec (`changes/*/change.md`): a change
that hasn't merged keeps what it copied. If you change a requirement that such a change
covers, say so in the handoff; this intent's change for that spec will stack after it.

Write straight into the spec files, using `pdlc/templates/` for new ones.

- **New requirement:** use the next free number in that spec. Set `Status: proposed` and
  `Intents:` to this intent. Write one or two plain sentences, then acceptance checks as
  "Given …, when …, then …" lines. Mark each detail the intent's words don't give (a
  message, a limit, an order, a format) *(assumed)* right where you write it.
- **The intent's own words bind.** Copy every example it gives (an output, a message, a
  value) into an acceptance line, exactly. Read its words plainly, for every value,
  including the edge ones (zero, empty, a whole number). An *(assumed)* reading never
  narrows them to keep the old behaviour.
- **Changed requirement:** edit it in place. Set `Status: proposed`. Add this intent to
  `Intents:`.
- **Removed requirement:** set `Status: retiring` and add this intent.
- **New job:** list the capabilities and design specs it relies on.

**The newest words win.** If the intent asks for something an older requirement or an
*(assumed)* detail rules out, change the older text to match. That is a changed
requirement, not a contradiction. Find every one: a new format changes every
example that shows the old one. Add a Note for each: `<ID>: was "<old>", now "<new>"`.
Only when the intent's words could be read two ways is it a question for ready.

If a requirement you need to change is still `proposed` for another intent that isn't
done, ask the user how the two fit. With `defaults`, this intent wins where they differ,
and its changes come after the other intent's.

## 5. Record and finish

- In the intent's "Requirements" section, list every requirement you added, changed or
  retired, with one word for which (added, changed, retiring). Every requirement whose
  text you touched is on this list.
- Write the intent's "Handoff" for ready (see `pdlc/templates/handoff.md`): what you
  wrote, what you assumed, what looks unclear.
- Commit the spec and intent files with the message "Specify IN-xxxx: <name>" and the
  trailer `Intent: IN-xxxx`. Commit them even if you stop early.
- Tell the tracker port.
- Tell the user what you wrote, and that `/pdlc:ready` is next.
