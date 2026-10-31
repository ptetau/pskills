# Why a pdlc run takes so long and costs so much

A full `/pdlc:ship` run of pdlc 0.4.0 costs $1.96 and takes 628 s on average. In round 7 (pdlc
0.2.x), a run cost $1.48 and took 338 s. Most of the cost has three causes:

1. The main session reads its full context again on each of its 50 turns. The context grows from
   37,000 to 141,000 tokens. Thus, the late stages pay for each early stage.
2. The acceptance stage of 0.3.0 adds $0.40 and 154 s. For an intent with one change, it writes the
   same checks as the tests stage.
3. About 13 turns a run run the writing checker. These turns hold up to 23% of the cost of a run.

The data is 6 runs of 0.3.0 and 6 runs of 0.4.0 in `bench/experiments/declarative/`, and the
reference files of the earlier rounds. `timeline.py` in this folder splits each saved event
stream into time and tokens.

## Where the cost goes

The main session is 72% of the cost, about $1.41 of a run. The agents are 28%.

- A run has 50 main turns (43 to 57). A main turn reads a mean context of 97,000 tokens, so a run
  reads about 4.7 million cached tokens. A main turn costs about $0.03.
- Cache reads are 41% of the cost, cache writes are 34%, and output (with thinking) is 24%.
- The context starts at 37,000 tokens: the system prompt, 41 tools, 35 skills and 4 plugins. The
  cache already holds 28,000 of these tokens, because each session shares them.
- The context grows by stage: intake +23,000 tokens, acceptance +17,000, `verify` +16,000, show
  +12,000, ship +11,000, tests +10,000, build +9,000, change +8,000, and ready +5,000.
- Each new agent writes its starting context of 12,000 to 14,000 tokens into the cache. Thus,
  cache writes are about half the cost of an agent, and output is most of the rest.

| Stage | Round 7 | 0.3.0 | 0.4.0 |
|---|---|---|---|
| ship | $0.060 | $0.065 | $0.059 |
| intake | $0.217 | $0.168 | $0.253 |
| ready | $0.045 | $0.061 | $0.039 |
| change | $0.059 | $0.068 | $0.065 |
| acceptance | none | $0.278 | $0.404 |
| tests | $0.352 | $0.211 | $0.271 |
| build | $0.125 | $0.179 | $0.143 |
| show | $0.163 | $0.160 | $0.148 |
| `verify` | $0.459 | $0.541 | $0.574 |
| **Run** | **$1.48** | **$1.75** | **$1.96** |

## Where the time goes

In 0.4.0, the median run takes 557 s. The median parts are:

| Part | Seconds |
|---|---|
| Agents | 213 |
| Model turns of the main session (about 3.3 s each) | 166 |
| Other tools | 69 |
| Writing checker (`check_writing.py`) | 52 |
| Checks and test runs | 38 |
| GIF recorder | 14 |

The agents run one at a time, except the four `verify` reviewers and the two recon agents of intake. The test writer runs twice: 46 s
in acceptance and 39 s in tests. The reviewers take 21 s in acceptance, 20 s in tests and 27 s in
`verify`. The builder takes 20 s, and recon takes 16 s.

| Stage | Round 7 | 0.3.0 | 0.4.0 |
|---|---|---|---|
| intake | 53 s | 66 s | 83 s |
| acceptance | none | 78 s | 154 s |
| tests | 92 s | 86 s | 103 s |
| build | 29 s | 43 s | 43 s |
| `verify` | 83 s | 98 s | 142 s |
| **Run** | **338 s** | **494 s** | **628 s** |

The `verify` time of 0.4.0 holds one slow run. Its median is 88 s.

## Why the run grew

- **The acceptance stage (0.3.0).** It added $0.40 and 154 s. In 11 of 12 runs, the acceptance
  checks and the component checks cover exactly the same requirements. Both sets run the same
  command through `subprocess`. In the other run, the acceptance checks cover one extra
  requirement. Thus, for an intent with one change, the second set of checks costs the full price
  but adds little.
