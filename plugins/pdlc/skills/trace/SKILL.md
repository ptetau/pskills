---
name: trace
description: >
  Follows the trace links of pdlc in the two directions. Answers
  "why does this code exist?": from a file and a line to its commit, requirement,
  intent, and ticket. Answers "what did this intent change?": the opposite direction.
  Use when the user says "/pdlc:trace", or asks why some code exists. Also use when the
  user asks what an intent or requirement touched, or what proves a requirement.
---

# pdlc trace

## Goal

Trace answers one trace question in plain words, with file paths and links. It goes from
code to its reason, or from an intent or a requirement to what it touched.

## Inputs

- `pdlc/README.md`, and the question: a file and maybe a line, an intent, or a requirement.
- The git history with its trailers, `pdlc/specs/`, the inbox port, the checks port
  (**find**), and `pdlc/changes/CH-xxxx-name/`.

## Outputs

- The answer first. Then the chain of links: commit, each `Req` with its title and
  status, the `Intent` with its name and status, the `Ticket`, change, and checks.
- Links to `change.md` and the other files of the change where they help.
- A list of each missing link, for example a commit with no trailers.

## Constraints

- `pdlc/README.md` binds, in particular "Writing", "Where pdlc commits", and "Ports".
- Trace changes no file and makes no commit, and invents no link.
- `git log --all --grep "Change: CH-xxxx"` and `git log --all -E --grep "Req:.*<ID>(,|$)"` find
  the commits. A requirement shows the files that those commits changed.

## Done when

Each link from the question has an answer, or is in the list of missing links.
