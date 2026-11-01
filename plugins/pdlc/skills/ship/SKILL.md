---
name: ship
description: >
  Runs pdlc from start to end, alone: each stage of the intent and of each change, with
  the changes stacked and each merge proposed. Continues from the point where it stopped.
  Use when the user says "/pdlc:ship", "ship it", or wants pdlc to run all the way alone.
---

# pdlc ship

## Goal

Ship takes the work through every pdlc stage, with the recommended answers, until each
change of the intent is proposed. Ship stops only for a case that needs the user.

## Constraints

- The session model is a Sonnet 5.5 class model or above ("Core rules" in
  `pdlc/README.md`). On a lower model, ship does no work. Ship tells the user that pdlc
  needs a Sonnet 5.5 class model or above.
- The rules of `pdlc/README.md` hold, and "Bookkeeping on main" runs first.
- Each stage runs through its own skill, with `defaults`, in the order of
  "Stages and handoffs". Each change gets every stage, also `verify` and show with
  nothing on screen.
- Only the handoffs and the files carry information from one stage to the next.
- Changes stack ("Stacked changes"). The tests of the next change start as soon as a
  change is `in review`, with no wait for a merge.
- After each stage, the dashboard and the tracker show the new state, if the project has
  them.
- The work to take is the first of these that exists, in this order:
  - An unmerged change where an earlier run stopped. With `defaults`, ship takes the
    recommended answer of its stop handoff, and gives the change two new rounds. A
    contradiction still waits for the user.
  - New words of the user: intake, with those words.
  - An intent or a change that the user names, from its current status.
  - The oldest intent that is not `in review`, `done`, `paused`, or `cancelled`, and has
    no `Awaits approval:` ("New behaviour needs approval"). An intent `in review` has
    each change proposed, and waits for the user.
- Ship reads each intent and change where it lives ("Where pdlc commits"), and starts
  from the latest handoff. Thus, ship continues after a stop, a crash, or a new session.
- A failed `verify` goes to the stage that its handoff names for each problem: tests,
  acceptance, or build. A failed tests review goes to tests. Then build and `verify` run
  again, and show runs after a passed `verify`. A failed acceptance review goes to
  acceptance. A failed visual review goes to show for a wrong script, and to build for a
  wrong app.
- A failed review is not a question for the user. Each change, and the acceptance stage
  of each intent, has two rounds ("Rounds").
- Ship stops only for these cases:
  - A contradiction between requirements. Ready takes no default for a contradiction.
  - A change that needs a file outside its "Files". A missing "Interface" entry is not a
    stop, because the tests stage adds it to its spec and to the change spec.
  - The third failure of the same stage.
  - The end: each change is proposed.
- Each other case takes the recommended answer, recorded in the handoff and the intent
  "Notes". These cases are not stops:
  - A missing git remote. The delivery adapter says what to do.
  - A choice of how to check, build, or name something. Each stage has a default. For a
    check that the runner cannot reach, the default is the stand-in seam of `pdlc:change`.
  - The base of a change, which `pdlc:tests` gives.
  - Long work, a slow agent, a failed tool, or a blocked agent ("Who does what").
- The recommended answer of a stop obeys the rules of pdlc. "Merge over a failed gate"
  and "accept a failed review" are not answers.

## Inputs

- `pdlc/README.md`, and the skills of the stages, from `pdlc:intake` to `pdlc:verify`.
- The words of the user, or the name of an intent or a change.
- The intents, the changes, their branches, and their latest handoffs.

## Outputs

- The outputs of each stage that ran.
- At a stop:
  - Under "Open" in the latest handoff: the reason in one sentence, what the user must
    decide, and the recommended answer, which the next run takes.
  - The commit "Stop CH-xxxx: <why>", or "Stop IN-xxxx: <why>" for an intent stage, with
    the trailers of "Commits". Then `git status --porcelain` shows nothing.
  - The same reason, for the user.
- At the end, a few lines for the user, from a one-line note on each stage:
  - The changes and their pull requests, in stack order, each with its GIF.
  - Each answer that ship took by default, so that the user can change it.
  - The new behaviour that waits for approval, with the intent filed for each item.
  - What waits for the user: the merge of the pull requests of each intent together, from
    the bottom of the stack, and any manual checks.
- Ship is done at the end of the stack, or at a stop. If an outside event ends the
  session, the next `/pdlc:ship` continues from the handoffs.
