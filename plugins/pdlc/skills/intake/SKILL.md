---
name: intake
description: >
  Takes one intent from the pdlc inbox and turns it into spec patches: new jobs, new
  capabilities, new conventions, or changes to existing ones. New requirements are marked
  proposed. Use when the user says "/pdlc:intake", or adds something to the inbox and wants
  it specified.
---

# pdlc intake

> Skeleton. Not built yet. See the plugin's `OUTLINE.md`, sections 4 and 5.

## What it does

Turns an intent into changes to the specs. Never writes code.

## Reads

- One intent, through the inbox port.
- The specs it might touch.

## Writes

- New or changed requirements, marked `proposed`, each listing the intent.
- The intent file: the list of requirements it touched. Status becomes `specifying`.

## Steps

1. Pick the intent. If the user didn't name one, take the oldest `new` intent.
2. Decide what it touches: which jobs, which capabilities, which design specs.
3. If a touched spec is only a stub, send the `recon` agent to that area first.
4. Write the patches straight into the spec files, marked `proposed`.
5. Keep the job-versus-capability line clean. What the user does goes in a job spec. What
   the system can do goes in a capability spec.
6. Update the intent's status and tell the tracker port.

## Stop and ask when

- The intent could mean two different things. Ask, don't guess.
- A patch would change a requirement another open intent is also changing.
