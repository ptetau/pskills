# pdlc config

## Adapters

Each port has one adapter. The name of an adapter is a file in `pdlc/adapters/`.

- inbox: inbox-files
- checks: checks-command
- review: review-agent
- visual: visual-terminal
- delivery: delivery-github
- tracker: none

## Checks

This section gives the command that runs the checks of this project, and the command that
runs only the checks for one requirement. Init writes this section. A project with no
checks yet keeps its checks in `tests/`.

- all: `python3 -m unittest discover -s tests`
- one requirement: `python3 -m unittest discover -s tests -k {req}`
- check folders: `tests/`
- ID form in check names: `underscored`

## Reviews

Each remit is a separate, independent review. The files in `pdlc/reviews/` give the
details of each remit.

- remits: tests, specification, security, quality, compliance, privacy

## Visual

This section tells how to run the app for the visual review. Init writes this section.

- start: none
- url: none

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
