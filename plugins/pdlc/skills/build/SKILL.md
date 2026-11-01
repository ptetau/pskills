---
name: build
description: >
  Builds one pdlc change whose checks are written and locked. The pdlc:builder agent
  writes app code until the checks pass, and cannot change the checks. Commits with trace
  trailers, and marks the requirements as built. Use when the user says "/pdlc:build", or
  when the tests of a change are locked and reviewed.
---

# pdlc build

## Goal

Build makes the locked checks of one change pass, with app code from the builder. Build
does not change the checks.

## Constraints

- The rules of `pdlc/README.md` hold, and "Bookkeeping on main" runs first. The builder
  obeys "Who does what".
- The change is the one that the user names, or else the first `building` change in the
  order of the intent. Build works on the branch of the change.
- A `Tests-Locked:` line with no hash and no `acceptance` stops the skill, and the user
  hears that `/pdlc:tests` comes first.
- When the base branch has new commits since this branch started (for example, a
  correction after a review), build first merges the base into this branch. The merge has
  the trailers `Intent` and `Change`.
- The `pdlc:builder` agent gets the absolute path of the change spec, and of each
  acceptance file that must pass:
  - The file of each other intent whose `Acceptance-Passed:` holds a hash.
  - For the last change under "Changes" of the intent, the file of this intent.
- The builder changes only the app files under "Files", runs the checks, and reports.
- A check that the builder calls incorrect stays as it is. The reason goes to
  `/pdlc:tests`, which asks the test writer and locks again, and then build runs again. For
  an acceptance check, the reason goes to `/pdlc:acceptance`. With `Tests-Locked:
  acceptance`, each check is an acceptance check.
- A file that the builder needs outside "Files" is a question for the user. On a yes, the
  file goes into "Files", and the builder runs again.
- The same problem a third time stops the skill, and build asks the user ("Rounds").
- After the builder, all checks and the acceptance checks of "Acceptance checks" pass,
  through the checks port.
- No check changed since the lock:
  `git diff --name-only <Tests-Locked hash> -- <check files>` shows nothing. With
  `Tests-Locked: acceptance`, the acceptance file did not change since `Acceptance-Locked`.

## Inputs

- `pdlc/README.md`, the shared rules.
- The change spec, its `handoff.md`, and its base branch.
- The intent, and the intents whose `Acceptance-Passed:` holds a hash.

## Outputs

- The commit "Build CH-xxxx: <what changed>": the app files. Its trailers are `Intent`,
  `Change`, `Req` (the requirements of the commit), and `Ticket` when there is a ticket.
  Keep the trailers in one block, as README "Commits" says.
- The ticked steps of the change, and a new line in its progress log.
- Each requirement of the change is `built` in its spec file. A `(retire)` requirement
  leaves its spec, with the code that served only that requirement. The test writer
  removed its checks before. Each "Interface" entry with ` · retiring` in the scope spec
  leaves the spec too.
- The handoff `build → verify`: what build made, how to run it, and anything unexpected.
- The commit "Built CH-xxxx" with the trailers `Intent` and `Change`: the specs, the
  change spec, and the handoff.
- For the user: `/pdlc:verify` is next.
- Build is done when every check that it runs passes, and no check changed since the lock.
