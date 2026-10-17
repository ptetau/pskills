---
name: tests
description: >
  Writes and locks the checks of a pdlc change before any app code. The pdlc:test-writer
  agent writes the checks from the spec only. Each new check must fail. Then the skill
  commits and locks the checks, and an independent reviewer judges the checks against the
  spec. Use when the user says "/pdlc:tests", or when a change is planned and ready for its
  checks.
---

# pdlc tests

The checks come first. A test writer that does not see the code writes the checks from
the spec.

Read `pdlc/README.md` first and obey it. Start with its "Before any work" step.

## 1. Pick the change and start its branch

- Use the change that the user named. If the user did not name a change, use the first
  `planned` change, in the order of the intent.
- If the change already has a branch, `/pdlc:build` or `/pdlc:verify` sent the change
  back to this skill. In this condition, do these steps:
  - Switch to that branch. Do not start a new branch.
  - Keep its `Base:`.
  - Go to step 2 with the reason that the change came back.
  - Do not change the status of the change until step 6.
- The base of the change is the branch of the previous change in the list of the intent.
  For the first change, the base is `main`. It is not necessary to merge the previous
  change first, because changes stack.
- Start the branch from the base, through the delivery port. Write `Branch:` and `Base:`
  in the header of the change spec. Set the change to `testing`, and set the intent to
  `building`.
- If the change has a `handoff.md`, read that file. If not, read the "Handoff" of the
  intent.

## 2. Write the checks

Start the `pdlc:test-writer` agent. Give the agent the path of the change spec and nothing
else. The agent writes the checks that the change spec lists under "Check files".

The test writer cannot delete files. If the test writer says that a check file served
only a `(retire)` requirement, delete that file yourself. Use `git rm` before the lock.

If the test writer says that the "Interface" is missing something, add that item to the
change spec yourself (you can see the code). Then start the test writer again.

## 3. Red

Run the checks of each requirement through the checks port.

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
2. Write the hash of that commit in the change spec, on its own line under the header:
   `Tests-Locked: <hash>`. If you lock the tests again, replace the old line.
3. Commit the change spec with the message "Lock tests CH-xxxx" and the trailers `Intent`
   and `Change`.

After the lock, only the test writer is permitted to change these files, and only through
this skill.
Each such change makes a new lock, which replaces the old `Tests-Locked:` line.

## 5. Review the checks

1. Run `python3 pdlc/bin/make_packets.py CH-xxxx tests`.
2. Start a fresh `pdlc:reviewer` agent. Give the agent the path of
   `pdlc/changes/CH-xxxx-…/review/tests/packet.md` and nothing else.
3. If the `result.md` of the reviewer says fail, send the problems to the test writer.
   Then do red, lock, and review again. After two failed rounds, stop and ask the user.

## 6. Finish

- Set the change to `building`.
- Write `handoff.md` for `/pdlc:build`: the checks and what each check proves, the lock,
  and anything that the builder must know.
- Commit with the message "Tests reviewed CH-xxxx" and the trailers `Intent` and `Change`.
- Tell the tracker port. Tell the user that `/pdlc:build` is next.
