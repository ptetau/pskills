---
name: verify
description: >
  Verifies a built pdlc change. Runs the tagged tests, sends the diff to an independent
  reviewer agent, marks requirements verified when both pass, and opens a PR for the user
  to approve. Use when the user says "/pdlc:verify" or a build has finished.
---

# pdlc verify

> Skeleton. Not built yet. See `pdlc/OUTLINE.md` section 7.

## What it does

Decides whether a built change is good enough to merge. Then asks the user to approve it.

## Reads

- The change spec, the diff, and the design specs it lists.

## Writes

- Requirement status `verified`, on the change's branch.
- A PR, through the delivery port, with a table of requirements, tests and results.

## Steps

1. Run the tests through the tests port. Every requirement in the change needs at least one
   passing test tagged with its ID.
2. Send the change spec, diff and design specs to the review port. The reviewer checks
   scope, acceptance, conventions and trailers.
3. If either fails, send the change back to `build` with the findings.
4. If both pass, mark the requirements `verified` and open the PR.
5. List any `manual check` items for the user to confirm when they approve.
6. Tell the tracker port.

## Rules

- Never merge. The user approves the merge.
