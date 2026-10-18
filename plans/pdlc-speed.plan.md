# Plan: make pdlc faster and cheaper

**Owner:** Patrick Te Tau · **Status:** Rounds 1 and 2 were reverted. Rounds 3, 4, and 5 are kept. Round 6 measures and optimises each section alone.
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

Round 2 used a sixth lever, fewer failed review rounds, which is not in this list. The
data showed that a second round of verify costs more than any change to a single stage.

## Who does what

A stronger model plans the experiments, and cheaper models make the changes and run them.

- **Planner:** a Fable agent. It reads the plan, the harness, and every result. It writes an
  experiment spec for each experiment, and a task for each harness change, in
  `bench/experiments/<round>/`. It does not run anything.
- **Executors:** Haiku agents. One builds a harness task from its exact description. Another
  runs `bench/run_experiment.py check`, `start`, and `wait` on a spec, and reports the output
  word for word.
- **Orchestrator:** the main session. It checks the plan, the diff of each harness task, and
  the saved results before it accepts a report. It applies a kept edit with
  `bench/run_experiment.py apply`.

## The two reference files

- `bench/baseline.json` holds six runs of today's pdlc, from before round 1. It is the floor
  for effectiveness.
- `bench/reference.json` holds six runs of the state after the last kept round (round 5), with
  its planted-defect result. The next experiment compares its cost with this file.
  `bench/reference-after-round-4.json` and `bench/reference-after-round-3.json` are the earlier ones.

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

The chance of luck comes from an exact permutation test of the costs of the runs. Without
`--target`, the gate asks for at least five runs on each side, and six are better. With fewer
runs it prints NEED MORE RUNS, because a few runs can mislead (see round 2).

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

[2026-10-17] Round 2: check the writing before verify (reverted)
Edit: step 3 of `skills/verify/SKILL.md` ran the writing check on the README, the specs, and
          the change spec before it made the packets. The baseline runs ran the check only
          after a failed review.
Result: the first four runs cost $1.43 to $1.60. That is 25% less than three baseline runs,
          with a 3% chance of luck. Three runs on the final wording cost $1.69, $1.71 and
          $2.49. Then three more baseline runs and three more runs of the edit settled it:
          the baseline mean is $1.88 over six runs, and the six runs of the final wording
          cost $2.07 (10% more). The chance that this is luck is 69%.
Gate: NO GAIN. The edit is reverted. The first four runs were luck, and three baseline
          runs were too few.
Fixed: the gate now says NEED MORE RUNS when a side has fewer than five runs. The probes
          now require the form that the intent shows (`--top N FILE`). One run accepted
          only that form, and the old probes failed it for an option that the intent does
          not ask for.
Learned from 16 runs:
          - A run with no extra review round costs $1.36 to $1.71. The cost follows the
            number of agent calls (correlation 0.95). Runs with 9 agent calls cost $1.36
            to $1.71, and runs with 14 to 24 calls cost $2.49 to $3.37. An extra round
            comes from the tests review, the specification review, or the quality review,
            and no one cause stands out.
          - Turns that only wait for a background agent cost $0.17 on average, which is 9%
            of a run. One run spent $0.75 (38%) on 41 such turns.
Next: round 3 starts agents in the foreground, so that the main session does not poll. It
          aims at the waiting turns, which are measured directly and do not depend on the
          review rounds. The gate needs a way to judge the waiting cost, and it needs six
          runs on each side.

[2026-10-17] Round 3: start agents in the foreground (kept)
Plan: a Fable agent planned two experiments (`bench/experiments/round3/`). Haiku agents built
          the harness tasks and ran the experiment. I checked the plan, the code, and the
          saved results myself.
Edit: the README and the tests, build, intake, and verify skills say to start each agent with
          `run_in_background: false`, and not to wait with a sleep, a loop, a monitor, or a
          notification. The README already said "run it in the foreground", and the model
          mostly ignored it.
Result: six runs of the edit had no waiting turn. The baseline runs had 3 to 41, with a mean of
          11.8 turns and $0.24 a run. All six finished, and all 8 probes pass. A whole run
          cost $1.62 against $1.88 (14% less, with a 9% chance of luck), and took 335 s
          against 483 s (31% less).
Gate: waiting target, SAME OR BETTER. The whole-run saving matches the waiting cost that the
          edit removed.
Planted defects: reviewers on Sonnet catch 5 of 5, with no false alarm. The first score was 4
          of 5. The privacy reviewer found the defect but answered in its reply and did not write
          `result.md`, and the check read only the file. The check now reads the reply when there
          is no file, as the main session does in a real run. The saved run was scored again.
Limits: the verify rounds were 3, 1, 1, 1, 2, 2 against 2, 2, 1, 1, 1, 1 in the baseline, so
          the whole-run test alone is borderline. The number of review rounds is the noise to
          beat.
Two mistakes of mine, fixed on the way: the first start of the experiment failed because the
          background runner got a relative spec path, and `wait` kept saying RUNNING. A test of
          `apply` failed in a commit that I pushed, and the next commit fixed it.
