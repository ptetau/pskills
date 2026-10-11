---
name: build
description: >
  Builds one pdlc change whose checks are written and locked. The pdlc:builder agent
  writes app code until the checks pass. The builder can't change the checks. Commits
  with trace trailers and marks requirements built. Use when the user says "/pdlc:build",
  or a change's tests are locked and reviewed.
---

# pdlc build

Makes a change's locked checks pass, without touching the checks.

Read `pdlc/README.md` first and follow it. Start with its "Before any work" step. Then
read the change's `handoff.md`.

## 1. Pick the change

If the user named a change, use that change. Otherwise, take the first change with status
`building`, in the intent's order. If its change spec's `Tests-Locked:` line has no hash,
stop and say `/pdlc:tests` comes first. Switch to the change's branch.

Each change branch starts from a base branch. If the base branch has new commits since
this branch started (for example a fix after review), merge the base branch in first.
Give the merge commit the trailers `Intent` and `Change`.

## 2. Build

Start the `pdlc:builder` agent with the change spec's absolute path. The builder changes
only the app files listed under "Files", runs the checks, and replies.

- If the builder says a check looks wrong, don't change the check. Send the reason to
  `/pdlc:tests`, which asks the test writer and locks the checks again. Then build again.
- If the builder needs a file that "Files" doesn't list, ask the user. If the user agrees,
  add the file to "Files". Then start the builder again.
- If the same problem comes back a third time, stop and ask the user.

## 3. Check its work

Run all checks through the checks port. Every check must pass. Confirm with
`git diff --name-only <Tests-Locked hash> -- <check files>` that no check changed.

## 4. Commit and finish

1. Commit the app files ("Build CH-xxxx: <what changed>") with the trailers `Intent`,
   `Change` and `Req` (the requirements the change serves). If the change has a
   `Ticket`, add that trailer too.
2. Tick the change's steps. Add a line to its progress log. Set each requirement in the
   change to `built` in its spec file.
3. Remove each requirement marked `(retire)` from its spec. Also remove code that only
   served that requirement. (The test writer already removed its checks.)
4. Write `handoff.md` for show: what you built, how to run it, anything surprising.
5. Commit ("Built CH-xxxx", trailers `Intent` and `Change`).
6. Tell the user `/pdlc:show` is next.
