---
name: verify
description: >
  Verifies a built and recorded pdlc change. Runs every check, then sends one packet per
  review remit (specification, security, quality, compliance, privacy) to a fresh,
  independent reviewer each, in parallel. When all pass, marks requirements verified,
  runs the merge check and proposes the merge with the GIF. Never merges. Use when the
  user says "/pdlc:verify", or a change has its visual review.
---

# pdlc verify

Decides whether a change is good enough to merge, then asks the user to approve it.

Read `pdlc/README.md` first and follow it. Start with its "Before any work" step, then read
the change's `handoff.md`.

## 1. Pick the change

Use the change the user named. Otherwise take the first change with status `building`
that has a `review.gif`. Switch to its branch.

## 2. Run the checks

Through the checks port:

- For each requirement in the change, run its checks. Each needs at least one, and all
  must pass. "No checks found" is a failure, except for a `(retire)` requirement.
- Run all checks. Everything must pass.
- Confirm no check file changed since `Tests-Locked`.

## 3. Independent reviews

1. Take the remits from "Reviews" in `pdlc/config.md`, leaving out `tests` (the tests stage
   already reviewed the checks; its result stays).
2. Build their packets: `python3 pdlc/bin/make_packets.py CH-xxxx <remit> <remit> …`.
3. Start one fresh `pdlc:reviewer` agent per remit, all at once. Give each only the path of
   its own packet. Don't tell any reviewer what another found.
4. Wait for all of them. Each writes `review/<remit>/result.md`.

## 4. New behaviour

A review point needs new behaviour when no acceptance line, design spec or remit rule
asks for it: a new limit or size cap, a guard, another input check, a new error or
status. Reviewers list these under "Follow-ups". A problem that only new behaviour would
fix counts too. For each one, in every round:

- Never build it on this branch.
- File it through the inbox port as a new intent, status `new`, in the reviewer's words.
  Its "Notes" start with `Awaits approval: found reviewing CH-xxxx (<remit>)`. Skip it if
  an intent already asks for the same thing.
- Add its ID to the change's progress log, for the proposal.

With `defaults`, never approve one. It waits for the user.

Commit every packet, result and new intent now, pass or fail ("Verify CH-xxxx: round
<n>", trailers `Intent` and `Change`). A failed round's findings must stay in git.

## 5. If anything failed

Collect the failing checks and every other problem from the results into the change's
`handoff.md`, each addressed to the stage that fixes it:

- a failing check, or a problem with a check → tests;
- a problem that says an acceptance line isn't met, when every check passed → tests
  first, for a check tagged with that line's requirement, then build;
- old wording in a spec's title, summary, cross-reference or note → fix it yourself
  now, on this branch, to match the requirements as they are. Change those words only,
  never an acceptance line;
- any other problem (a remit rule, a design spec, unsafe code) → build. No acceptance
  line names it, so it needs no new check.

If a remit failed only for new behaviour or old wording, nothing is built for it:
verify runs again, and counts as a round.

Add a line to the progress log, commit ("Send back CH-xxxx: <stage>", trailers `Intent`
and `Change`), and tell the user which stage is next. Stop here.

Every problem goes to tests or build, never to the user. Build only makes the code meet
an existing acceptance line, design spec or remit rule, inside the change's "Files",
with the plainest fix, for example a clearer message. Never add or change a requirement,
an acceptance line or an error code on a change's branch.

## 6. If everything passed

1. Set each requirement in the change to `verified` in its spec file, and the change to
   `in review`.
2. Commit the results and statuses: "Verified CH-xxxx", trailers `Intent` and `Change`.
3. Run the gate through the delivery port. It must pass, except for lines saying another
   change of this intent is not ready: those clear once the whole stack is proposed. Fix
   anything else it names ("Update CH-xxxx: <what>"). For a conflict with main, merge
   main into this branch (trailers `Intent` and `Change`), keeping main's text and this
   branch's statuses for its own requirements. For a marker it names, write it as
   `(assumed)` and move any reason out of the brackets, keeping the meaning.
4. Propose the merge through the delivery port, with the change's base as the target.
   Write the description from `pdlc/templates/proposal.md`, filling every section: the
   GIF, the requirements and their checks, the remits, manual checks, every `(assumed)`
   detail, the changes that merge together, and the intents filed in step 4.
5. If every change for the intent is now `in review` or `merged`, set the intent to
   `in review`, here on the change's branch.
6. Write `handoff.md`: the link, and what the user needs to confirm. Commit it with the
   intent ("Propose CH-xxxx", trailers `Intent` and `Change`). Every commit on a
   change's branch carries its `Change`.
7. Tell the tracker port. Give the user the link.

Never merge yourself.
