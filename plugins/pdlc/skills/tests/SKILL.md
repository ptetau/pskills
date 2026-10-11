---
name: tests
description: >
  Writes and locks a pdlc change's checks before any app code. The pdlc:test-writer agent
  writes the checks from the spec alone. Every new check must fail. Then the skill commits
  and locks the checks, and an independent reviewer judges them against the spec. Use when
  the user says "/pdlc:tests", or a change is planned and ready for its checks.
---

# pdlc tests

Checks come first. Someone who never sees the code writes them, from the spec.

Read `pdlc/README.md` first and follow it. Start with its "Before any work" step.

## 1. Pick the change and start its branch

- If the user named a change, use that change. Otherwise, take the first change with
  status `planned`, in the intent's order.
- If the change already has a branch, build or verify sent it back here. In that case:
  - switch to that branch instead of starting one;
  - keep its `Base:`;
  - go to step 2 (write the checks) with the reason the change came back;
  - leave its status as it is until step 6 (finish).
- The change's base is the branch of the change before it in the intent's list. For the
  intent's first change, the base is the newest change of an earlier intent that hasn't
  merged. If there is none, the base is `main`. The change before doesn't need to be
  merged, but it must be `in review` or `merged`. If it isn't, finish that change's show
  and verify first.
- Start the branch through the delivery port, from the base. If the intent has a
  `Branch:`, the intent's first change starts from that branch instead. That way, the
  change carries the intent's specs.
- If the first change starts from the intent's branch, check that this branch holds the
  base: `git merge-base --is-ancestor <base> <intent branch>`. If the command fails, merge
  the base into the intent's branch first (trailer `Intent`). If both branches changed a
  line, keep the intent's text and status for requirements the intent changed. Keep the
  base's text and status for the rest.
- Write `Branch:` and `Base:` into the change spec header. Set the change to `testing`
  and the intent to `building`. Commit ("Start CH-xxxx", trailers `Intent` and `Change`).
- If the change has a `handoff.md`, read it. Otherwise, read the intent's "Handoff".

## 2. Write the checks

Start the `pdlc:test-writer` agent. Give it the change spec's absolute path and nothing
else. The test writer writes the checks listed under "Check files".

The test writer can't delete files. If the test writer says a check file served only a
`(retire)` requirement, delete that file yourself with `git rm`. Do this before the lock.

If the test writer says the "Interface" is missing something, add the missing part to the
change spec yourself. You can see the code. Then start the test writer again.

## 3. Red

Run each requirement's checks through the checks port, with a time limit of a few
minutes. A run that doesn't finish is a broken check, not a red one. Send that check back
to the test writer before you lock.

- For new behaviour, every check must fail. A check that already passes proves nothing.
  Send it back to the test writer with the reason.
- For behaviour that already exists (a requirement only reworded), a pass is fine. Note
  the pass in the progress log.
- If a check errors because the interface doesn't exist yet, the check counts as failing.
  But the error must be about the missing interface, not a mistake in the check.
- If build or verify sent the change back, app code already exists, so a fixed check may
  pass. Such a pass is fine. Note each result in the progress log.

## 4. Lock

1. Commit the check files with the message "Tests CH-xxxx", with `Intent`, `Change` and
   `Req` trailers.
2. Write that commit's hash into the `Tests-Locked:` line right under the change spec's
   header: `Tests-Locked: <hash>`. On a re-lock, replace the hash.
3. Commit the change spec ("Lock tests CH-xxxx", trailers `Intent` and `Change`).

From now on, only the test writer may change these files, and only through this skill.
Each such change makes a new lock, which replaces the old `Tests-Locked:` line.

## 5. Review the checks

Every lock gets its own review, including a re-lock after build or verify sent the change
back. The merge check refuses a tests review of an older lock.

1. Run `python3 pdlc/bin/make_packets.py CH-xxxx tests`.
2. Start a fresh `pdlc:reviewer` agent with the path of
   `pdlc/changes/CH-xxxx-…/review/tests/packet.md` and nothing else.
3. Commit the packet and result ("Review tests CH-xxxx", trailers `Intent` and
   `Change`). If the result says fail, send the problems to the test writer. Then run red,
   lock and review again. If the review fails a third time, stop and ask the user.

## 6. Finish

- Set the change to `building`.
- Write `handoff.md` for build: the checks and what each proves, the lock, and anything the
  builder must know.
- Commit ("Tests reviewed CH-xxxx", trailers `Intent` and `Change`).
- Tell the tracker port. Tell the user `/pdlc:build` is next.
