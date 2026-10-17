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

First, find where to work ("Where pdlc commits" in `pdlc/README.md`). If a pdlc branch is
unmerged, switch to the newest unmerged pdlc branch. Then the inbox and the specs that you
read are current.

- If the user described something new, add it through the inbox port. Use the words of
  the user for "What and why". Tell the user the ID of the new intent.
- If the user named an intent, read that intent. If the "Notes" of the intent say
  `Awaits approval:`, remove that line. Naming the intent is the approval.
- If neither is true, take the oldest intent with status `new` that does not await
  approval.

If you switched to a branch, start a branch for the intent from that branch. Use the
delivery port. Do this before you commit anything. Write the name of the new branch as the
`Branch:` of the intent. Set the status of the intent to `specifying`.

## 2. Decide what it touches

Read the specs in `pdlc/specs/`. For each thing that the intent needs, decide where the
thing belongs:

- What a user does, through a route, a command, or a page, and what the user gets back →
  a **job** spec. This holds even when the code of the job is in a shared file.
- What the system can do, for use by jobs (a store, an outside service, or plumbing that
  every job uses) → a **capability** spec. The requirements of the capability say what
  the capability offers to jobs. These requirements do not give the user-facing behaviour
  of one job.
- How we do something in all places → a **design** spec.
- How something looks to the user (a format, a wording, or a layout) → the **job** where
  the user sees it. This holds even when a capability makes the value. Add the requirement
  to each place where the user sees the value (a page, an output, or a reply).

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

First, list the change branches, as "Where pdlc commits" in `pdlc/README.md` says. The
statuses on `main` can be out of date. Do not edit a change spec (`changes/*/change.md`).
A change that is not merged keeps what it copied. If you change a requirement that an
unmerged change covers, say so in the handoff. The change of this intent for that spec
then stacks after the unmerged change.

Write directly into the spec files. For a new spec, use `pdlc/templates/`.

- **New requirement:** use the next free number in that spec. Set `Status: proposed`, and
  set `Intents:` to this intent. Write one or two plain sentences. Then write the
  acceptance checks as "Given …, when …, then …" lines. Mark `(assumed)` on each detail
  that the words of the intent do not give, right where you write the detail. Examples of
  such details are a message, a limit, an order, and a format.
- **The intent's own words bind.** Copy every example that the intent gives (an output, a
  message, or a value) into an acceptance line, exactly. Read the words of the intent
  plainly, for every value. This includes the edge values: zero, empty, and an
  integer. Do not use an `(assumed)` reading to narrow the words of the intent and keep the
  old behaviour.
- **Changed requirement:** edit the requirement in place. Set `Status: proposed`. Add this
  intent to `Intents:`.
- **Removed requirement:** set `Status: retiring`, and add this intent to `Intents:`.
- **New job:** list the capabilities and the design specs that the job relies on.

**The newest words win.** Sometimes the intent asks for something that an older
requirement or an `(assumed)` detail rules out. In that case, change the older text to
match. This case is a changed requirement, not a contradiction.

Find every changed requirement of this type. For example, a new format changes every
example that shows the old format. For each changed requirement, add a Note:
`<ID>: was "<old>", now "<new>"`.

Make a point a question for ready only if the words of the intent have two possible
meanings.

**Leave no old wording.** For each requirement that you change or retire, search
`pdlc/specs/` and the README for the words of the old behaviour (a command, a message, a
value, or a button). Fix each place in the specs that still shows those words:

- The title and the summary of the spec.
- The examples and the acceptance lines in other requirements.
- The cross-references (`see CAP-x.R4`). Each cross-reference must still point at the rule
  that it means.
- The notes, the "Known gap" lines, and the "Changes" lists that show the old
  behaviour.

Do not edit the README here, because the README is app code. For each README line that
shows the old behaviour, add a line to the "Notes" of the intent:
`README: "<old line>" → <requirement>`. The change for that requirement fixes the README
line.

Sometimes a requirement that you must change is still `proposed` for a different intent
that is not done. In that case, ask the user how to fit the two intents together. With
`defaults`, this intent wins where the two intents differ. The changes of this intent come
after the changes of the other intent.

## 5. Record and finish

1. In the "Requirements" section of the intent, list each requirement that you added,
   changed, or retired. Give one word for each requirement: added, changed, or retiring.
   This list must include each requirement whose text you touched.
2. Write the "Handoff" of the intent for ready (see `pdlc/templates/handoff.md`): what you
   wrote, what you assumed, and what looks unclear.
3. Commit the spec and intent files with the message "Specify IN-xxxx: <name>" and the
   trailer `Intent: IN-xxxx`. If you stop early, commit these files also.
4. Tell the tracker port.
5. Tell the user what you wrote, and that `/pdlc:ready` is next.
