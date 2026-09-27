---
name: verify
description: >
  Verifies a built pdlc change. Runs the checks for each requirement, sends the change to
  an independent reviewer, marks requirements verified when both pass, runs the merge
  check, and proposes the merge for the user to approve. Never merges. Use when the user
  says "/pdlc:verify", or a pdlc build has finished.
---

# pdlc verify

Decides whether a built change is good enough to merge, then asks the user to approve it.

Read `pdlc/README.md` first and follow it. Start with its "Before any work" step.

## 1. Pick the change

Use the change the user named. Otherwise take the change with status `building` whose
requirements are all `built`. Switch to its branch.

## 2. Run the checks

Through the checks port:

- For each requirement in the change, run its checks. Each needs at least one check, and
  all of them must pass. "No checks found" is a failure.
- Run all checks. Everything must pass.

## 3. Review

Through the review port, send the change spec, the branch's diff and commit messages, and
the design specs the change lists.

## 4. If anything failed

Add the failures and review problems to the change spec's progress log, commit, and tell
the user. Say `/pdlc:build` should fix them. Stop here.

## 5. If everything passed

1. Set each requirement in the change to `verified` in its spec file.
2. Set the change to `in review`.
3. Commit with the message "Verified CH-xxxx" and the trailers.
4. Run the gate through the delivery port. It must pass. If it doesn't, something above
   was missed: fix it before going on.
5. Propose the merge through the delivery port. In the description, include a table of
   each requirement, its checks and their result, the review result, and any "Manual
   checks" for the user to confirm.
6. If every change for the intent is now `in review` or `merged`, set the intent to
   `in review`.
7. Tell the tracker port.
8. Give the user the link. Say the change merges when they approve it.

Never merge yourself.
