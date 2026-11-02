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
  "Spec patches", "Questions", "Interfaces", "Commits", "Stages and handoffs",
  "New behaviour needs approval".
- Source, first match: new words of the user, a named intent or `.blueprint.md`, the
  oldest `new` intent with no `Awaits approval:`. Argument `defaults`.

## Outputs

- Intent: `Status: specifying`. "Requirements": each requirement whose text intake
  changed, with one word only: added, changed, or retiring. Handoff `intake → ready`.
- Commit "Specify IN-xxxx: <name>" with `Intent: IN-xxxx` in the last paragraph, with each
  other trailer, after `python3 pdlc/bin/check_handoff.py IN-xxxx --stage intake` exits 0. After three failed
  runs: problems under "Open", handoff `intake → user`, commit.
- Reply: what intake wrote. Next: `/pdlc:ready`.

## Constraints

- With an unmerged pdlc branch, the intent gets its own branch (delivery port).
  Otherwise `Branch: none`.
- Each detail not in the intent has `(assumed)`, also in a Given line, a new
  `DES-errors` code, and an edge-case result.
- Each `(assumed)` decision has its own line in "Decided on defaults" and in "Notes", in
  the template form.
- The summary of each spec ("Who and why" or "What it is for") names each requirement
  that intake adds.
- A failure line gives the exact message and result.
- A `Status: stub` spec first gets `pdlc:recon` with only the project root, spec path,
  and `deep look`.
- A new job lists its capabilities and design specs.

## Done when

The commit holds each requirement that the intent needs.
