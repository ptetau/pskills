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
2. Make the packets: `python3 pdlc/bin/make_packets.py CH-xxxx <remit> <remit> …`. For a
   remit that does not apply, the script writes `result.md` itself and says so. Start no
   reviewer for that remit.
3. Start one fresh `pdlc:reviewer` agent for each remit that got a packet, all in one
   message, each with `run_in_background: false`. Give each reviewer only the path of its
   own packet. Do not tell a reviewer what a different reviewer found.
4. The tool calls return when all the reviewers are done. Each reviewer writes
   `review/<remit>/result.md`.

## 4. New behaviour

A review point needs new behaviour when no acceptance line, design spec, or remit rule
asks for the behaviour. Examples are a new limit or size cap, a guard, another input
check, and a new error or status. Reviewers list these points under "Follow-ups". A
problem that only new behaviour can fix is also such a point. For each such point, in
every round, do these steps:

- Do not build the point on this branch.
- File the point through the inbox port as a new intent, with status `new`, in the words
  of the reviewer. The "Notes" of the intent start with
  `Awaits approval: found reviewing CH-xxxx (<remit>)`. If an intent already asks for the
  same thing, do not file the point.
- Add the ID of the new intent to the progress log of the change, for the proposal.

If the user gave `defaults`, do not approve such an intent. The intent waits for the user.

Commit each packet, each result, and each new intent now, whether the round passes or
fails. Use the message "Verify CH-xxxx: round <n>" and the trailers `Intent` and `Change`.
The findings of a failed round must stay in git.

## 5. If anything failed

1. Collect the failed checks and each other problem from the results in the `handoff.md`
   of the change. Address each problem to the stage that fixes the problem:
   - A failed check, or a problem with a check: the tests stage.
   - A problem that says that an acceptance line is not met, although each check passed:
     the tests stage first (for a check tagged with the requirement of that line), then
     the build stage.
   - Old wording in the title, summary, cross-reference, or note of a spec: fix the
     wording yourself now, on this branch. Make the wording match the requirements as they
     are. Change only those words. Do not change an acceptance line.
   - Any other problem (a remit rule, a design spec, or unsafe code): the build stage. No
     acceptance line names the problem, so the problem needs no new check.
2. If a remit failed only for new behaviour or old wording, send nothing to the build
   stage for that remit. The next stage is verify again, and that run counts as a round.
3. Add a line to the progress log.
4. Commit with the message "Send back CH-xxxx: <stage>" and the trailers `Intent` and
   `Change`.
5. Tell the user which stage is next. Stop here.

Every problem goes to the tests stage or the build stage. No problem goes to the user.
The build stage only makes the code meet an existing acceptance line, design spec, or
remit rule. The build stage stays inside the "Files" of the change and uses the plainest
fix, for example a clearer message. Do not add or change a requirement, an acceptance
line, or an error code on the branch of a change.

## 6. If everything passed

1. In the spec file of each requirement in the change, set the requirement to `verified`.
   Set the change to `in review`.
2. Commit the results and the statuses with the message "Verified CH-xxxx" and the
   trailers `Intent` and `Change`.
3. Run the gate through the delivery port. The gate must pass, except for lines that say
   that another change of this intent is not ready. Those lines clear when each change in
   the stack is proposed. Correct each other problem that the gate names. Commit each
   correction with the message "Update CH-xxxx: <what>". Use these rules:
   - For a conflict with main, merge main into this branch. Give the merge commit the
     trailers `Intent` and `Change`. Keep the text of main, and keep the statuses of this
     branch for its own requirements.
   - For a marker that the gate names, write the marker as `(assumed)`. Move any reason
     out of the brackets, and keep the meaning.
4. Propose the merge through the delivery port, with the base of the change as the
   target. Write the description from `pdlc/templates/proposal.md`, and fill each section.
   Put these items in the description:
   - The GIF, embedded. The delivery adapter tells how.
   - A table of each requirement, its checks, and their result.
   - A table of each remit and its result, with a link to each `result.md`.
   - The lock commit, and each "Manual checks" item that the user must confirm.
   - Each detail that is marked `(assumed)` in the change spec and its requirements, on
     one line each. Thus, the user reviews all these details in one place.
   - The other changes that merge together with this change.
   - The intents that you filed in step 4 (new behaviour).
5. If each change for the intent is now `in review` or `merged`, set the intent to
   `in review`. Do this on the branch of the change.
6. Write `handoff.md`: the link, and what the user must confirm. Commit the handoff
   together with the intent. Use the message "Propose CH-xxxx" and the trailers `Intent`
   and `Change`. Each commit on the branch of a change carries the trailer `Change`.
7. Tell the tracker port. Give the user the link.

Do not merge the change yourself.
