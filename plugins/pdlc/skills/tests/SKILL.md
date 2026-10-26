---
name: tests
description: >
  Writes and locks the component checks of a pdlc change before any app code. The
  pdlc:test-writer agent writes the checks from the spec only. Each new check must fail.
  Then the skill commits and locks the checks, and an independent reviewer judges the
  checks against the spec. Use when the user says "/pdlc:tests", or when a change is
  planned and ready for its checks.
---

# pdlc tests

The checks come first. A test writer that does not see the code writes the checks from
the spec. This skill writes the component checks of one change. The acceptance checks of
the intent come before the first change, from `/pdlc:acceptance`.

Read `pdlc/README.md` first and obey it. Start with its "Before any work" step.

## 1. Pick the change and start its branch

- Use the change that the user named. If the user did not name a change, use the first
  `planned` change, in the order of the intent.
- For the first change of an intent, the acceptance stage must be complete. Its handoff
  in the intent has the title `acceptance → tests`. If not, run `/pdlc:acceptance` first.
- If the change already has a branch, `/pdlc:build` or `/pdlc:verify` sent the change
  back to this skill. In this condition, do these steps:
  - Switch to that branch. Do not start a new branch.
  - Keep its `Base:`.
  - Go to step 2 with the reason that the change came back.
  - Do not change the status of the change until step 6.
- The base of the change is the branch of the previous change in the list of the intent.
  For the first change, the previous change is the newest unmerged change of an earlier
  intent. If there is no such change, the base is `main`.
- Changes stack, so merging the previous change first is not necessary. But if the
  previous change is not `in review` or `merged`, finish the show and verify stages of
  that change first.
- Start the branch from the base, through the delivery port. If the intent has a
  `Branch:`, the first change of the intent starts from that branch instead. Then the
  change carries the specs and the acceptance checks of the intent.
- If the first change starts from the branch of the intent, make sure that this branch
  holds the base: `git merge-base --is-ancestor <base> <intent branch>`. If the command
  fails, merge the base into the branch of the intent first. Give the merge commit the
  trailer `Intent`.
- If both branches changed a line, resolve the line as follows. For a requirement that the
  intent changed, keep the text and status of the intent. For the other requirements, keep
  the text and status of the base.
- Write `Branch:` and `Base:` in the header of the change spec. Set the change to
  `testing`, and set the intent to `building`. Commit with the message "Start CH-xxxx" and
  the trailers `Intent` and `Change`.
- If the change has a `handoff.md`, read that file. If not, read the "Handoff" of the
  intent.

## 2. Write the checks

Start the `pdlc:test-writer` agent with `run_in_background: false`. Give the agent the
absolute path of the change spec and nothing else. The agent writes the checks that the
change spec lists under "Check files".

The test writer cannot delete files. If the test writer says that a check file served
only a `(retire)` requirement, delete that file yourself. Use `git rm` before the lock.

If the test writer says that the "Interface" is missing something, add that item to the
change spec yourself (you can see the code). Then start the test writer again.

## 3. Red

Run the checks of each requirement through the checks port. Use a time limit of a few
minutes for each run. A run that does not finish is a broken check, not a red one. Send
that check back to the test writer before you lock.

- For new behaviour, each check must fail. A check that already passes proves nothing.
  Send that check back to the test writer with the reason.
- For behaviour that already exists (only the words of the requirement changed), a pass
  is correct. Record the pass in the progress log.
- A check that gives an error because the interface does not exist yet counts as failing.
  But the error must be about the missing interface, not about a mistake in the check.
- If `/pdlc:build` or `/pdlc:verify` sent the change back, app code already exists. Thus,
  a corrected check can pass. A pass is correct here. Record each result in the progress
  log.

## 4. Lock

1. Commit the check files with the message "Tests CH-xxxx" and the trailers `Intent`,
   `Change`, and `Req`.
2. Write the hash of that commit on the `Tests-Locked:` line, right under the header of
   the change spec: `Tests-Locked: <hash>`. If you lock the tests again, replace the hash.
3. Commit the change spec with the message "Lock tests CH-xxxx" and the trailers `Intent`
   and `Change`.

After the lock, only the test writer is permitted to change these files, and only through
this skill.
Each such change makes a new lock, which replaces the old `Tests-Locked:` line.

## 5. Review the checks

Every lock gets its own review, including a re-lock sent back from build or verify. The
merge check refuses a tests review of an older lock. After the first review,
`make_packets.py` makes a re-review packet. The packet holds the earlier problems, and the
diff of the checks since the earlier lock. The reviewer judges only these two items.

1. Run `python3 pdlc/bin/make_packets.py CH-xxxx tests`.
2. Start a fresh `pdlc:reviewer` agent with `run_in_background: false`. Give the agent the
   path of `pdlc/changes/CH-xxxx-…/review/tests/packet.md` and nothing else.
3. Commit the packet and the result with the message "Review tests CH-xxxx" and the
   trailers `Intent` and `Change`. If the `result.md` of the reviewer says fail, send the
   problems to the test writer. Then do red, lock, and review again. If the review fails a
   third time, stop and ask the user.

## 6. Finish

- Set the change to `building`.
- Write `handoff.md` for `/pdlc:build`: the checks and what each check proves, the lock,
  and anything that the builder must know.
- Commit with the message "Tests reviewed CH-xxxx" and the trailers `Intent` and `Change`.
- Tell the tracker port. Tell the user that `/pdlc:build` is next.
