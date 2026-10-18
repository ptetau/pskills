# Round 3 plan: foreground agents first, lean review packets second

Run `r3-foreground-agents` (agents in the foreground) first. Run `r3-lean-packets` (the
writing rules only in the specification packet) second, and only if budget remains. Both
specs pass `python3 bench/run_experiment.py check`. Both need a small harness change for
their verdict, because the whole-run test cannot see a saving under about 24%.

## The experiments, in order

| Rank | Id | Edit | Lever | Expected saving | Sure? | Cost |
|---|---|---|---|---|---|---|
| 1 | `r3-foreground-agents` | Six find/replace edits. The README, tests, build, verify, and intake skills say: start each agent with `run_in_background: false`, and do not wait with a sleep, a loop, a monitor, or a notification. | more in parallel (no polling) | $0.21 a run (11%) by the harness's own attribution, plus up to 600 s of time | High for the waiting cost. Low for a whole-run verdict. | 6 runs, $11.4. No seeds: the reviewers see the same packets. |
| 2 | `r3-lean-packets` | Four find/replace edits in `make_packets.py` and its test. `DES-writing-style` (3.5k tokens) goes only to the specification packet. | context pack | $0.06 a run (3%). Each other reviewer call costs 22% less. | Medium. The packets of five remits shrink 45%. | 6 runs and the seeds check, $12.3. |

Total: $23.7 of the $25.

### Why this order

- Experiment 1 removes a cause of cost. The main session polled 1 to 41 times a run for
  background agents. In 8 of 16 runs the model already set `run_in_background: false` on
  some calls, and the Agent tool then returned the reply with no polling. So the mechanism
  is proven; only the instruction is missing. It also fixes time: baseline-6 spent 627 s of
  its 835 s in bash wait loops that never matched.
- Experiment 2 is small but clean. The tests, security, quality, compliance, and privacy
  remits never judge writing, yet each packet carries the 14k-character writing spec.
- Both edits change nothing about what pdlc decides, so the effectiveness risk is low.

## What the data says (16 runs)

- Cost splits into cache writes (35%), cache reads (28%), and output (37%). Half of the
  output is thinking. The main session is 71% of a run, the reviewers 23%.
- The reviewer costs $0.058 a call on average: the specification reviewer $0.10 (it reads
  all 21 frames, 19k tokens of images), each other remit $0.04.
- The harness's `is_waiting` misses bash loops such as `for i in $(seq 1 90); do …; sleep 3;
  done`. Baseline-6 shows 1 waiting turn, but it had 6.
- In 4 of 6 baseline runs, the specification remit failed the first verify round. The
  cause was a bare requirement ID (`R4`) in the progress log of the change spec.
- The reviewer sometimes refuses to write `result.md` and hands the text back. It says
  "not allowed to write report files". The main session then writes the file itself. This
  happened in 8 of 16 runs. It is a fidelity defect, not a cost lever (see "Outside the
  loop").

## Power estimate

The six baseline runs cost $1.78, $1.87, $2.49, $1.78, $1.99, $1.36: mean $1.88, SD $0.37
(20%). The whole-run test uses six runs a side and a one-sided permutation test at 10%.
It detects a saving of 24% ($0.45) with 84% power. It detects 16% with 54% power, 11%
with 32%, and 5% with 12%. Neither experiment reaches 16%. So each needs a component
metric:

- Experiment 1: the waiting cost a run. Baseline: $0.08, $0.03, $0.21, $0.19, $0.75, $0.02.
  If the candidate waits nowhere, the chance of luck is 0.1%. If it still waits in two of
  six runs for $0.05 and $0.10, the chance is 2.7%. Harness task H1 adds `--target waiting`.
- Experiment 2: the reviewer cost a call. Today's target mode needs a 42% fall, because it
  uses the range of six per-run averages. A permutation test on the same six values has
  80% power for a 15% fall (harness task H3). The expected fall is 15% to 20%.

## Risks to effectiveness

- Experiment 1: a foreground agent blocks the main session until it returns. The longest
  agent call seen took 55 s, so no timeout applies. Five reviewers in one message returned
  side by side in the runs that set the flag. If a run ends with a `Stop` commit, the gate
  says REGRESSION. The reviewers see the same packets, so the seeds check is not needed.
- Experiment 2: the five remits lose the writing rules for their own prose. The reviewer
  agent already carries a two-line fallback ("short sentences, active voice, describe each
  ID"). The planted defects are all in the diff, the requirements, or the checks, which
  every packet keeps. The seeds check guards this.

## Decision tree

Harness tasks H1 (waiting target) and H2 (wider `is_waiting`) can land while experiment 1
runs. The gate re-runs on the saved `result.json`.

Experiment 1, after `python3 bench/run_bench.py gate bench/baseline.json
bench/results/r3-foreground-agents/result.json --target waiting`:

- SAME OR BETTER: keep the edit. Log it. Then run experiment 2 if at least $13 remains.
- NO GAIN: count the Agent calls with `run_in_background` unset in the six streams. If two
  or more runs ignored the instruction, add the same sentence to step 2 of
  `skills/ship/SKILL.md` and run it again as `r3-foreground-agents-b` (6 runs). That
  spends the budget of experiment 2, which moves to round 4. If every run set the flag and
  the waiting cost stayed, stop and report: the model waits in a way the metric misses.
- REGRESSION: if a run did not finish, read its `Stop` reason. If an agent call was cut
  or timed out, revert and report. If the probes or the project checks failed, revert. The
  edit does not touch what the builder writes, so report the run as noise. Do not retry
  before round 4.
- NEED MORE RUNS (fewer than 5 runs finished the harness): start `r3-foreground-agents-b`
  with the same edits and `"runs": 3`. Freeze both: `python3 bench/run_bench.py freeze
  bench/results/r3-foreground-agents-*/e2e.json --out
  bench/results/r3-foreground-agents/result.json --label r3-foreground-agents`. Gate again.

Experiment 2, only after experiment 1 is settled and H3 is in place:

- SAME OR BETTER: keep. NO GAIN: revert, and do not retry; the saving sits at the floor.
- REGRESSION from the seeds (a missed defect or a false alarm): revert, and name the remit
  whose judgement changed in the log.

## What not to try, and why

- Haiku reviewers (round 1) and the writing check before verify (round 2): done.
- Review by risk that skips privacy: the planted defect `privacy-log` (the usage log) would
  be missed. Skipping compliance alone saves $0.04 a round (2%), which no test can see.
- Fewer or smaller frames: every one of the 21 steps carries its own caption, so "one
  frame per caption" lists every frame. Smaller frames save about 2% and make the frames
  harder to read.
- A cheaper model for the builder, the test writer, or recon: together they cost $0.11 a
  run (6%). Haiku would save at most $0.08 and risk the build.
- A context pack for the main session: the pdlc documents it reads carry about $0.30 a
  run. But a rewrite of seven skills is not a mechanical edit, and it risks behaviour.
- A template hint against bare IDs in the progress log: it aims at round 2's target again.
  It saves about $0.10 a run only if the model complies. No gate mode counts the
  specification reviewer calls a run yet.

## Outside the loop

- Fix `agents/reviewer.md` so that the reviewer always writes `result.md`. Say that the
  file is the required output, and that the guard permits it. Run the seeds check after.
- The frames: 21 frames cost the specification reviewer about $0.05 a call. A later round
  can let the show skill group the steps of one acceptance line under one caption.