- **The tests stage got cheaper.** It fell from $0.35 to $0.27, because it now writes only the
  component checks of one change.
- **The declarative skills (0.4.0).** They added $0.21 a run, mostly in the main session: acceptance
  +$0.13, intake +$0.09, and tests +$0.06. Build and ready fell by $0.06 together.
- **The growing context.** Each turn of a late stage reads the work of each early stage. A fresh
  session for each stage would read only the shared 37,000 tokens, the files of that stage, and
  its own turns. An estimate with 10,000 tokens to read the files again gives a saving of 17% of
  a run (15% to 19%), about $0.33.

## Waste in single runs

- **The writing-fix loop.** The main session runs `check_writing.py` itself about 13 times a run.
  It edits the text, then runs the checker again. These turns hold 23% of the cost of a run (15%
  to 27%), and their model time is about 51 s a run. Some of these turns also do other work, so
  23% is the upper limit. The commit hook already runs the same check after each commit.
- **A command that waited for input.** In run 6 of 0.4.0, the command `cat > $TMPDIR/ed.sh` had
  no input. The Bash tool moved it to the background after 120 s. After its work, the session
  waited about 310 s more for that task. This one command cost 430 s.
- **Second `verify` rounds.** 3 of 6 runs of 0.3.0 and 1 of 6 runs of 0.4.0 needed a second round.

## Options to discuss

| Option | What changes | Estimated saving | Notes |
|---|---|---|---|
| A. One set of checks for a one-change intent | When an intent has one change, the acceptance checks are also the component checks. One test writer and one review. | $0.25 to $0.40 and 80 to 150 s a run | An intent with more changes keeps both sets. The 0.3.0 reason for acceptance checks (a check needs a later change) applies only there. |
| B. A fresh context for each stage | Ship runs each stage in its own session, with the handoff as the link. | About 17%, $0.33 a run | Each stage skill can run in its own fresh context with `context: fork`. A forked stage can still start its test writer and reviewer, because a subagent can start subagents, up to three layers deep. The stage then reads its inputs from the handoff files. |
| C. One writing pass for each stage | A stage runs the checker once on all the files that it changed, and fixes all findings in one edit. Or the commit hook is the only check. | Part of the 23% (up to $0.45), and up to 50 s a run | The specification review fails writing problems, so the text must still pass. |
| D. Fewer small turns in acceptance and `verify` | One script makes the packets, runs the checks and records the results. | Not measured | Each main turn of a late stage costs about $0.03. |
| E. No command that waits for input | A rule, or a hook that stops a command such as `cat > file` with no input. | Rare, but 430 s in one run | Small. |

Options A and C need only skill and script changes. Option B needs a front-matter setting in each stage skill, and a check that each stage reads all its inputs from files.

## How the cost is split

The CLI reports the total cost and the total tokens of a run. The bench splits that total between
the stages by the tokens of each message in the event stream. But the stream gives each message
its output tokens at the start of the message, so it holds almost no output tokens. `timeline.py`
estimates the output of each message from its text, its tool input and its thinking tokens. Then
it scales the estimates to the reported total.

With that split, `verify` costs about $0.08 less
than the bench gives, and each other stage changes by $0.03 or less. The tables use the bench
split, so that all rounds use the same method.

## Bench fixes

The analysis found two faults in `bench/run_bench.py`. Both are fixed, with tests.

- Since 0.3.0, the bench counted no run as finished. The merge check prints nothing on an intent
  branch, and the bench counted that empty output as a failure.
- The bench counted the test writer and the reviewer of the acceptance stage under the tests
  stage. Now the prompt of the agent decides: a change path is the tests stage, and an intent or
  acceptance path is the acceptance stage. The result files in `bench/experiments/declarative/`
  hold the corrected split.

## Commands

```
python3 bench/run_bench.py reanalyse <results>/v040-N
python3 bench/experiments/cost-time/timeline.py <results>
```

`timeline.py` writes `timeline.json` in the results folder, and prints the main numbers of this
note for each label. For each run, the file gives the cost of each stage, and the main-session
time of each stage by model and by tool.
