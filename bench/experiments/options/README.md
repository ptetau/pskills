# Five options to cut the cost and the time of a pdlc run

`bench/experiments/cost-time/README.md` names five options (A to E). Each option was built on
its own branch from pdlc 0.4.0 and measured with 3 full runs of `/pdlc:ship`. The fixture
app and the intent are the same as in `bench/experiments/declarative/`.

The runs of 2026-10-31 cost about 6% more than the 0.4.0 runs of 4 days before, on the same
plugin. The CLI changed from 2.1.314 to 2.1.316 between them. Thus, 3 control runs of 0.4.0 on
the same day (`k.json`) are the reference for each option.

## Result

| Option | Runs | Mean cost | Median time | Probes | `verify` rounds | Decision |
|---|---|---|---|---|---|---|
| Control: 0.4.0 | 3 | $2.09 | 514 s | 8 of 8 | 1, 2, 1 | |
| A. One set of checks for an intent with one change | 3 | $1.80 (-14%) | 400 s (-22%) | 8 of 8 | 2, 1, 1 | Keep |
| B. A new agent for each stage, with nested agents | 1 | $3.13 (+50%) | 794 s | 8 of 8 | 2 | Drop |
| C. The commit hook is the only writing check | 3 | $2.06 (-2%) | 505 s (-2%) | 8 of 8 | 1, 1, 1 | Keep |
| D. A script for the fixed steps | 3 | $2.19 (+5%) | 548 s (+7%) | 8 of 8 | 2, 1, 1 | Drop |
| E. A hook that stops a command that waits for input | 0 | | | | | Keep |
| 0.5.0: A, C and E together | 3 | $1.69 (-19%) | 392 s (-24%) | 8 of 8 | 2, 1, 2 | |

Three runs give only a rough result. In 6 runs of 0.4.0, the cost of a run went from $1.75 to
$2.29. One extra review round costs about $0.40. The chance that the fall of A is luck is 15%.

## 0.5.0: A, C and E together

pdlc 0.5.0 has options A, C and E. Its 3 runs cost $1.73, $1.44 and $1.91, and each run passed
8 of 8 probes. Against the 3 control runs, the cost falls by 19%, and the chance that the fall
is luck is 10%. Against all 9 runs of 0.4.0, the cost falls by 15%, and that chance is 4%. Two
of the 3 runs needed a second `verify` round, and they still cost less than the control. The
stdin hook stopped no command in these runs.

## After 0.5.0: the recording after `verify`

The change stages then became tests → build → `verify` → show. Show records the GIF only
after `verify` passes, and then proposes the merge. The 3 runs (`reorder.json`) cost $1.59,
$2.09 and $2.42, and each run passed 8 of 8 probes.

- `verify` and show together cost $0.73, against $0.77 in 0.5.0. Show costs more, because
  it now makes the proposal. The specification reviewer costs about half as much, because
  it no longer reads the frames.
- The higher mean ($2.03) comes from stages that this change does not touch. The
  acceptance stage cost $0.48 in place of $0.32, and one run needed 3 builder calls.

## After 0.5.0: a separate visual review

A separate `visual` review then took the place of the frame check of the specification
review. It runs in show, after the recording, and before the proposal. The merge gate moved
to show too. The 3 runs (`visual.json`) cost $1.86, $1.73 and $2.09, a mean of $1.89. Each
run passed 8 of 8 probes, and the median time was 429 s.

- The visual reviewer ran once in each run, and cost $0.08 to $0.10. Each review passed.
- Show now costs about $0.41: the recording, the visual review, the gate, and the proposal.
  `verify` costs about $0.43, with 2, 1 and 3 rounds.
- Each reviewer counted the frames against the acceptance lines, and found the last frame
  with all checks passing. Two reviewers put a weak frame under "Notes" as a wish. In one,
  the exit code on screen came from `wc`, not from the app. In the other, the input file
  was too small to show the limit of `--top`.

## A. One set of checks for an intent with one change

The tests stage fell from $0.27 to $0.07 a run, as the plan expected ($0.18 to $0.24 less).
That stage now starts no test writer and no reviewer. Run 1 cost $2.29, because the acceptance
review and `verify` each needed a second round. The other two runs cost $1.56 and $1.55.

The checks of the new feature are now only in the acceptance file, for example
`acceptance/acc_IN_0001.py`. The "all" command of the project does not run that file. pdlc runs
it in each later `verify`, through the acceptance command.

## B. A new agent for each stage

In this design, `/pdlc:ship` starts a `pdlc:stage` agent for each stage. B failed in two ways:

- By default, an agent that a subagent starts has no Agent tool. The first run stopped at the
  acceptance stage, because the stage agent could not start the test writer
  (`b-plain.json`). Nested agents need `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=3`.
- With that setting, the run passed, but it cost 50% more (`b-nested.json`). Each new agent
  reads the README, the config, the skill and the specs again, and writes them into the cache.
  The ready stage cost $0.19 in place of $0.05, and the change stage cost $0.16 in place of
  $0.07. The run read 6.5 million cached tokens and wrote 627,000.

The estimate of a 17% saving assumed that a new stage reads about 10,000 tokens again. A stage
agent reads much more before it starts its work. Two more runs could not change the decision,
so B has 1 run. `patches/b-stage-agents.patch` holds the change.

## C. The commit hook is the only writing check

The runs of the checker in the main session fell from 13.2 to 3.0 a run. Two runs did not run
it. But the main session made about 57 turns, against 50 in the 0.4.0 runs. The hook reports
up to 10 findings after one commit. The model then fixes each finding with its own edit, and
amends the commit. Thus, the fix turns moved from before the commit to after it.

C stays,
because its cost and time are the same and its rule is simpler. No run left a writing finding.

A next step: a writer with several findings in one file writes the full file again in one
call.

## D. A script for the fixed steps

Each run used `steps.py lock`, `checks` and `verified`, and each call gave a short result. The
acceptance stage made 11.3 main turns, against 12.0. The plan expected $0.06 to $0.15 less a
run. That is less than one review round, so 3 runs cannot show it.

The runs showed no saving,
and the script has 458 lines. Thus, D is dropped. `patches/d-steps-script.patch` holds the
change.

## E. A hook that stops a command that waits for input

The fault occurred in 1 of 12 earlier runs, so 3 runs cannot show it. The hook ran on each of
the 546 Bash commands of those 12 runs. It stopped only the command `cat > $TMPDIR/ed.sh` of
run 6 of 0.4.0, which waited 430 s. The 25 unit tests in `plugins/pdlc/tests/test_stdin_hook.py`
cover the other cases.

## Files

- `k.json`: the 3 control runs of 0.4.0.
- `a.json`, `c.json`, `d.json`: the 3 runs of each option.
- `b-plain.json`: the run of B without nested agents. `b-nested.json`: the run of B with them.
- `v050.json`: the 3 runs of 0.5.0.
- `reorder.json`: the 3 runs with the recording after `verify`.
- `visual.json`: the 3 runs with the separate visual review.
- `patches/`: the changes of B and D, which 0.5.0 does not have.

The plugin commits in the files are local branches. Only the commits of A, C and E are on the
main line.
