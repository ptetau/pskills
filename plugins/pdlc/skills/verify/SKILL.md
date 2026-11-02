---
name: verify
description: >
  Examines a built pdlc change before the merge. Runs each check, and sends one packet
  for each review remit (specification, security, quality, compliance, privacy) to a
  fresh, independent reviewer, all at the same time. When all pass, marks the
  requirements verified. Then /pdlc:show records the change and proposes the merge. Does
  not merge. Use when the user says "/pdlc:verify", or when a change is built.
---

# pdlc verify

## Goal

Pass all checks and reviews, so the requirements are `verified`. Else send each problem
back. Do not merge.

## Inputs

The named change, else the first `building` one with all requirements `built`.

## Outputs

Trailers: `Intent`, `Change`.

- Each round: "Verify CH-xxxx: round <n>": packets
  (`python3 pdlc/bin/make_packets.py CH-xxxx --verify`), results, new intents.
- Failed: handoff `verify → tests`, `verify → build`, or `verify → acceptance`.
  "Send back CH-xxxx: <stage>".
- Passed: handoff `verify → show`. "Verified CH-xxxx".
- Passed: each requirement `verified` in its spec file, the change `in review`.
- Passed, last change: `git rev-parse HEAD` of **run acceptance** on `Acceptance-Passed:`.
- Passed: no ` · proposed` on its "Interface" entries.

## Constraints

- `pdlc/README.md` binds "Bookkeeping on main", "Who does what", "Where pdlc commits", "Acceptance checks", "Spec patches", "New behaviour needs approval", "Rounds", and "Commits".
- Each requirement needs a check ("No checks found" fails, except `(retire)`). Run all
  checks and **run earlier acceptance**. For the last change, **run acceptance**.
- No check file changed since `Tests-Locked` (with `Tests-Locked: acceptance`, no acceptance-file change since `Acceptance-Locked`).
- Each "Follow-ups" point, and each problem that only new behaviour can fix, becomes a `new` intent through the inbox port, also with `defaults`. Its "Notes" start `Awaits approval: found reviewing CH-xxxx (<remit>)`. Such a problem sends nothing to build.
- Send a failed or wrong check to tests.
- Send a failed acceptance check, a remit rule, a design spec, or unsafe code to build.
- Send a wrong acceptance check to acceptance.
- Keep the trailers in one block, as README "Commits" says.

## Done when

The requirements are `verified`, or the change is sent back.
