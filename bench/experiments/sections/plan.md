# Round 6 plan: cut the cost of each stage alone

Run five stage experiments. Each spec is in `bench/experiments/sections/`, passes
`python3 bench/run_experiment.py check`, has green plugin tests, and adds no writing
finding. All five touch different files, so all five can run at the same time. Run at most
three at the same time, so that the rate limit does not stop a replay.

| Rank | Id | Stage | Edit | Lever | Expected saving | Sure? | Cost |
|---|---|---|---|---|---|---|---|
| 1 | `s6-readme-short-forms` | show | Four edits. README rule 9 (the commit trailers) and rule 10 (the writing rules) get a short form. The handoff and proposal templates ask for a description next to each ID. | shorter prompts | Show: $0.027 (11%). Verify: $0.025 (5%). Tests: $0.01 (3%). A whole run: $0.06 to $0.08 (4% to 5%). | Medium. The model decides whether to skip the full read of the rules. The hint aims at the finding that is 2 of 3 findings. | 6 show replays, $1.4 |
| 2 | `s6-review-packets-lean` | verify | Eight edits. `make_packets.py` gives each acceptance line once, shows a new file once, and sends `DES-pdlc-check-tagging` only to the tests remit. Four tests. | context pack | Code packets 22% smaller, the specification packet 12%, the tests packet 32% (measured on the frozen project). Verify: $0.015 (3%). Tests: $0.008 (2%). A whole run: $0.03 (2%). | High on the mechanism. The seeds guard the remits. | 6 verify replays and the seeds, $4.5 |
| 3 | `s6-verify-fewer-turns` | verify | Three edits. The verify skill runs the checks and makes the packets in one command. The inbox adapter gives the shape of an intent file, and the skill files a follow-up intent in one command. | fewer turns | Verify: 2 turns, $0.03 (6%). A whole run: $0.03 (2%). | Medium to low. The number of turns is the choice of the model. | 6 verify replays, $3.0 |
| 4 | `s6-tests-one-red-run` | tests | One edit. The red step runs all the checks once, with the verbose flag, in place of one run for each requirement and then a run of all. | fewer turns | Tests: 1 turn, $0.018 (5%). A whole run: $0.02 (1%). | Medium. | 6 tests replays, $2.3 |
| 5 | `s6-intake-recon-brief` | intake | Three edits. Intake gives recon a fixed ask. Recon replies with the requirements only, and does not read the writing rules. | shorter prompts | Intake: $0.025 (7%). A whole run: $0.02 (1.5%). | Medium to low. The spread of intake (11%) hides a 7% saving in half of the cases. | 6 intake replays, $2.0 |

Total: $13.2 of the $16 for experiments. The reserve is $6.8: the $4 that the budget keeps,
plus $2.8. A top-up of three verify replays costs $1.5, and three show replays cost $0.7.

## Words used here

- A **turn**: one message of the main session, with its tool calls. Each turn reads the
  whole context again from the cache.
- A **write**: a token that enters the context for the first time. A write costs 20 times
  a cached read, because every cache write in these runs is a 1-hour write.
- The **start-up**: the first turn (8k to 10k written tokens) and the read of
  `pdlc/README.md` (5k tokens).
- A **unit**: the weight that the harness gives a token (input 1, 1-hour write 2, cached
  read 0.1, output 5). In these replays, 1,000 units cost about $1.45.

## The section map

Each stage pays a start-up of $0.045 to $0.06 (turn 1 at $0.028 to $0.03, the README at
$0.02 to $0.025 with its reads). Then the cost follows the number of turns: a turn at a
context of 50k to 65k tokens costs $0.01 before its own output. The main session writes
30k to 37k tokens into the cache in each stage, and 14k of them are the start-up.

