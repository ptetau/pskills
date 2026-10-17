# pdlc config

## Adapters

Each port has one adapter. The name of an adapter is a file in `pdlc/adapters/`.

- inbox: inbox-files
- checks: checks-command
- review: review-agent
- visual: visual-terminal (or visual-web)
- delivery: delivery-github
- tracker: none (or tracker-github-projects, tracker-linear)

## Checks

This section gives the command that runs the checks of this project, and the command that
runs only the checks for one requirement. Init writes this section. A project with no
checks yet keeps its checks in `tests/`.

- all: `...`
- one requirement: `...` (use {req} where the requirement ID goes)
- check folders: `tests/` (where the checks live. Only the test writer is permitted to
  change the checks)
- ID form in check names: `dotted` (`CAP-email.R3`) or `underscored` (`CAP_email_R3`). Use
  `underscored` for runners that do not accept `.` or `-` in names. Write only one of the
  two words.

## Reviews

Each remit is a separate, independent review. The files in `pdlc/reviews/` give the
details of each remit.

- remits: tests, specification, security, quality, compliance, privacy

## Visual

This section tells how to run the app for the visual review. Init writes this section.

- start: none (a command that starts the app, for web apps)
- url: none (where the app answers after it starts)

## Board columns

pdlc uses this section only when a tracker adapter is set. Each line gives a pdlc status
and its board column, for intents and changes.

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

This section is necessary only when a tracker adapter is set. The file of the adapter
tells what goes here.

- none
