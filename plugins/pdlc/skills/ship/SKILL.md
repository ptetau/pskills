---
name: ship
description: >
  Runs pdlc end to end: takes what the user wants (or an intent in progress) through
  intake, ready and change, then each change through tests, build, show and verify,
  stacking the changes and proposing each merge. Keeps going on recommended answers and
  stops only for contradictions, out-of-scope files, repeated failure, or the end of the
  stack. Picks up where it left off. Use when the user says "/pdlc:ship", "ship it", or
  wants pdlc to run the whole way on its own.
---

# pdlc ship

Runs every pdlc stage in order, using each stage's own skill, until the intent's changes
are all proposed.

Read `pdlc/README.md` first and follow it. Start with its "Before any work" step.

## 1. Find where to start

- If an earlier run stopped on a change that hasn't merged, take it up first. With
  `defaults`, take the recommended answer in its stop handoff and give it two new
  rounds. A contradiction still waits for the user. Then go on below.
- If the user described something new, start at intake with their words.
- If they named an intent or change, start from its current status.
- Otherwise take the oldest intent that isn't `in review`, `done`, `paused` or
  `cancelled`. An intent `in review` has every change proposed and waits on the user.

Read intents and changes where they live: unmerged work is on its branch ("Where pdlc
commits" in `pdlc/README.md`). Then read the latest handoff of the one you picked. The
handoffs and statuses say exactly where things are, so ship can always pick up after a
stop, a crash or a new session.

## 2. Run the stages

Run each stage by following its skill (`pdlc:intake`, `pdlc:ready`, `pdlc:change`,
`pdlc:tests`, `pdlc:build`, `pdlc:show`, `pdlc:verify`), always with `defaults`. Each
stage starts from the last handoff and ends by writing the next one. Don't carry details
from one stage into the next except through the handoff and the files.

```
intent:          intake → ready → change
for each change: tests → build → show → verify → propose
```

- Every change runs every stage, in order. Never hold or skip show or verify, even when
  a change has nothing on screen yet.
- Changes stack: start the next change's tests as soon as the one before it is proposed
  (`in review`). Don't wait for merges.
- After each stage, if the dashboard or a tracker is set up, update it.
- Keep a one-line note per stage for the final summary.

## 3. When a stage fails

- Verify failed on code → back to build, then show and verify again. If no check caught
  the problem, go to tests first, so a check holds the fix.
- Verify or the tests review failed on checks → back to tests, then build, show, verify.
- Allow two rounds per change. On the third failure, stop.

A round is one failed tests review, one failed verify, or one builder report that a check
is wrong. Fixing a check before it is locked is not a round.

## 4. Stop only for these

1. A contradiction between requirements (ready never defaults these).
2. A change needing a file outside its "Files". (A missing "Interface" entry is not a
   stop: the tests stage adds it.)
3. The same stage failing three times.
4. The end: every change proposed.

Everything else takes the recommended answer, recorded in the handoff and the intent's
notes. A missing git remote is not a stop: the delivery adapter says what to do.
Neither is a choice about how to check, build or name something: each stage has a
default for it (for checks the project's runner can't reach, the change skill's
stand-in seam).

When you stop, write why in one sentence under "Open" in the latest handoff, with what
the user needs to decide and your recommended answer. Commit everything, so
`git status --porcelain` shows nothing. Then tell the user the same.

## 5. Finish

Tell the user, in a few lines:

- the changes and their pull requests, in stack order, each with its GIF;
- every answer taken by default, so they can change any of them;
- the reviewers' follow-ups, which they may add as new intents;
- what is waiting for them: approving merges, bottom of the stack first, and any manual
  checks.

If the session gets long, it is safe to stop. Running `/pdlc:ship` again picks up from the
handoffs.