| Stage | Cost | Main session (writes, reads, output) | Agents | Turns |
|---|---|---|---|---|
| verify | $0.507 | $0.263 ($0.105, $0.112, $0.046) | $0.244 | 14.8 |
| tests | $0.378 | $0.239 ($0.099, $0.106, $0.034) | $0.140 | 14.0 |
| intake | $0.334 | $0.251 ($0.126, $0.062, $0.063) | $0.083 | 7.5 |
| show | $0.234 | $0.234 ($0.105, $0.084, $0.045) | none | 10.5 |
| ready | $0.227 | $0.227 ($0.105, $0.066, $0.056) | none | 7.8 |
| build | $0.200 | $0.155 ($0.074, $0.059, $0.021) | $0.045 | 8.7 |
| change | $0.193 | $0.193 ($0.100, $0.056, $0.037) | none | 7.2 |

The agent column comes from the `modelUsage` of the result event, less the `usage` of the
main session. The harness gives verify agents $0.194, because the stream carries the
output tokens of the first chunk of each message only. See "Notes on the harness".

### Verify ($0.507)

The four reviewer calls cost $0.244: the specification reviewer about $0.125, and
security, quality, and privacy about $0.040 each. The waste, from the largest item:

1. The specification reviewer reads 23 frames of 1000 by 640 pixels, about 850 image
   tokens each: $0.058 (11%). In 2 of 6 runs the reviewer read 9 frames and still passed.
   A verify replay cannot measure a change to the recorder, because the frames are frozen
   in the snapshot. See "Outside the stage loop".
2. The security reviewer finds the same follow-up in 5 of 6 runs: `int()` refuses a
   number of more than 4,300 digits. The main session then files intent IN-0002 (huge top
   value) in 3 turns. For that, it reads the inbox adapter, the intent template, and often
   `DES-pdlc-commit-trailers`. Cost: $0.054 on average (11%). This is a design feature.
   Rank 3 (fewer turns in verify) makes the filing cheaper.
3. The main session runs `check_writing.py` on the proposal and the handoff, and then
   fixes the findings: 1.8 turns, $0.03 (6%). No reviewer judges these two files. The
   findings are bare IDs ("R5, R7, and R8") and long sentences. Rank 1 (README short
   forms) aims at a first draft that passes.
4. Each packet shows each acceptance line twice: in the change spec and in "The
   requirements, in full" (3.3k characters). The three code packets also carry
   `DES-pdlc-check-tagging` (1.2k characters), which only the tests remit judges. In four
   packets this is 4.5k tokens: $0.015 (3%). Rank 2 (lean packets) removes it.
5. The start-up: $0.053 (10%). Not a pdlc lever, except the skill text itself (1.8k
   tokens, $0.005).

### Tests ($0.378)

The test writer and the tests reviewer cost $0.14 together (about $0.07 each). The tests
packet is 30k characters, because the diff of the new check file repeats its full text
(6.4k characters). The waste in the main session:

1. The red run takes two turns: a summary run, then a verbose run. $0.035 (9%). Rank 4
   (one red run) asks for one verbose run.
2. To start the branch, the model reads the delivery adapter, `DES-pdlc-branches`, and
   `DES-pdlc-commit-trailers`: 1 to 2 turns, $0.03 (8%). The commands belong to the
   adapter, so the skill must not inline them. Rank 1 (README short forms) gives the
   trailer lines in the README, which removes one reason for the read.
3. Fixes to the handoff after it is written: 0.8 turns, $0.012 (3%). Tests runs no
   writing check, so these fixes come from the model's own re-read.
4. The tests packet repeats the new check file: 1.7k tokens, $0.006 (2%). Rank 2 (lean
   packets) shows a new file once.
5. The start-up: $0.05 (13%).

### Intake ($0.334)

Intake writes the most: 7.3k output tokens in the main session ($0.063) for the spec, the
intent, and the reply. The recon call costs $0.083 (25%). The waste:

1. Recon reads `DES-writing-style` (14k characters, 3.7k tokens) in every run: $0.012
   (3.5%). Rank 5 (a brief recon) gives recon the two rules that matter and says not to
   read the file.
2. The reply of recon is 4.5k to 9.6k characters. The reply is longest when the main
   session asks for extras (a summary of the parsing, the exit codes, the template). The
   avoidable part is about $0.01 (3%). Rank 5 fixes the ask.
