# Plan: make pdlc faster and cheaper

**Owner:** Patrick Te Tau · **Status:** Round 1 was reverted. Round 2 is in progress.
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

- In every run, pdlc finishes: it proposes the change, and the merge check of pdlc prints
  `ok`. A run that ends with a `Stop` commit did not finish.
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
- **NO GAIN**: the cost did not fall by at least 5%, or the fall could easily be luck.
  Revert the edit.
- **SAME OR BETTER**: nothing got worse, the cost fell by at least 5%, and the chance that
  the fall is luck is 10% or less. Keep the edit.

The chance of luck comes from an exact permutation test of the costs of the runs. It needs
at least three runs of the baseline and three of the candidate to reach 5%.

A whole run varies a lot. Three runs of today's pdlc cost $1.78, $1.87, and $2.49, because
the number of review rounds changes. For an edit that aims at one agent, run the gate with
`--target <agent>`. The gate then compares the cost of each call of that agent, which
varies by about 5%. It also prints what the saving means for a whole run. The checks for
effectiveness still apply in full, so a cheaper agent never excuses a run that did not
finish.

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
- The planted defects are five. A reviewer on a smaller model can still miss a subtler
  defect, so each new defect that pdlc misses in real use joins `bench/seeds/`.
- The effort of the benchmark is not the effort of every user. A saving in tokens should
  carry over, but the exact percentage will not.

## Progress log

One entry for each step, newest last.

```
[2026-10-17] Steps 1 to 5: baseline and round 1
Baseline: three runs of today's pdlc, on Sonnet 5.5 at medium effort, cost $1.78, $1.87 and
          $2.49 (mean $2.05). They took 346, 381 and 676 seconds. In each run all 8 probes
          pass and the project's own checks pass. Reviewers on Sonnet catch 5 of 5 planted
          defects, and they raise no false alarm on the clean change.
Where the cost goes: verify costs 43% to 47% of a run, and tests costs 14% to 25%. Reviewer
          calls cost about $0.06 each, and a run makes 7 to 10 of them: 23% to 27% of the
          cost. The rest is the main session. It takes about 45 turns, and each turn reads a
          context that grows from 37k to 125k tokens. Cache reads are about 93% of all tokens.
          Turns that only wait for a background agent cost 1% to 8%.
Round 1 edit: the lever "cheaper models". `agents/reviewer.md` gets `model: haiku`.
Result: two runs cost $1.13 and $1.75 (mean $1.44, 30% less, which is inside the noise of
          a whole run). Each reviewer call costs $0.006, which is 91% less. A run makes 8.3
          reviewer calls on average, so the edit saves about $0.47 (23%) in a run. All 8
          probes pass in both runs. The project's checks pass. Reviewers on Haiku catch 5 of
          5 planted defects, and they raise no false alarm.
Gate: for a whole run, NO GAIN (a 30% fall is inside a noise of 43%). Aimed at
          `pdlc:reviewer`, SAME OR BETTER. This verdict was wrong. See the correction below.
Next: start agents in the foreground, so that the main session does not poll (1% to 8%);
          review by risk, because compliance and privacy answer "not applicable" on this
          fixture; and shrink the context that the main session carries into verify.

[2026-10-17] Correction of round 1
Found: the two runs with Haiku reviewers did not finish. One ended with "Stop CH-0001: three
          failed rounds, quality remit open". The other ended with "Stop CH-0001: the
          specification remit failed three times for writing style". The merge check
          failed in both, because requirements were "built, not verified". All three
          baseline runs finished. The gate checked the probes and the project's own checks,
          which the builder passes even when pdlc stops. It did not check that pdlc
          finished, so it said SAME OR BETTER. Part of the lower cost came from runs that
          stopped early.
Fixed: the gate now fails an edit when pdlc does not finish in a run, when it finished in
          every baseline run. Round 1 now gets REGRESSION, in both modes of the gate.
          The `model: haiku` line is removed from `agents/reviewer.md`.
Learned: in 4 of the 5 runs, the specification review failed the first verify round on
          writing findings: an ID with no description, a sentence of more than 25 words, an
          imperative in a description. No stage runs the writing check before verify, so
          each run pays for a second round of reviews. In one run the writing findings did
          not converge, and pdlc stopped. This is round 2.
```
