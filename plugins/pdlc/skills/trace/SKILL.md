---
name: trace
description: >
  Follows the trace links of pdlc in the two directions. Answers
  "why does this code exist?": goes from a file and a line to its commit, requirement,
  intent, and ticket. Answers "what did this intent change?": goes in the opposite
  direction. Use when the user says "/pdlc:trace", or asks why some code exists. Also use
  when the user asks what an intent or requirement touched, or what proves a requirement.
---

# pdlc trace

This skill answers trace questions in plain words, with file paths and links.

Read `pdlc/README.md` first. Do not change any file.

## From code (a file, and maybe a line)

1. Run `git blame -L <line>,<line> <file>`. For a full file, run
   `git log --follow <file>`.
2. Read the trailers of the commit with `git log -1 --format=%B <commit>`.
3. For each `Req`, find the requirement in `pdlc/specs/`. Show its title and its status.
4. For the `Intent`, show its name and its status from the inbox port.
5. If there is a `Ticket`, show the ticket.

## From an intent

1. Read the intent. List its requirements and its changes, with their statuses.
2. For each change, list its commits: `git log --all --grep "Change: CH-xxxx"`.
3. For each requirement, list the checks that prove the requirement (the **find** of the
   checks port).

## From a requirement

1. Show the requirement, its status, and its intents.
2. List the checks that prove the requirement.
3. List the commits that name the requirement: `git log --all --grep "Req:.*<ID>"`. Also
   list the files that these commits changed.

## Change folders

Each change is in its folder `pdlc/changes/CH-xxxx-name/`. The spec of the change is
`change.md`. The review results, the GIF, and the handoff are in the same folder. Link to
these files when they help the user.

## Say when a link is missing

Tell the user about each missing link. Examples are a commit with no trailers, a
requirement with no checks, or an intent that names a change that does not exist. A
missing link is a useful finding.
