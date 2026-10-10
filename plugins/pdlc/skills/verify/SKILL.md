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

Commit every packet and result now, pass or fail ("Verify CH-xxxx: round <n>", trailers
`Intent` and `Change`). A failed round's findings must stay in git.

## 4. If anything failed

Collect the failing checks and every problem from the results into the change's
`handoff.md`, addressed to build (code problems) or tests (check problems). Add a line to
the progress log, commit, and tell the user which stage is next. Stop here.

A code problem that every check passed is also a gap in the checks. Address it to tests
first: a check that fails on it is written and locked before build fixes the code.

A fix stays inside the change's spec. Never add or change a requirement, an acceptance
line or an error code on a change's branch to answer a review. A point that needs one is
a follow-up: list it in the handoff for the user, not for build.

## 5. If everything passed

1. Set each requirement in the change to `verified` in its spec file, and the change to
   `in review`.
2. Commit the results and statuses: "Verified CH-xxxx", trailers `Intent` and `Change`.
3. Run the gate through the delivery port. It must pass. If it doesn't, fix what it names.
   For a conflict with main, merge main into this branch (trailers `Intent` and
   `Change`), keeping main's text and this branch's statuses for its own requirements.
4. Propose the merge through the delivery port, with the change's base as the target. In
   the description:
   - the GIF, embedded (the delivery adapter says how);
   - a table of each requirement, its checks and their result;
   - a table of each remit and its result, linking each `result.md`;
   - the lock commit, and any "Manual checks" for the user to confirm;
   - every detail marked *(assumed)* in the change spec and its requirements, one line
     each, so the user reviews them in one place;
   - every follow-up from the results, for the user to add as intents if they want them.
5. If every change for the intent is now `in review` or `merged`, set the intent to
   `in review`, here on the change's branch.
6. Write `handoff.md`: the link, and what the user needs to confirm. Commit it with the
   intent ("Propose CH-xxxx", trailers `Intent` and `Change`). Every commit on a
   change's branch carries its `Change`.
7. Tell the tracker port. Give the user the link.

Never merge yourself.
