---
name: trace
description: >
  Follows pdlc's trace links in either direction. Answers "why does this code exist?" by
  going from a file and line to its commit, requirement, intent and ticket, and "what did
  this intent change?" by going the other way. Use when the user says "/pdlc:trace", or
  asks why some code exists, what an intent or requirement touched, or what proves a
  requirement.
---

# pdlc trace

Answers trace questions in plain words, with file paths and links.

Read `pdlc/README.md` first. Never change any file.

## From code (a file, and maybe a line)

1. Run `git blame -L <line>,<line> <file>` (or `git log --follow <file>` for a whole file).
2. Read the commit's trailers with `git log -1 --format=%B <commit>`.
3. For each `Req`, find the requirement in `pdlc/specs/` and show its title and status.
4. For the `Intent`, show its name and status from the inbox port.
5. Show the `Ticket` if there is one.

## From an intent

1. Read the intent. List its requirements and its changes, with their statuses.
2. For each change, list its commits: `git log --all --grep "Change: CH-xxxx"`.
3. For each requirement, list the checks that prove it (the checks port's **find**).

## From a requirement

1. Show the requirement, its status and its intents.
2. List the checks that prove it.
3. List the commits that name it: `git log --all --grep "Req:.*<ID>"`, and the files they
   changed.

## Change folders

Each change lives in `pdlc/changes/CH-xxxx-name/`: its spec is `change.md`, and its
review results, GIF and handoff sit next to it. Link to them when they help.

## Say when a link is missing

For example: a commit with no trailers, a requirement with no checks, or an intent that
names a change that doesn't exist. Missing links are useful findings.
