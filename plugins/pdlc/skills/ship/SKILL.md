---
name: ship
description: >
  Runs pdlc from start to end. Takes the request of the user (or an intent in progress)
  through intake, ready, and change. Then takes each change through tests, build, show,
  and verify. Stacks the changes, and proposes each merge. Continues with the recommended
  answers. Stops only for contradictions, out-of-scope files, repeated failure, or the end
  of the stack. Continues from the point where it stopped. Use when the user says
  "/pdlc:ship", "ship it", or wants pdlc to run all the way alone.
---

# pdlc ship

Ship runs each pdlc stage in order, with the skill of that stage, until each change of
the intent is proposed.

Read `pdlc/README.md` first, and follow its instructions. Start with its "Before any
work" step.

## 1. Find where to start

- If an earlier run stopped on a change that is not merged, continue with that change
  first. If this run uses `defaults`, take the recommended answer in the stop handoff of
  the change. Give the change two new rounds. A contradiction still waits for the user.
  Then continue with the steps below.
- If the user described something new, start at intake with the words of the user.
- If the user named an intent or a change, start from its current status.
- If not, take the oldest intent that is not `in review`, `done`, `paused`, or
  `cancelled`, and that does not await approval. An intent `in review` has each change
  proposed, and waits for the user. An intent with `Awaits approval:` in its "Notes" is
  new behaviour from a review. Do not take such an intent unless the user names it.

Read intents and changes where they live. Unmerged work is on its branch ("Where pdlc
commits" in `pdlc/README.md`). Then read the latest handoff of the intent or change that
you chose. The handoffs and the statuses show accurately where the work is. Thus, ship can
always continue after a stop, a crash, or a new session.

## 2. Run the stages

For each stage, follow its skill (`pdlc:intake`, `pdlc:ready`, `pdlc:change`,
`pdlc:tests`, `pdlc:build`, `pdlc:show`, `pdlc:verify`). Always use `defaults`. Each stage
starts from the last handoff. At its end, each stage writes the next handoff. Do not carry
details from one stage into the next stage, except through the handoff and the files.

```
intent:          intake → ready → change
for each change: tests → build → show → verify → propose
```

- Each change runs each stage, in order. Do not hold or skip show or verify, also when a
  change has nothing on screen yet.
- Changes stack. When a change is proposed (`in review`), start the tests of the next
  change immediately. Do not wait for merges.
- After each stage, if the project has the dashboard, update the dashboard. If the
  project has a tracker, update the tracker.
- Keep a one-line note for each stage, for the final summary.

## 3. When a stage fails

- If verify fails, go to the stage that the handoff of verify names for each problem:
  tests or build. Then run build, show, and verify. Do not ask the user about a failed
  review.
- If the tests review fails, go back to tests. Then run build, show, and verify.
- Each change can have two rounds. On the third failure, stop.

A round is one failed tests review, one failed verify, or one builder report that a check
is wrong. Fixing a check before it is locked is not a round.
An agent blocked twice also counts as one.

## 4. Stop only for these

1. A contradiction between requirements. (Ready does not take a default answer for a
   contradiction.)
2. A change that needs a file outside its "Files". A missing "Interface" entry is not a
   stop, because the tests stage adds the entry.
3. Three failures of the same stage.
4. The end: each change is proposed.

For everything else, take the recommended answer. Record the answer in the handoff and in
the "Notes" of the intent. These cases are not a stop:

- A missing git remote. The delivery adapter says what to do.
- A choice about how to check, build, or name something. Each stage has a default for the
  choice. For checks that the runner of the project cannot reach, the default is the
  stand-in seam of the change skill.
- The base that a change starts from. The tests skill says which base to use.

Do not stop because the work is long, an agent is slow, or a tool failed. If an agent is
blocked, run the agent once more from the project root ("Starting an agent" in
`pdlc/README.md`).

When you stop, write the reason in one sentence under "Open" in the latest handoff. Also
write what the user must decide, and your recommended answer. The next run takes that
answer. Thus, the answer must obey the rules of pdlc. Do not write "merge over a
failed gate" or "accept a failed review".

Commit everything with the message "Stop CH-xxxx: <why>", or "Stop IN-xxxx: <why>" for an
intent stage. After the commit, `git status --porcelain` must show nothing. Then tell the
user the same reason.

## 5. Finish

Tell the user these items, in a few lines:

- The changes and their pull requests, in stack order, each with its GIF.
- Each answer that you took by default, so that the user can change any of these answers.
- The new behaviour that waits for the approval of the user, with the intent that you
  filed for each item.
- What waits for the user: merging the pull requests of each intent together, from the
  bottom of the stack first, and any manual checks.

Continue until the end of the stack or a stop in the list above. If an outside event ends
the session, `/pdlc:ship` continues from the handoffs when it runs again.