3. The main session reads every design spec in step 2, with the writing rules: 5.5k
   tokens, $0.02 (6%). Intake writes specs, so the rules are needed. The other design
   specs (1.8k tokens, $0.006) are not. Not in a spec: a 2% saving is not measurable.
4. The start-up: $0.055 (16%).

### Show ($0.234)

1. The main session reads the full writing rules in 5 of 6 runs, before the handoff:
   $0.012 on average (5%). Then fixes to the handoff take 0.8 turns, $0.013 (6%). Rank 1
   (README short forms) aims at both.
2. The main session reads 4 to 5 frames (3.8k image tokens) in 1.5 turns: $0.03 (13%).
   The skill asks for this read, and it is a check. Not a lever.
3. The main session reads 60 to 80 lines of `record_gif.mjs` in every run, and the whole
   file in 2 of 6: $0.003 to $0.01. Too small to measure.
4. The start-up: $0.05 (21%).

### Ready ($0.227), change ($0.193), build ($0.200)

In a whole run these three stages cost $0.03, $0.06, and $0.15. Alone, the start-up is 22%
to 26% of each, and the rest is their own work. Ready reads the inbox and every spec,
with the writing rules, in one 10k-token write ($0.05); ready changes specs, so the rules
are needed. Change writes the change spec (1.6k output tokens, $0.017). Build is lean:
the builder costs $0.045 and the main session takes 8.7 turns. No spec for these stages.
Rank 1 (README short forms) helps each of them a little, through the handoff template.

### Across the stages

- The main session reads the full writing rules in 21 of 42 replays: intake 6, ready 6,
  show 5, change 3, verify 1. Each read costs $0.014.
- The main session reads `DES-pdlc-commit-trailers` (2.9k characters) in 20 of 42
  replays, to see the trailer lines that the README names.
- Turns that run the writing check or fix its findings, for each replay: verify 1.8,
  show 0.8, tests 0.8, build 0.5. A turn costs about $0.015.
- The reads of the fixed context are 80% of the read cost. Each of the 15 turns of verify
  reads 42k tokens of system prompt, skill, and README ($0.09 of $0.112).

## Measurement and power

The spread of a stage replay (standard deviation over 6 runs): verify 5.9%, tests 3.4%,
intake 10.9%, show 9.5%, ready 15.1%, build 5.4%, change 10.2%. The gate uses six runs on
each side and a one-sided test at 10%. It detects a fall of two spreads with about 90%
power. It detects a fall of one spread with about 50%.

- Rank 1 (README short forms): 11% on show, a spread of 9.5%. Power about 65%.
- Rank 2 (lean packets): the target is `pdlc:reviewer/quality`. The quality reviewer
  reads its packet and writes a short result, so its cost is nearly all the packet. Its
  cost for each call spreads 1% (security 6%, privacy 5%, specification 21%, the mean of
  all reviewers 11%). A 22% smaller packet cuts the call by about 13%. Power about 100%.
  The gate also refuses a stage that costs clearly more, a missed planted defect, and a
  false fail.
- Rank 3 (fewer turns in verify): 6% on verify, a spread of 5.9%. Power about 50%.
- Rank 4 (one red run): 5% on tests, a spread of 3.4%. Power about 70%.
- Rank 5 (a brief recon): 7% on intake, a spread of 10.9%. Power about 40%.

## Files that each experiment touches

| Rank | Id | Files |
|---|---|---|
| 1 | `s6-readme-short-forms` | `skills/init/references/templates/README.md`, `templates/handoff.md`, `templates/proposal.md` |
| 2 | `s6-review-packets-lean` | `skills/init/references/bin/make_packets.py`, `tests/test_make_packets.py` |
| 3 | `s6-verify-fewer-turns` | `skills/verify/SKILL.md`, `skills/init/references/adapters/inbox-files.md` |
| 4 | `s6-tests-one-red-run` | `skills/tests/SKILL.md` |
| 5 | `s6-intake-recon-brief` | `skills/intake/SKILL.md`, `agents/recon.md` |

