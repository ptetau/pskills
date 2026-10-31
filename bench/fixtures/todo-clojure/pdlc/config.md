# pdlc config

## Adapters

Each port has one adapter. The name of an adapter is a file in `pdlc/adapters/`.

- inbox: inbox-files
- checks: checks-command
- review: review-agent
- visual: visual-web
- delivery: delivery-github
- tracker: none

## Checks

This section gives the command that runs the checks of this project, and the command that
runs only the checks for one requirement.

- all: `clojure -cp src:test -m todo.run-tests`
- one requirement: `clojure -cp src:test -m todo.run-tests {req}`
- check folders: `test/`
- acceptance file: `test/acceptance/{intent}.acceptance.clj`
- acceptance: `clojure -cp src:test -e "(require 'clojure.test 'clojure.string) (doseq [f (clojure.string/split \"{files}\" #\" \")] (load-file f)) (let [r (clojure.test/run-all-tests #\"acceptance\\..*\")] (System/exit (if (pos? (+ (:fail r) (:error r))) 1 0)))"`
- ID form in check names: `underscored`

## Reviews

Each remit is a separate, independent review. The files in `pdlc/reviews/` give the
details of each remit.

- remits: tests, specification, security, quality, compliance, privacy, visual

## Visual

This section tells how to run the app for the visual review.

- start: `PORT=8080 DATA_FILE=/tmp/todo-visual.txt clojure -cp src -m todo.main`
- url: http://127.0.0.1:8080/

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
