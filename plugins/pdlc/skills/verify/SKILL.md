---
name: verify
description: >
  Examines a built and recorded pdlc change before the merge. Runs each check. Then sends
  one packet for each review remit (specification, security, quality, compliance,
  privacy) to a different fresh, independent reviewer, all at the same time. When all
  pass, marks the requirements verified, runs the merge check, and proposes the merge with
  the GIF. Does not merge. Use when the user says "/pdlc:verify", or when a change has its
  visual review.
---

# pdlc verify

This skill decides if a change is sufficiently good to merge. Then the skill asks the user
to approve the merge.

Read `pdlc/README.md` first and obey it. Start with its "Before any work" step. Then read
the `handoff.md` of the change.

## 1. Pick the change

Use the change that the user named. If the user did not name a change, use the first
change with the status `building` that has a `review.gif`. Switch to the branch of that
change.

## 2. Run the checks

Do these steps through the checks port:

- For each requirement in the change, run its checks. Each requirement needs at least one
  check, and all its checks must pass. "No checks found" is a failure, but not for a
  `(retire)` requirement.
- Run all checks. All checks must pass.
- Make sure that no check file changed since `Tests-Locked`.

## 3. Independent reviews

1. Get the remits from "Reviews" in `pdlc/config.md`. Do not include `tests`, because the
   tests stage already reviewed the checks, and its result stays.
2. Make the packets: `python3 pdlc/bin/make_packets.py CH-xxxx <remit> <remit> …`.
3. Start one fresh `pdlc:reviewer` agent for each remit, all at the same time. Give each
   reviewer only the path of its own packet. Do not tell a reviewer what a different
   reviewer found.
4. Wait for all the reviewers. Each reviewer writes `review/<remit>/result.md`.

## 4. If anything failed

1. Collect the failed checks and each problem from the results in the `handoff.md` of the
   change. Address each item to the build stage (code problems) or to the tests stage
   (check problems).
2. Add a line to the progress log.
3. Commit these changes.
4. Tell the user which stage is next. Stop here.

## 5. If everything passed

1. In the spec file of each requirement in the change, set the requirement to `verified`.
   Set the change to `in review`.
2. Commit the results and the statuses with the message "Verified CH-xxxx" and the
   trailers `Intent` and `Change`.
3. Run the gate through the delivery port. The gate must pass. If the gate fails, correct
   the problems that it names.
4. Propose the merge through the delivery port, with the base of the change as the
   target. Put these items in the description:
   - The GIF, embedded. The delivery adapter tells how.
   - A table of each requirement, its checks, and their result.
   - A table of each remit and its result, with a link to each `result.md`.
   - The lock commit, and each "Manual checks" item that the user must confirm.
   - Each detail that is marked *(assumed)* in the change spec and its requirements, on
     one line each. Thus, the user reviews all these details in one place.
5. If each change for the intent is now `in review` or `merged`, set the intent to
   `in review`.
6. Write `handoff.md`: the link, and what the user must confirm. Commit the handoff.
7. Tell the tracker port. Give the user the link.

Do not merge the change yourself.
