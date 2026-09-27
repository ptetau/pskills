---
name: trace
description: >
  Follows pdlc's trace links in either direction. Answers "why does this code exist?" by
  going from a line to its commit, requirement, intent and ticket, and "what did this intent
  change?" by going the other way. Use when the user says "/pdlc:trace" or asks why some
  code exists or what an intent touched.
---

# pdlc trace

> Skeleton. Not built yet. See the plugin's `OUTLINE.md`, section 6.

## What it does

Answers trace questions in plain words, with links.

## Reads

- `git blame` and commit trailers.
- Specs, intents and change specs.
- Check names tagged with requirement IDs.

## Steps

- **From code:** blame the line, read the commit's trailers, then show the requirement,
  its intents, and the ticket.
- **From an intent:** list its requirements, their changes and commits, and the checks
  that prove each requirement.
- **From a requirement:** show its intents, its checks, and the code its commits touched.

## Rules

- Say plainly when a link is missing, for example a commit with no trailers.
