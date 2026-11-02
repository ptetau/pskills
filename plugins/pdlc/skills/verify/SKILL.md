---
name: verify
description: >
  Examines a built pdlc change before the merge. Runs each check. Sends one packet
  for each review remit (specification, security, quality, compliance, privacy) to a
  fresh, independent reviewer, all at the same time. When all pass, marks the
  requirements verified. Then /pdlc:show records the change and proposes the merge. Does
  not merge. Use when the user says "/pdlc:verify", or when a change is built.
---

# pdlc verify

## Goal

A built change is `verified` only when all checks and reviews pass. Else each problem goes
back to one stage. Never merge.

## Inputs

The named change, else the first `building` one with all requirements `built`.

## Outputs

Trailers: `Intent`, `Change`.

- Each round: "Verify CH-xxxx: round <n>": packets (`python3 pdlc/bin/make_packets.py
  CH-xxxx --verify`), results, new intents. One fresh `pdlc:reviewer` per packet.
- Failed: handoff `verify → tests`, `verify → build`, or `verify → acceptance`; "Send
  back CH-xxxx: <stage>".
- Passed: handoff `verify → show`; "Verified CH-xxxx"; change `in
  review`; last change: `git rev-parse HEAD` of **run acceptance** on `Acceptance-Passed:`;
  no ` · proposed` on its "Interface" entries. Next: `/pdlc:show`.

## Constraints

- Each requirement needs a check ("No checks found" fails, except `(retire)`). Run all
  checks and **run earlier acceptance**; the last change, **run acceptance**.
- A "Follow-ups" point needing new behaviour becomes a `new` intent, also with
  `defaults`. Notes start `Awaits approval: found reviewing CH-xxxx (<remit>)`.
- Send a bad check to tests, a failed acceptance check or a remit rule to build, a wrong
  acceptance check to acceptance. `Tests-Locked: acceptance` replaces tests.

## Done when

The change is `verified` or sent back.
