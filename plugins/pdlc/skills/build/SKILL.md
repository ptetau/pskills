---
name: build
description: >
  Builds one pdlc change whose checks are written and locked. The pdlc:builder agent
  writes app code until the checks pass. The agent cannot change the checks. The skill
  commits with trace trailers, and marks the requirements as built. Use when the user says
  "/pdlc:build", or when the tests of a change are locked and reviewed.
---

# pdlc build

This skill makes the locked checks of a change pass. The skill does not change the checks.

Read `pdlc/README.md` first. Obey the instructions in that file, and start with its
"Before any work" step. Then read the `handoff.md` of the change.

## 1. Select the change

If the user named a change, use that change. If not, use the first change with the status
`building`, in the order that the intent gives. If the `Tests-Locked:` line in the change
spec has no hash, tell the user that `/pdlc:tests` comes first. Then stop. Switch to the
branch of the change.

If the base branch has new commits since this branch started, merge the base branch into
this branch first. For example, the base branch can have a correction after a review.
Give the merge the trailers `Intent` and `Change`.

## 2. Build

Start the `pdlc:builder` agent with `run_in_background: false`. Give the builder the
absolute path of the change spec. The builder changes only the app files under "Files".
Then the builder runs the checks, and sends you a report.

- If the builder says that a check looks incorrect, do not change the check. Send the
  reason to `/pdlc:tests`. That skill asks the test writer, and then locks the checks
  again. Then build again.
- If the builder needs a file that "Files" does not list, ask the user. If the user
  agrees, add the file to "Files". Then start the builder again.
- If the same problem comes back a third time, stop and ask the user.

## 3. Examine the work of the builder

Run all checks through the checks port. Each check must pass. To make sure that no check
changed, run `git diff --name-only <Tests-Locked hash> -- <check files>`.

## 4. Commit and finish

1. Commit the app files with the message "Build CH-xxxx: <what changed>". Add the
   trailers `Intent`, `Change`, and `Req` (the requirements that the commit is for). If
   there is a ticket, also add the trailer `Ticket`.
2. Tick the steps of the change, and add a line to the progress log of the change. In the
   spec file of each requirement in the change, set the requirement to `built`. If a
   requirement has the mark `(retire)`, remove the requirement from its spec. Also remove
   the code that was only for that requirement. (The test writer removed the checks of
   that requirement before this step.)
3. Write `handoff.md` for the show stage. Give what you built, how to run it, and anything
   that you did not expect.
4. Commit with the message "Built CH-xxxx" and the trailers `Intent` and `Change`.
5. Tell the user that `/pdlc:show` is the next step.
