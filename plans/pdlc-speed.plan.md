# Plan: make pdlc faster and cheaper

**Owner:** Patrick Te Tau · **Status:** In progress
**Plan location:** `plans/pdlc-speed.plan.md`

## Goal

pdlc must use fewer tokens and finish sooner, and it must stay as effective as it is today.
When tokens and speed conflict, tokens win.

We do this with a loop. Each round changes one thing in pdlc. A benchmark run then shows if
the change saved tokens, and a gate shows if pdlc got any weaker.

## Decisions

Patrick Te Tau chose these on the `/quiz-visual` page on 17 October 2026.

| Question | Answer |
|---|---|
| Priority | Tokens first |
| Floor | Today's results: each edit must match a frozen run of today's pdlc |
| Loop | Measure, edit, re-measure |
| Levers | Cheaper models, shorter prompts, review by risk, context pack, more in parallel |
| Test bed | A small fixture app |
| How far | The loop, and one round of it |

## What we measure

- **Cost** is the dollar cost that `claude -p` reports for one run, at list prices. It
  weights each kind of token by its price, so it is our measure of token use.
- **Tokens** are the four kinds: input, cache write, cache read, and output.
- **Time** is the wall-clock time of the run, in seconds.
- Each number is also split by stage and by agent. The split finds the costliest stage.

## What "as effective as today" means

Today's results are in `bench/baseline.json`. An edit keeps them when all of these are true:

- All 8 acceptance probes of the intent pass on the change that pdlc proposes.
- The project's own checks pass.
- The merge check of pdlc prints `ok`.
- Each planted defect that today's pdlc catches is still caught. A planted defect is a
  bug that we put into a finished change, in `bench/seeds/`, to see if the reviewers
  find it.

## The benchmark

- The fixture is `wordfreq`, a small Python command that counts words (`bench/fixture-app/`).
  The fixture already holds the `pdlc/` folder that `/pdlc:init defaults` made.
- The intent is one scripted request: add `--top N`, with an exact error message and an
  exit code.
- A run copies the fixture to a throwaway folder and starts `claude -p` with
  `/pdlc:ship defaults <intent>`. The run loads the plugin folder under test.
- The model and the effort are fixed, so each run is comparable.
- `bench/run_bench.py` does all of this and reads the result.

## The gate

`bench/run_bench.py gate BASELINE CANDIDATE` prints one of three verdicts:

- **REGRESSION**: a result from the list above got worse, or the run was more than 50%
  slower. Revert the edit.
- **NO GAIN**: cost did not fall by more than the noise of the runs, and at least 5%.
  Revert the edit.
- **SAME OR BETTER**: nothing got worse and cost fell by more than that. Keep the edit.

## The loop

1. Run the benchmark. The first time, run it twice, to see the noise.
2. Find the costliest stage and the costliest agent in the result.
3. Pull one lever on that stage. Make one edit.
4. Run the benchmark again, and run the gate.
5. Keep the edit or revert it. Write the result in the progress log.

## Steps

1. **Write this plan.** Done when this file exists.
2. **Build the fixture.** Done when `/pdlc:init defaults` has run on it and its result is
   committed.
3. **Build the harness.** Done when a run produces a result file and its unit tests pass.
4. **Measure today's pdlc.** Done when `bench/baseline.json` holds the runs.
5. **Run one round.** Done when one edit has a gate verdict.
6. **Finish.** Done when the repository tests pass and a draft pull request is open.

## What we accept

- The benchmark has one intent. It shows if an edit breaks the main path, and it cannot show
  every effect. More intents and a second app come later.
- Runs of a model differ from each other. The gate uses the spread that it saw, and it
  does not claim more.
- The effort of the benchmark is not the effort of every user. A saving in tokens should
  carry over, but the exact percentage will not.

## Progress log

One entry for each step, newest last.
