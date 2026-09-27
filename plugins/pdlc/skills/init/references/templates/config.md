# pdlc config

## Adapters

One adapter per port. The name is a file in `pdlc/adapters/`.

- inbox: inbox-files
- checks: checks-command
- review: review-agent
- visual: visual-terminal (or visual-web)
- delivery: delivery-github
- tracker: none (or tracker-github-projects, tracker-linear)

## Checks

The command that runs this project's checks, and how to run only the checks for one
requirement. Filled in by init.

- all: `...`
- one requirement: `...` (use {req} where the requirement ID goes)
- check folders: `test/` (where checks live; only the test writer may change them)
- ID form in check names: `CAP-email.R3` or `CAP_email_R3` (for runners that don't allow
  `.` or `-` in names)

## Reviews

Each remit is a separate, independent review. Remits are described in `pdlc/reviews/`.

- remits: tests, specification, security, quality, compliance, privacy

## Visual

How to run the app for the visual review. Filled in by init.

- start: none (a command that starts the app, for web apps)
- url: none (where the app answers once started)

## Board columns

Used only when a tracker adapter is set. pdlc stage → board column.

- new: Backlog
- specifying: Backlog
- ready: Ready
- building: In progress
- in review: In review
- done: Done

## Tracker settings

Only needed when a tracker adapter is set. See the adapter's file for what goes here.

- none