No file is in two experiments. Rank 2 (lean packets) and rank 3 (fewer turns in verify)
both replay verify. Each runs from its own copy of the plugin, so they do not disturb each
other. Each experiment compares with the frozen baseline of its stage, so the order
does not matter. After the round, apply each kept edit with
`python3 bench/run_experiment.py apply <spec>`, and then run six whole runs to check the
kept edits together.

## Decision tree

For each experiment, after `python3 bench/run_experiment.py wait <spec>` prints DONE:

- SAME OR BETTER: keep. Apply the spec. Write the result in the progress log.
- NO GAIN: find if the mechanism worked, with the checks below. If it worked and the
  saving is below the noise, log the measured saving and do not retry. If it did not
  work, report which instruction the model ignored, and stop.
- REGRESSION because the stage did not finish: read the `Stop` commit in the project of
  that run (`project` in `bench/results/<id>-stage/run<n>.json`). If the cause is the
  edit, revert. If the cause is a tool or a rate limit, start `<id>-b` with `"runs": 3`.
- NEED MORE RUNS: start `<id>-b` with the same edits and `"runs": 3`. Freeze both sets
  with `python3 bench/run_bench.py freeze bench/results/<id>-stage/e2e.json bench/results/<id>-b-stage/e2e.json --out bench/results/<id>/result.json --label <id>`,
  and gate again.

The checks for each experiment:

- Rank 1 (README short forms): count the full reads of the rules by the main session with
  `grep -c 'ASD-STE100' bench/results/s6-readme-short-forms-stage/run*.stream.jsonl`.
  The baseline has a read in 5 of 6 runs. Count the turns in `num_turns` of each
  `run<n>.json` (the baseline mean is 10.5). Read the six handoffs for bare IDs.
- Rank 2 (lean packets): `wc -c` on the packets in each replay project. The expected
  sizes are about 14.8k characters for a code packet, 31.3k for specification, and 20.6k
  for tests. The seeds must catch 5 of 5 with no false fail. Also run the gate by hand
  with `--target pdlc:reviewer` and with no target, for the log.
- Rank 3 (fewer turns in verify): `num_turns` (the baseline mean is 14.8), and
  `grep -c 'templates/intent.md' ...run*.stream.jsonl` (the baseline reads the template
  in 6 of 6 runs). Make sure that the packets exist in each run, so that the one-command
  rule did not stop the reviews.
- Rank 4 (one red run): count the `unittest` runs by the main session in each stream (the
  baseline runs 2 to 4). Make sure that the lock and the review still happened
  (`Tests reviewed CH-` in the subjects of `run<n>.json`).
- Rank 5 (a brief recon): the length of the `handback_report` of recon in each stream.
  The baseline is 4.5k to 9.6k characters. Then
  `grep -c 'DES-writing-style' ...run*.stream.jsonl` for the reads by recon. The stage
  check cannot see the text quality. So read the spec that intake wrote in one run, for
  bare IDs and long sentences.

## Risks to effectiveness

- Rank 1 (README short forms): a handoff or a proposal written from the short form can
  break a rule that the short form omits. An example is an "-ing" form. The specification
  reviewer judges specs, the README, and code comments. The README edit says to read the
  full rules before a spec or an intent. So the reviewed text keeps its rules.
- Rank 2 (lean packets): a reviewer sees each acceptance line once, in the change spec,
  which is the contract of the change. When the spec has a line that the change spec
  lacks, the script keeps the full text. The seeds check runs on each remit.
- Rank 3 (fewer turns in verify): if a check fails, the `&&` makes no packets, and the
  skill goes to step 5 as before. The shape of the intent file lives in the inbox
  adapter, so a project with another inbox adapter is not affected.
- Rank 4 (one red run): the model must read the result of each requirement from the
  verbose list. If the project's runner has no verbose flag, the adapter already says to
  run all and read the names.
- Rank 5 (a brief recon): recon writes its draft requirements without the full rules. The
  main session has the rules and writes the spec. It ran the writing check 10 times over
  the 6 baseline replays of intake. The replay cannot see a later writing finding in that
  text, so read one spec by hand (see the checks above).

## Outside the stage loop

These items need a whole run, or a decision. No spec is written for them.

