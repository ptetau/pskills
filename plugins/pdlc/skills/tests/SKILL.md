---
name: tests
description: >
  Writes and locks a pdlc change's checks before any app code. The pdlc:test-writer agent
  writes them from the spec alone; every new check must fail; they are committed and
  locked; then an independent reviewer judges the checks against the spec. Use when the
  user says "/pdlc:tests", or a change is planned and ready for its checks.
---

# pdlc tests

Checks come first, from the spec, written by someone who never sees the code.

Read `pdlc/README.md` first and follow it. Start with its "Before any work" step.

## 1. Pick the change and start its branch

- Use the change the user named. Otherwise take the first change, in the intent's order,
  with status `planned`.
- Its base is the branch of the change before it in the intent's list, or `main` for the
  first. The change before it doesn't need to be merged: changes stack.
- Start the branch through the delivery port, from the base. Write `Branch:` and `Base:`
  into the change spec header. Set the change to `testing` and the intent to `building`.
- Read the intent's "Handoff", or the change's `handoff.md` if it has one.

## 2. Write the checks

Start the `pdlc:test-writer` agent. Give it the change spec's path and nothing else. It
writes the checks listed under "Check files".

If it says the "Interface" is missing something, add it to the change spec yourself (you
can see the code), then start the test writer again.

## 3. Red

Run each requirement's checks through the checks port.

- For new behaviour, every check must fail. A check that passes already proves nothing:
  send it back to the test writer with the reason.
- For behaviour that already exists (a requirement only reworded), a pass is fine. Note it
  in the progress log.
- A check that errors because the interface doesn't exist yet counts as failing, as long
  as the error is about the missing interface and not a mistake in the check.

## 4. Lock

1. Commit the check files with the message "Tests CH-xxxx", with `Intent`, `Change` and
   `Req` trailers.
2. Write that commit's hash into the change spec on its own line under the header:
   `Tests-Locked: <hash>`.
3. Commit the change spec ("Lock tests CH-xxxx", trailers `Intent` and `Change`).

From now on, only the test writer may change these files, and only through this skill.
Doing so makes a new lock, and the merge check reads the newest one.

## 5. Review the checks

1. Run `python3 pdlc/bin/make_packets.py CH-xxxx tests`.
2. Start a fresh `pdlc:reviewer` agent with the path of
   `pdlc/changes/CH-xxxx-…/review/tests/packet.md` and nothing else.
3. If its `result.md` says fail, send the problems to the test writer, then run red,
   lock and review again. After two failed rounds, stop and ask the user.

## 6. Finish

- Set the change to `building`.
- Write `handoff.md` for build: the checks and what each proves, the lock, and anything the
  builder must know.
- Commit ("Tests reviewed CH-xxxx", trailers `Intent` and `Change`).
- Tell the tracker port. Tell the user `/pdlc:build` is next.
