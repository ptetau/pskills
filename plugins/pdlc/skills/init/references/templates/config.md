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
requirement. Init fills this in. A project with no checks yet keeps them in tests/.

- all: `...`
- one requirement: `...` (use {req} where the requirement ID goes)
- check folders: `tests/` (where checks live; only the test writer may change them)
- ID form in check names: dotted (`CAP-email.R3`), or underscored (`CAP_email_R3`) for
  runners that don't allow `.` or `-` in names. Write the one word: dotted or underscored.

## Reviews

Each remit is a separate, independent review. `pdlc/reviews/` describes each remit.

- remits: tests, specification, security, quality, compliance, privacy

## Visual

How to run the app for the visual review. Init fills this in.

- start: none (a command that starts the app, for web apps)
- url: none (where the app answers once started)

## Board columns

Applies only when the tracker is not `none`. pdlc status → board column, for intents and
changes.

- new: Backlog
- specifying: Backlog
- paused: Backlog
- ready: Ready
- planned: Ready
- testing: In progress
- building: In progress
- in review: In review
- done: Done
- merged: Done

## Tracker settings

Needed only when the tracker is not `none`. The adapter's file says what goes here.

- none
