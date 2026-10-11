---
name: ship
description: >
  Runs pdlc end to end. Takes what the user wants (or an intent in progress) through
  intake, ready and change. Then takes each change through tests, build, show and verify,
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

- If an earlier run stopped on a change that hasn't merged, take that change up first.
  With `defaults`, take the recommended answer in the change's stop handoff. Give the
  change two new rounds. A contradiction still waits for the user. Then go on below.
- If the user described something new, start at intake with the user's words.
- If the user named an intent or change, start from its current status.
- Otherwise, take the oldest intent that isn't `in review`, `done`, `paused` or
  `cancelled`, and doesn't await approval. An intent `in review` has every change
  proposed and waits on the user. An intent whose "Notes" say `Awaits approval:` is new
  behaviour from a review. Never take such an intent up unless the user names it.

Read intents and changes where they live. Unmerged work is on its branch ("Where pdlc
commits" in `pdlc/README.md`). Then read the latest handoff of the intent or change you
picked. The handoffs and statuses say exactly where things are. So ship can always pick
up after a stop, a crash or a new session.

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
- Changes stack. As soon as a change is proposed (`in review`), start the next change's
  tests. Don't wait for merges.
- After each stage, update the dashboard if it is set up, and the tracker if one is set
  up.
- Keep a one-line note per stage for the final summary.

## 3. When a stage fails

- Verify failed → for each problem, go to the stage that verify's handoff names (tests,
  or build). Then go on through build, show and verify. A failed review is never a
  question for the user.
- The tests review failed → back to tests, then build, show, verify.
- Allow two rounds per change. On the third failure, stop.

A round is one failed tests review, one failed verify, or one builder report that a check
is wrong. Fixing a check before the tests stage locks it is not a round. An agent blocked
twice also counts as one round.

## 4. Stop only for these

1. A contradiction between requirements (ready never defaults these).
2. A change needing a file outside its "Files". (A missing "Interface" entry is not a
   stop: the tests stage adds it.)
3. The same stage failing three times.
4. The end: every change proposed.

For everything else, take the recommended answer. Record it in the handoff and the
intent's notes. A missing git remote is not a stop: the delivery adapter says what to do.
A choice about how to check, build or name something is not a stop either. Each stage has
a default for it. For checks the project's runner can't reach, the default is the change
skill's stand-in seam. The base a change starts from is not a stop either: the tests
skill says which base to use.

Never stop because the work is long, an agent is slow, or a tool failed. Run a blocked
agent once more from the project root ("Starting an agent" in `pdlc/README.md`).

When you stop, write why in one sentence under "Open" in the latest handoff. Add what the
user needs to decide, and your recommended answer. The next run takes that answer. So the
answer must be one the rules allow: never "merge over a failed gate" or "accept a failed
review". Commit everything ("Stop CH-xxxx: <why>", or "Stop IN-xxxx: <why>" for an intent
stage), so `git status --porcelain` shows nothing. Then tell the user the same.

## 5. Finish

Tell the user, in a few lines:

- the changes and their pull requests, in stack order, each with its GIF;
- every answer taken by default, so the user can change any of them;
- the new behaviour waiting for the user's approval, with the intent filed for each;
- what is waiting for the user: merging each intent's pull requests together, bottom of
  the stack first, and any manual checks.

Keep going until the end of the stack or a stop above. If something outside cuts the
session off, running `/pdlc:ship` again picks up from the handoffs.
