---
name: intake
description: >
  Takes one intent into pdlc and turns it into spec patches: new jobs, new capabilities,
  new conventions, or changes to existing ones. Marks new requirements proposed. Never
  writes code. Use when the user says "/pdlc:intake", or describes something they want
  built or changed in a pdlc project. Also use when the user names an intent in the inbox
  to specify.
---

# pdlc intake

Turns an intent into changes to the specs. Never writes code.

Read `pdlc/README.md` first and follow it. Start with its "Before any work" step.

## 1. Get the intent

First, see where to work ("Where pdlc commits" in `pdlc/README.md`). If a pdlc branch is
unmerged, switch to the newest unmerged pdlc branch. Then the inbox and specs you read are
current.

- If the user described something new, add it through the inbox port. Use the user's
  words for "What and why". Tell the user the intent's ID.
- If the user named an intent, read that intent. If its "Notes" say `Awaits approval:`,
  remove that line. Naming the intent is the approval.
- If neither, take the oldest intent with status `new` that doesn't await approval.

If you switched to a branch, start the intent's own branch from that branch now, through
the delivery port. Do this before you commit anything. Write the new branch's name as the
intent's `Branch:`. Set the intent's status to `specifying`.

## 2. Decide what it touches

Read the specs in `pdlc/specs/`. For each thing the intent needs, decide where it belongs:

- What a user does (through a route, a command or a page) and what the user gets back → a
  **job** spec. This holds even when the job's code sits in a shared file.
- What the system offers to jobs (a store, an outside service, plumbing every job uses)
  → a **capability** spec. A capability's requirements say what it offers jobs, never one
  job's user-facing behaviour.
- How we do something everywhere → a **design** spec.
- How something looks to the user (a format, a wording, a layout) → the **job** where the
  user sees it. This holds even when a capability makes the value. Add the requirement to
  each place where the user sees the value (a page, an output, a reply).

Prefer existing specs. Create a new spec only when no existing spec fits. When you create
a capability, draw it around something likely to change (a vendor, a set of rules, a
store). Name the capability for that thing, not for a feature: `CAP-payments`, not
`CAP-checkout-button`.

If the intent could mean two different things, ask the user before you go on. See "Asking
questions" in `pdlc/README.md`. With `defaults`, take the likelier meaning and note it.

## 3. Deepen stub specs

If a spec you will change says `Status: stub`, start the `pdlc:recon` agent for a **deep
look** at that spec's code map. Write the requirements that recon returns into the spec
(they come back as `built`, `Source: recon`). Set the spec to `Status: active`.

## 4. Write the patches

First, list the change branches, as "Where pdlc commits" in `pdlc/README.md` says.
Statuses on main may be stale. Never edit a change spec (`changes/*/change.md`). A change
that hasn't merged keeps what it copied. If you change a requirement that an unmerged
change covers, say so in the handoff. This intent's change for that spec then stacks
after the unmerged change.

Write straight into the spec files. Use `pdlc/templates/` for new spec files.

- **New requirement:** use the next free number in that spec. Set `Status: proposed`. Set
  `Intents:` to this intent. Write one or two plain sentences. Then write acceptance checks
  as "Given …, when …, then …" lines. Mark `(assumed)` on each detail the intent's words
  don't give, right where you write the detail. Examples of such details: a message, a
  limit, an order, a format.
- **The intent's own words bind.** Copy every example the intent gives (an output, a
  message, a value) into an acceptance line, exactly. Read the intent's words plainly, for
  every value, including the edge ones (zero, empty, a whole number). An `(assumed)`
  reading never narrows the intent's words to keep the old behaviour.
- **Changed requirement:** edit it in place. Set `Status: proposed`. Add this intent to
  `Intents:`.
- **Removed requirement:** set `Status: retiring`. Add this intent to `Intents:`.
- **New job:** list the capabilities and design specs it relies on.

**The newest words win.** If the intent asks for something an older requirement or an
`(assumed)` detail rules out, change the older text to match. Such a case is a changed
requirement, not a contradiction. Find every such case. For example, a new format changes
every example that shows the old format. Add a Note for each case:
`<ID>: was "<old>", now "<new>"`. Leave a point as a question for ready only if the
intent's words could be read two ways.

**Leave no old wording.** For each requirement you change or retire, search `pdlc/specs/`
and the README for the old behaviour's words (a command, a message, a value, a button).
Fix every place in the specs that still shows those words:

- the spec's title and summary;
- examples and acceptance lines in other requirements;
- cross-references (`see CAP-x.R4`): each still points at the rule it means;
- notes, "Known gap" lines and "Changes" lists that describe the old behaviour.

Don't edit the README here. The README is app code. For each README line that shows the
old behaviour, add a line to the intent's "Notes": `README: "<old line>" → <requirement>`.
The change for that requirement fixes the README line.

If a requirement you need to change is still `proposed` for another intent that isn't
done, ask the user how the two intents fit. With `defaults`, this intent wins where the
two intents differ. Its changes come after the other intent's changes.

## 5. Record and finish

- In the intent's "Requirements" section, list every requirement you added, changed or
  retired. Give each one word for which: added, changed or retiring. Every requirement
  whose text you touched is on this list.
- Write the intent's "Handoff" for ready (see `pdlc/templates/handoff.md`): what you
  wrote, what you assumed, what looks unclear.
- Commit the spec and intent files with the message "Specify IN-xxxx: <name>" and the
  trailer `Intent: IN-xxxx`. Even if you stop early, commit these files.
- Tell the tracker port.
- Tell the user what you wrote, and that `/pdlc:ready` is next.