Next: round 4. The planner's second experiment, lean review packets, is not run. It would save
          about $0.06 a run (3%), and it costs about $12 to test. The other levers left are the
          context that the main session carries into verify, and the reviewer that does not write
          its `result.md` (the main session writes some of those files itself).

[2026-10-18] Round 4: the writing rules go only to the specification reviewer (kept)
Plan: the second experiment of the Fable plan. A Haiku agent built the gate change (H3) and ran
          the experiment. I checked the diff, the runs, and the numbers myself.
Edit: `make_packets.py` puts `DES-writing-style` (3.5k tokens) only in the packet of the
          specification remit, because only that remit judges writing. A test checks this.
Result: each reviewer call cost $0.054 before and $0.046 after (15% less). All six values of the
          edit are below all six values of the reference, so the chance of luck is 0.1%. A run
          makes 7.7 reviewer calls, so the edit saves about $0.06 (4%) in a run. A whole run
          cost $1.47 against $1.62. All six runs finished, all 8 probes pass, and reviewers on
          Sonnet catch 5 of 5 planted defects, with no false alarm.
Gate: agent target (`pdlc:reviewer`), SAME OR BETTER.
Limits: the other five remits no longer see the writing rules for their own prose. The reviewer
          agent keeps a two-line fallback, and no planted defect tests writing in those remits.
          The saving is small, and the whole-run drop is mostly noise.
Next: the reviewer sometimes answers in its reply and does not write `result.md`, and the main
          session writes the file; the context that the main session carries into verify; and
          the 21 frames that the specification reviewer reads (about $0.05 a call).

[2026-10-18] Round 5: no compliance reviewer when it has nothing to judge (kept)
Plan: a Fable agent planned two experiments and a fallback (`bench/experiments/round5/`). Haiku
          agents built the two harness tasks and ran the experiment. I read the plan and each
          diff, and I checked the runs. I ran the second experiment and held the first (see
          "Held" below).
Edit: when the project lists no compliance rules and the change touches no dependency file,
          `make_packets.py` writes the compliance `result.md` itself ("Result: pass", not
          applicable), and the verify skill starts no reviewer for that remit. A project with
          rules, or a change that touches a dependency file, still gets a reviewer.
Result: six runs made no compliance reviewer call (1.17 a run before). All six finished, and all
          8 probes pass. Reviewers on Sonnet still catch 5 of 5 planted defects, with no false
          alarm. The edit saves one call of $0.027 a run, about 2%, by construction.
Gate: calls of `pdlc:reviewer/compliance`, SAME OR BETTER.
Limits: the six runs cost $1.61 on average against $1.47, which is noise (22% chance of luck).
          The extra review rounds came from the tests, specification, and quality reviews, and
          none from compliance. A change that vendors a library as plain source no longer gets a
          compliance look.
Held: the planner's first experiment replaces the frames that the specification reviewer reads
          with a text transcript, for a terminal recording. It would save about 4% a run. The
          planted-defect check cannot see frames, so nothing measures what it loses in the visual
          review. It waits for a decision, and a planted visual defect would be the guard.
Next: the saving per round is now 2% to 4%, and each test costs about $9. The pools that are left
          are the main session (70% of a run), the extra review rounds (about $0.19 a run), and the
          1-hour cache writes (a Claude Code setting, about a fifth of a run).
[2026-10-18] Sections: measure each stage alone
Plan: a whole run varies too much to show a saving of 2% to 4%. So I split the pipeline into its
          seven stages. `bench/sections/project.bundle` is the project of a reference run. Each
          stage starts and finishes at a known commit in it. `run_bench.py stage` replays one
          stage in a fresh session from its start commit. Haiku built the command from my spec
          and found one bug in the spec. Haiku also ran the replays.
Result: six replays of each stage all finished and passed their stage checks.

          | Stage | Alone | Main session | Agents | In a whole run |
          |---|---|---|---|---|
          | verify | $0.51 | $0.31 | $0.19 | $0.53 |
          | tests | $0.38 | $0.29 | $0.09 | $0.42 |
          | intake | $0.33 | $0.29 | $0.05 | $0.22 |
          | show | $0.23 | $0.23 | none | $0.16 |
          | ready | $0.23 | $0.23 | none | $0.03 |
          | build | $0.20 | $0.17 | $0.03 | $0.15 |
          | change | $0.19 | $0.19 | none | $0.06 |

Findings: a replay of tests, verify, or build varies by 10% to 14%. A whole run varies by 35% to
          60%. An idle session costs $0.03, so nearly all of a stage's cost is its own work. The
          main session costs more than the agents in each stage. The stages alone cost $2.07
          together, and a whole run costs $1.61. So one session for all the stages is cheaper
          than a session for each stage.
Next: a Fable planner maps where each stage's tokens go and writes one or two experiments for
          each stage, with verify, tests, and intake first. Each experiment replays only its
          stage. Six whole runs then check the kept edits together.
```
