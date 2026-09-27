---
name: build
description: >
  Builds one pdlc change whose checks are written and locked. The pdlc:builder agent
  writes app code until the checks pass; it can't change the checks. Commits with trace
  trailers and marks requirements built. Use when the user says "/pdlc:build", or a
  change's tests are locked and reviewed.
---

# pdlc build

Makes a change's locked checks pass, without touching them.

Read `pdlc/README.md` first and follow it. Start with its "Before any work" step, then read
the change's `handoff.md`.

## 1. Pick the change

Use the change the user named. Otherwise take the first change, in the intent's order,
with status `building`. If its change spec has no `Tests-Locked:` line, stop and say
`/pdlc:tests` comes first. Switch to its branch.

If the branch it is based on has new commits since this branch started (for example a
fix after review), merge that branch in first, with the trailers `Intent` and `Change`.

## 2. Build

Start the `pdlc:builder` agent with the change spec's path. It changes only the app files
listed under "Files", runs the checks, and reports back.

- If it says a check looks wrong, don't change the check. Send the reason to
  `/pdlc:tests`, which asks the test writer and locks again. Then build again.
- If it needs a file that isn't listed, ask the user. If they agree, add it to "Files"
  and start the builder again.
- If the same problem comes back twice, stop and ask the user.

## 3. Check its work

Run all checks through the checks port. Every one must pass. Confirm with
`git diff --name-only <Tests-Locked hash> -- <check files>` that no check changed.

## 4. Commit and finish

1. Commit the app files with a message that says what changed, and the trailers `Intent`,
   `Change`, `Req` (the requirements it serves) and `Ticket` if there is one.
2. Tick the change's steps, add a line to its progress log, and set each requirement in the
   change to `built` in its spec file. Remove any requirement marked `(retire)` from its
   spec, along with code that only served it. (The test writer already removed its checks.)
3. Write `handoff.md` for show: what was built, how to run it, anything surprising.
4. Commit ("Built CH-xxxx", trailers `Intent` and `Change`).
5. Tell the user `/pdlc:show` is next.
