# pdlc config

## Adapters

One adapter per port. The name is a file in `pdlc/adapters/`.

- inbox: inbox-files
- checks: checks-command
- review: review-agent
- delivery: delivery-github
- tracker: none

## Checks

The command that runs this project's checks, and how to run only the checks for one
requirement. Filled in by init.

- all: `...`
- one requirement: `...` (use {req} where the requirement ID goes)

## Board columns

Used only when a tracker adapter is set. pdlc stage → board column.

- new: Backlog
- specifying: Backlog
- ready: Ready
- building: In progress
- in review: In review
- done: Done