- Smaller terminal frames (640 by 400 pixels, the fallback of round 5,
  `bench/experiments/round5/r5-small-terminal-frames.json`, whose edits still apply). The
  frames cost the specification reviewer $0.058 a call, and a run makes about 1.5 calls:
  the edit saves about $0.05 a run (3%). A verify replay cannot measure it, because the
  snapshot holds the frames. The whole-run gate with `--target pdlc:reviewer/specification`
  can, but that cost spreads 21%, because the reviewer sometimes samples 9 frames. The
  guard gap is the same as for the held transcript edit. The user decides.
- The 1-hour cache. Every cache write is a 1-hour write at twice the input price. The
  writes are $0.07 to $0.13 of each stage. At the 5-minute rate they cost 37% less:
  $0.03 to $0.05 a stage, about $0.12 a whole run (7%). A Claude Code setting, not a pdlc
  lever.
- The context that `/pdlc:ship` carries from stage to stage. A whole run reads about 2.7M
  cached tokens in its main session (31 to 38 turns at 37k to 118k), about $0.40 (25%).
  A fresh stage pays $0.05 for its start-up and $0.03 to $0.05 to orient itself. It saves
  the carried reads: about $0.13 in verify, less in each other stage. So a fresh
  context before verify is at break-even, and a fresh context before a small stage is a
  loss. A compaction before verify would save at most $0.05 a run (3%), with the risk
  that the model loses a detail. Do not pursue.
- Follow-up intents from reviews: 5 of 6 verify runs file one, at $0.05 to $0.065 a run
  (3% to 4%). A design feature. Rank 3 (fewer turns in verify) makes the filing cheaper.
- The writing check on handoffs and proposals that no reviewer judges: 1 to 3 turns a
  whole run ($0.03 to $0.05, 2% to 3%). Rank 1 (README short forms) aims at fewer fixes.
  To remove the check would trade the quality of the proposal, which the user reads.

## What not to try, and why

- A shorter README. The README is 5k tokens. A 20% cut saves $0.004 a stage alone and
  $0.008 a whole run, and a rewrite of the central document has behaviour risk.
- Shorter skill descriptions. They are about 1.6k tokens of the system prompt, $0.005 a
  stage. The trigger phrases must stay.
- No writing rules in the specification packet. Round 1 showed that writing findings fail
  reviews, and an extra round costs $0.19.
- A shorter `DES-writing-style`. It is a synced copy of `WRITING-GUIDELINES.md`.
- Intake without the writing rules in the main session. Intake writes the spec text that
  the specification reviewer judges. Rank 5 keeps that read, and changes recon only.
- Commands of an adapter inlined in a skill (the branch start, the commit). A project with
  another adapter would get wrong commands. Rank 3 puts the shape of an intent in the
  adapter instead.
- A script that sets the statuses to `verified` and `in review`. A spec cannot add a file,
  and a writer inside `check_merge.py` mixes a gate with a mutation.
- Fewer frames read by the main session in show. The read is a check.
- The reverted edits (Haiku reviewers, the writing check before verify) and the held
  transcript edit.

## Notes on the harness

- `analyse()` under-counts the output of agents. The stream repeats the `usage` of the
  first chunk of each assistant message, so `output_tokens` is 2 to 60 for a message of
  500 tokens. The totals are right, because they come from the result event. The split
  between the main session and the agents is off. In verify the agents cost $0.244, not
  $0.194. A reviewer call costs about $0.061, not $0.048. Baseline and candidate
  share the bias, so the gate still compares like with like. A fix: take the output of
  the main session from `usage` in the result event, and the output of the agents from
  `modelUsage` less `usage`.
- A verify replay cannot measure an edit to `record_gif.mjs`. The frames come from the
  snapshot.
- The cost for each reviewer call spreads 1% for quality, 5% for privacy, 6% for
  security, and 21% for specification. So `--target pdlc:reviewer/quality` is the sharpest
  gate for a packet edit. `--target pdlc:reviewer` (11%) is a weak one.
- `run_experiment.py check` writes `bench/results/s6-*/` (spec.json, applied.diff,
  check.txt) as a side effect. Nothing blocked the planning.
