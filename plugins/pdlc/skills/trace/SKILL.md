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

Trace answers a trace question in plain words, with file paths and links. Trace changes no
file.

## Constraints

- The rules of `pdlc/README.md` hold. Trace changes no file.
- From code: `git blame -L <line>,<line> <file>` gives the commit of a line, and
  `git log --follow <file>` the commits of a full file. `git log -1 --format=%B <commit>`
  gives the trailers.
- Each `Req` leads to its requirement in `pdlc/specs/`, with its title and status. The
  `Intent` leads to its name and status through the inbox port. A `Ticket` is shown.
- From an intent: its requirements and its changes, with their statuses. The commits of
  each change come from `git log --all --grep "Change: CH-xxxx"`. The checks of each
  requirement come from **find** of the checks port.
- From a requirement: the requirement, its status, its intents, and its checks. The commits
  that name it come from `git log --all --grep "Req:.*<ID>"`, with the files that they
  changed.
- Each change is in `pdlc/changes/CH-xxxx-name/`, with `change.md`, the review results,
  the GIF, and the handoff. The answer links to these files when they help.
- Each missing link is a useful finding, and the user hears about it. Examples are a commit
  with no trailers, a requirement with no checks, and an intent that names a change that
  does not exist.

## Inputs

- `pdlc/README.md`, and the question: a file and a line, an intent, or a requirement.
- The git history and its trailers, the specs, the inbox, and the change folders.

## Outputs

- An answer in plain words, with the file paths and the links.
- A list of each missing link.
- No changed file.
