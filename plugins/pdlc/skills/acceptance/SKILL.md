---
name: acceptance
description: >
  Writes, locks, and reviews the acceptance checks of a pdlc intent, before the first
  change of the intent starts. The pdlc:test-writer agent writes black-box checks of each
  acceptance line of the intent, through the interface that a user uses. Each check must
  fail first. Then the skill locks the checks on the intent branch, and an independent
  reviewer judges the checks. Use when the user says "/pdlc:acceptance", or when the
  changes of an intent are planned.
---

# pdlc acceptance

The acceptance checks prove all of the intent. Each check proves one acceptance line, as a
user meets the line. A check can use each feature of the intent, and each feature that
exists already. Thus, the checks fail until the last change of the intent is built.

Read `pdlc/README.md` first and obey it. Start with its "Before any work" step. Then read
the "Handoff" section of the intent.

## 1. Pick the intent and its branch

- Use the intent that the user named. If the user did not name an intent, use the oldest
  `ready` intent that lists changes and has `Acceptance-Locked: none`.
- If `/pdlc:build` or `/pdlc:verify` sent the intent back, read the reason in the
  `handoff.md` of that change. App code exists already.
- Work at the top of the stack of the intent. The top is the branch of the newest change
  of the intent that has a branch. Before the first change, the top is the intent branch.
- If the intent has `Branch: none`, start the intent branch through the delivery port. Use
  the newest unmerged pdlc branch as its start, or else main. Write the new branch in
  `Branch:`.
- Set the intent to `building`.
- If each requirement that the intent lists is `retiring`, there is nothing to prove. Keep
  `Acceptance-File: none` and `Acceptance-Locked: none`, and go to step 6.
- If `pdlc/config.md` has no "acceptance file" line or no "acceptance" line, write them
  now, as step 4 of `/pdlc:init` says. Commit them with the acceptance file.
- Write the path of the acceptance file on the line `Acceptance-File:` of the intent. The
  path is the "acceptance file" of `pdlc/config.md`, with the intent ID for `{intent}`.
  Write the ID in the ID form of the project.

## 2. Write the checks

Start the `pdlc:test-writer` agent with `run_in_background: false`. Give the agent the
absolute path of the intent file and nothing else. The agent writes the acceptance file.

The test writer can say that the "Interface" of a change is missing something. Then add
that item to the change spec yourself, and start the test writer again.

The test writer can also remove a check from the acceptance file of an earlier intent.
That check proved a requirement that this intent changes or retires. The acceptance file
of this intent proves the new line.

## 3. Red

Run the acceptance checks of the intent through the checks port (**run acceptance**). Use
a time limit of a few minutes. A run that does not finish has a broken check. Send that
check back to the test writer before you lock.

- For new behaviour, each check must fail. Send a check that passes back to the test
  writer with the reason.
- For behaviour that exists already, a pass is correct. Record the pass in the "Notes" of
  the intent.
- A check that fails because a command, a route, or a function does not exist yet counts
  as failing. The error must not come from a mistake in the check.
- After a send-back, app code exists. Thus, a corrected check can pass.

## 4. Lock

On the branch of a change, each commit also carries the trailer `Change`.

1. Commit the acceptance files and the intent with the message "Acceptance IN-xxxx" and
   the trailers `Intent` and `Req`.
2. Write the hash of that commit on the line `Acceptance-Locked:` of the intent. If you
   lock again, replace the hash.
3. Commit the intent with the message "Lock acceptance IN-xxxx" and the trailer `Intent`.

After the lock, only the test writer is permitted to change the acceptance file, and only
through this skill. Each edit makes a new lock and needs a new review. A new lock also
makes the old `Acceptance-Passed:` out of date. The merge check finds both.

## 5. Review the checks

1. Run `python3 pdlc/bin/make_packets.py IN-xxxx`.
2. Start a fresh `pdlc:reviewer` agent with `run_in_background: false`. Give the agent the
   path of `pdlc/acceptance/IN-xxxx-…/review/tests/packet.md` and nothing else.
3. Commit the packet and the result with the message "Review acceptance IN-xxxx" and the
   trailer `Intent`.
4. If the result says fail, send the problems to the test writer. Then do red, lock, and
   review again. If the review fails a third time, stop and ask the user.

## 6. Finish

- Write the handoff for `/pdlc:tests` in the "Handoff" section of the intent. Give the
  checks, the lock, and what each change must give the checks. After a send-back, write
  the `handoff.md` of that change for `/pdlc:build`.
- Commit with the message "Acceptance reviewed IN-xxxx" and the trailer `Intent`.
- Tell the tracker port. Tell the user the next step: `/pdlc:tests`, or `/pdlc:build`
  after a send-back.
