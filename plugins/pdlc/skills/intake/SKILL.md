---
name: intake
description: >
  Takes one intent into pdlc, and makes spec patches from it: new jobs, new capabilities,
  new conventions, or changes to existing specs. Marks each new requirement as proposed.
  Does not write code. Use when the user says "/pdlc:intake", or tells you about
  something to build or change in a pdlc project. Also use when the user names an intent
  in the inbox to specify.
---

# pdlc intake

## Goal

One intent's requirements are in their right specs, as `proposed`. No code.

## Inputs

- `pdlc/README.md` binds: "Core rules", "Bookkeeping on main", "Where pdlc commits",
  "Spec patches", "Questions", "Interfaces", "Commits", "Stages and handoffs".
- Source, first match: new words of the user, a named intent, a named
  `.blueprint.md`, the oldest `new` intent with no `Awaits approval:`.

## Outputs

- Intent: `Status: specifying`; "Requirements" with added, changed, or retiring; handoff
  `intake → ready`.
- Commit "Specify IN-xxxx: <name>" with `Intent: IN-xxxx`, after
  `python3 pdlc/bin/check_handoff.py IN-xxxx --stage intake` exits 0. After three failed
  runs: problems under "Open", handoff `intake → user`, commit.
- Reply: what intake wrote; next `/pdlc:ready`.

## Constraints

- With an unmerged pdlc branch, the intent gets its own branch (delivery port).
  Otherwise `Branch: none`.
- Each detail the intent does not give has `(assumed)`, also in a Given line.
- A failure line gives the exact message and result.
- A `Status: stub` spec first gets `pdlc:recon` with only the project root, the spec path,
  and `deep look`.
- A new job lists its capabilities and design specs.

## Done when

The commit holds each requirement that the intent needs.
