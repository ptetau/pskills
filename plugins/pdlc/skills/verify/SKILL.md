---
name: verify
description: >
  Examines a built and recorded pdlc change before the merge. Runs each check, and sends
  one packet for each review remit (specification, security, quality, compliance,
  privacy) to a fresh, independent reviewer, all at the same time. When all pass, marks
  the requirements verified, and proposes the merge with the GIF. Does not merge. Use
  when the user says "/pdlc:verify", or when a change has its visual review.
---

# pdlc verify

## Goal

The `verify` skill decides if a change is good enough to merge. When it is, the change is
`verified`, and the user gets a proposal to approve. The skill does not merge the change.

## Constraints

- The rules of `pdlc/README.md` hold, and "Bookkeeping on main" runs first. The reviewers
  obey "Who does what".
- The change is the one that the user names, or else the first `building` change that has
  a `review.gif`. The skill works on the branch of the change.
- Through the checks port, all of these pass:
  - The checks of each requirement. Each requirement has at least one check.
    "No checks found" is a failure, except for a `(retire)` requirement. With
    `Tests-Locked: acceptance`, **find** shows these checks in the acceptance file, and
    **run acceptance** runs them.
  - All checks, and **run earlier acceptance**. No check file changed since
    `Tests-Locked`. With `Tests-Locked: acceptance`, the acceptance file did not change
    since `Acceptance-Locked`.
  - For the last change under "Changes" of the intent, **run acceptance**. Its commit
    (`git rev-parse HEAD`) is the pass commit. For an earlier change, a failure is
    expected.
- `python3 pdlc/bin/make_packets.py CH-xxxx --verify` makes the packets, for the remits
  under "Reviews" in `pdlc/config.md` except `tests`, whose result stays. With
  `Tests-Locked: acceptance`, the tests remit has no result, because the acceptance review
  stands for it. The skill does not list the remits itself.
- The script writes the `result.md` of a remit that does not apply, which gets no
  reviewer. In a later round, the script makes re-review packets: the earlier problems and
  the diff since the earlier review. The reviewer judges only these two items.
- Each remit with a packet gets one fresh `pdlc:reviewer`, all in one message. Each
  reviewer gets only the path of its packet, and does not hear what another one found.
- New behaviour ("New behaviour needs approval") is each point under "Follow-ups", and
  each problem that only new behaviour can fix. Examples are a new limit or size cap, a
  guard, another input check, and a new error or status.
- In every round, each such point becomes a `new` intent through the inbox port, in the
  words of the reviewer. Its "Notes" start with
  `Awaits approval: found reviewing CH-xxxx (<remit>)`. A point that an intent asks for
  already gets no new intent.
- With `defaults`, the skill does not approve such an intent. The intent waits for the
  user.
- Each problem of a failed round goes to the stage that fixes it, not to the user:
  - A failed check, or a problem with a check: tests. With `Tests-Locked: acceptance`,
    each check is an acceptance check, and the next line applies.
  - A failed acceptance check: build. A wrong acceptance check: acceptance. A check of an
    earlier intent is wrong when this intent changes its requirement.
  - An acceptance line that is not met, while each check passes: tests first (for a check
    tagged with that requirement), then build. With `Tests-Locked: acceptance`,
    acceptance replaces tests.
  - A remit rule, a design spec, or unsafe code: build, with no new check.
  - Old wording in a title, summary, cross-reference, or note of a spec ("Spec patches"):
    the skill fixes the words now, on this branch. The words match the requirements as
    they are. Only those words change, and no acceptance line.
- A remit that failed only for new behaviour or old wording sends nothing to build. The
  next stage is `verify` again, and that run counts as a round ("Rounds").
- The build stage only makes the code meet an existing acceptance line, design spec, or
  remit rule, inside "Files", with the plainest fix (for example, a clearer message). No
  requirement, acceptance line, or error code changes on the branch of a change.
- The gate of the delivery port passes, except for lines that say `not ready`. These lines
  clear when the last change of the intent is `verified`. For the last change, the gate
  passes with no exception.
- The skill corrects each other problem that the gate names:
  - A conflict with main: a merge of main into this branch. The merge keeps the text of
    main, and the statuses of this branch for its own requirements.
  - A mark that the gate names: the mark becomes `(assumed)`, with the reason outside the
    brackets, and the same meaning.
  - A correction of app files after the acceptance run: the acceptance checks run again,
    and the new commit goes on `Acceptance-Passed:`.
- The proposal goes through the delivery port, with the base of the change as its target.
  Its description fills each section of `pdlc/templates/proposal.md`:
  - The embedded GIF (the adapter says how), and a table of each requirement, its checks,
    and their result.
  - A table of each remit and its result, with a link to each `result.md`.
  - The acceptance file, its lock, and its review. For the last change, the pass commit.
  - The lock commit (with `Tests-Locked: acceptance`, the acceptance lock), and each
    "Manual checks" item for the user to confirm.
  - Each `(assumed)` detail of the change spec and its requirements, one line each.
  - The changes that merge together, and the intents filed for new behaviour.

## Inputs

- `pdlc/README.md`, the change spec, its `handoff.md`, `review.gif`, and the intent.
- The "Reviews" of `pdlc/config.md`, and `pdlc/templates/proposal.md`.

## Outputs

- In every round, the commit "Verify CH-xxxx: round <n>" (`Intent`, `Change`): each
  packet, each result, and each new intent. The findings of a failed round stay in git.
  The progress log names each new intent.
- After a failed round:
  - The `handoff.md` gives each problem to its stage. Its title is `verify → tests`,
    `verify → build`, or `verify → acceptance`. The progress log has a new line.
  - The commit "Send back CH-xxxx: <stage>" (`Intent`, `Change`).
  - The user hears which stage is next, and the skill stops.
- After a passed round:
  - Each requirement of the change is `verified` in its spec file, and the change is
    `in review`. For the last change, the pass commit is on `Acceptance-Passed:`.
  - The commit "Verified CH-xxxx" (`Intent`, `Change`): the results and the statuses.
  - Each gate correction is a commit "Update CH-xxxx: <what>". A merge of main has the
    trailers `Intent` and `Change`.
  - The proposal. When each change of the intent is `in review` or `merged`, the intent is
    `in review`, on the branch of the change.
  - The handoff `verify → user`: the link, and what the user must confirm.
  - The commit "Propose CH-xxxx" (`Intent`, `Change`): the handoff and the intent.
  - The user gets the link.
- The skill is done when the change is proposed, or when a failed round goes back.
