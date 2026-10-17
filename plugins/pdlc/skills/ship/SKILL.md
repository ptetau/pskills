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

- If the user described something new, start at intake with the words of the user.
- If the user named an intent or a change, start from its current status.
- If not, take the oldest intent that is not `in review`, `done`, `paused`, or
  `cancelled`. An intent `in review` has each change proposed, and waits for the user.

Read the latest handoff of that intent or change. The handoffs and the statuses show
accurately where the work is. Thus, ship can always continue after a stop, a crash, or a
new session.

## 2. Run the stages

For each stage, follow its skill (`pdlc:intake`, `pdlc:ready`, `pdlc:change`,
`pdlc:tests`, `pdlc:build`, `pdlc:show`, `pdlc:verify`). Always use `defaults`. Each stage
starts from the last handoff. At its end, each stage writes the next handoff. Do not carry
details from one stage into the next stage, except through the handoff and the files.

```
intent:          intake → ready → change
for each change: tests → build → show → verify → propose
```

- Changes stack. When a change is proposed, start the tests of the next change
  immediately. Do not wait for merges.
- After each stage, update the dashboard and the tracker, if the project has them.
- Keep a one-line note for each stage, for the final summary.

## 3. When a stage fails

- If verify fails on the code, run build again. Then run show and verify again.
- If verify or the tests review fails on the checks, run tests again. Then run build,
  show, and verify.
- Each change can have two rounds. On the third failure, stop.

## 4. Stop only for these

1. A contradiction between requirements. (Ready does not take a default answer for a
   contradiction.)
2. A change that needs a file outside its "Files". A missing "Interface" entry is not a
   stop, because the tests stage adds the entry.
3. Three failures of the same stage.
4. The end: each change is proposed.

For all other questions, take the recommended answer. Record the answer in the handoff
and in the "Notes" of the intent. When you stop, say why in one sentence. Also say what
the user must decide.

## 5. Finish

Tell the user these items, in a few lines:

- The changes and their pull requests, in stack order, each with its GIF.
- Each answer that you took by default, so that the user can change any of these answers.
- What waits for the user: the merges to approve, from the bottom of the stack first, and
  any manual checks.

If the session becomes long, you can stop safely. When `/pdlc:ship` runs again, it
continues from the handoffs.
