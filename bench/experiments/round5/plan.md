# Round 5 plan: text in place of frames first, compliance by risk second

Run `r5-terminal-transcript` (the specification reviewer reads a text transcript in place
of the frames) first. Run `r5-compliance-by-risk` (no compliance reviewer when there is
nothing to judge) second. It needs harness tasks H4 (reviewer calls split by remit) and H5
(a gate mode that counts calls) first. Keep `r5-small-terminal-frames` (frames of 640 by 400) as
the fallback for the first slot. All three specs pass `python3 bench/run_experiment.py
check`, with no new writing finding and green plugin tests.

## The experiments, in order

| Rank | Id | Edit | Lever | Expected saving | Sure? | Cost |
|---|---|---|---|---|---|---|
| 1 | `r5-terminal-transcript` | Nine edits. `record_gif.mjs` writes `frames/transcript.md` for a terminal recording. `make_packets.py` puts the transcript in the specification packet in place of the list of frames. The specification remit says how to judge it. Two tests. | context pack | About $0.055 a run (4%). Each specification review costs about $0.05 less. The mean cost of a reviewer call falls 20% to 25%. | High: the code is deterministic and tested end to end on the project of reference run 4. | 6 runs and the seeds check, about $9.3. |
| 2 | `r5-compliance-by-risk` | Six edits. `make_packets.py` writes the compliance result itself when the project lists no rules and no dependency file changed. The verify skill starts no reviewer for that remit. Three tests. | review by risk | About $0.035 a run (2.4%): 1.17 compliance calls a run at $0.027 each, plus a little less work for the main session. | High on the mechanism. Medium on the main session: it must not start the reviewer anyway. | 6 runs, no seeds, about $8.4. Needs H4 and H5 first. |
| Fallback | `r5-small-terminal-frames` | Three edits. A terminal recording defaults to 640 by 400 pixels. One test. | context pack | About $0.04 a run (3%). Each frame costs 341 image tokens in place of 853. | High: I rendered run 4's script at that size, and the text is the same size as before. | 6 runs, no seeds, about $8.5. Run it only if experiment 1 is not kept. |

Total: $17.7 of the $25 when both ranked experiments run. About $7 stays in reserve for a
top-up of three runs if a side has fewer than five.

### Why this order

- The specification reviewer costs $0.105 a call in the harness's split, against $0.027
  for security, quality, compliance, or privacy. The difference is the frames: 17 to 20
  images of 1000 by 640 pixels, about 850 tokens each, read in three to five messages. A
  run makes 1.5 specification calls on average. So the frames cost about $0.08 a run (5%),
  the largest single item that one mechanical edit can remove.
- For a terminal recording the frame is text. A transcript of 4.7k characters (about 1.3k
  tokens) carries the same evidence. The reviewer reads it with no risk of a misread digit
  in an image. The recorder keeps the GIF and the PNG frames for the
  pull request and for web recordings, where the frames stay in the packet.
- Experiment 2 is small but deterministic. On this fixture the compliance reviewer answers
  "not applicable" in every run, because the project lists no rules and the change touches
  no dependency file. A script can say the same thing for $0.
- The fallback shrinks the same cost pool as experiment 1, so the two must not both run.

## What the data says (six reference runs)

- A run costs $1.26 to $1.68, mean $1.47, standard deviation $0.15 (10.5%). The spread is
  half of what it was before round 3, because no run waits for agents any more.
- Agent calls: 9 to 15 a run. Reviewer calls: 6 to 11 a run (mean 7.5), $0.0457 a call.
  Per run, the mean cost of a reviewer call is 0.0425 to 0.0487 (a 14% range).
- The specification reviewer reads every frame (17 to 20) in batches of 3 to 7 per
  message. Its packet is 35k characters against 19k for the other code remits, because it
  also carries the writing rules and the writing check.
- The main session is about 70% of a run. Its context grows from 37k to 108k to 118k
  tokens (a 9% range) over 31 to 38 turns. The first 37k is Claude Code itself. The pdlc
  documents it reads (README, seven skills, templates, adapters, design specs) are about
  23k tokens, 11% of a run once carried through every turn.
- Every cache write is a 1-hour write, at twice the input price. Cache writes are 193k to
  278k tokens a run. That is a Claude Code setting, not a pdlc lever (see "Outside the
  loop").
- Extra review rounds: 4 of 6 runs had one. Runs 2 and 6 failed the tests review once
  (the reviewer wanted checks for `+2` and ` 2`). Run 4 failed verify on old wording in
  the README. Run 6 failed verify on a 26-word sentence and bare IDs in the progress log.
  Run 5 ran verify twice. The causes differ each time, so no single edit removes them.
- The reviewer wrote no `result.md` in 1 of 48 reviewer calls (the tests reviewer in run
  3). The main session wrote that one file. This defect is now rare and is not a lever.

## Power estimate

Six runs a side, a one-sided permutation test at 10%, 3,000 resamples of the reference
values. The whole-run gate detects a 5% saving with 33% power, 10% with 70%, 15% with 95%
and 20% with 100%. Neither experiment reaches 10%, so each needs a component metric:

- Experiment 1 and the fallback: the cost of a reviewer call (`--target pdlc:reviewer`).
  Its per-run values spread 5%. The gate detects a 5% fall with 50% power, 10% with 97%
  and 15% or more with 100%. Experiment 1 expects a fall of 20% to 25%; the fallback
  expects 13% to 17%. After H4, `--target pdlc:reviewer/specification` on the saved
  `result.json` shows the saving on the specification call alone (expected: $0.105 to
  about $0.055).
- Experiment 2: compliance calls a run (`--target calls:pdlc:reviewer/compliance`, mode
  H5). The reference makes 1, 1, 1, 2, 1, 1 calls. If every candidate run makes none, the
  chance of luck is 0.1%. If one run still calls the reviewer, 0.6%; if two do, 2.3%.

## Risks to effectiveness

- Experiment 1: the planted defects sit in the code, the specs and the checks, which every
  packet keeps, so the seeds check guards the remits. The seeds project has no frames, so
  the seeds check cannot see the transcript itself. The guard for that is in the six runs:
  pdlc must finish, and the specification results must not fail on the transcript. The
  decision tree says how to check. A web recording is not affected: its packet still lists
  the frames.
- Experiment 2: compliance has no planted defect, and the seeds build never makes a
  compliance packet, so `seeds` is off. The merge check still needs a `result.md` that
  says `Result: pass` for every remit in `config.md`; the script writes one. A project that
  lists rules, or a change that touches a dependency file, still gets a reviewer. A change
  that vendors a library as plain source is the one case that no longer gets a compliance
  look.
- Fallback: a smaller frame holds fewer lines, so a long output scrolls out of view. The
  terminal shows the newest lines, so the command of the step and its result stay in view.
  I checked frames 09 and 20 of run 4 at 640 by 400.

## Decision tree

Experiment 1, after `python3 bench/run_experiment.py wait` prints DONE. First read the
specification results of the six runs: for each `project` path in
`bench/results/r5-terminal-transcript-*/run1.json`, run `git -C <project> log --all
--format=%h -- pdlc/changes/CH-*/review/specification/result.md | head -3` and show each
result with `git -C <project> show <hash>:<path>`. A problem that names a frame, the
transcript, or an output "not shown" is a false alarm from the edit.

- SAME OR BETTER, and no false alarm: keep. Apply with `python3 bench/run_experiment.py
  apply`. Freeze the new reference:
  `python3 bench/run_bench.py freeze bench/results/r5-terminal-transcript-{1,2,3,4,5,6}/e2e.json --out bench/reference.json --seeds bench/results/r5-terminal-transcript-seeds/seeds.json --label r5`.
  Log it. Then do H4 and H5 (H4 then reads these six runs again) and run experiment 2.
- SAME OR BETTER, but a false alarm in one or more specification results: do not keep.
  Read the result: if the reviewer misread the transcript, revert and run the fallback.
- NO GAIN: count the frame reads by agents in the six streams
  (`grep -c '"file_path": "[^"]*frames/[0-9]*\.png"' bench/results/r5-terminal-transcript-*/run1.stream.jsonl`).
  If the count is above zero, the reviewer found the frames without the list; report it
  and stop. If it is zero, do H4, read the six candidate folders again
  (`python3 bench/run_bench.py reanalyse bench/results/r5-terminal-transcript-<n>`), freeze
  `result.json` again, and gate by hand with `--target pdlc:reviewer/specification`. If
  that says SAME OR BETTER, keep: the mix of remits hid the saving. If not, revert and run
  the fallback.
- REGRESSION from the seeds (a missed defect or a false fail): revert, and name the remit
  in the log. Do not run the fallback before the cause is known.
- REGRESSION because a run did not finish: read its `Stop` commit. If the specification
  remit failed three times on the transcript, revert and run the fallback. If the probes
  or the project checks failed, the edit did not touch the builder. Report the run as
  noise, revert, and do not retry before round 6.
- NEED MORE RUNS (fewer than five runs finished the harness): start
  `r5-terminal-transcript-b` with the same edits and `"runs": 3`. Freeze both sets with
  `python3 bench/run_bench.py freeze bench/results/r5-terminal-transcript-*/e2e.json --out
  bench/results/r5-terminal-transcript/result.json --label r5-terminal-transcript --seeds
  bench/results/r5-terminal-transcript-seeds/seeds.json`. Gate again.

Experiment 2, only after experiment 1 is settled, H4 and H5 pass their tests, and the
reference is frozen again with the per-remit labels:

- SAME OR BETTER: keep, apply, freeze, log.
- NO GAIN: count the compliance calls in the six streams
  (`grep -c 'review/compliance/packet.md' bench/results/r5-compliance-by-risk-*/run1.stream.jsonl`).
  If two or more runs started a compliance reviewer, the main session ignored the skill
  text; report it and stop. The saving sits at the floor, so do not retry.
- REGRESSION because a run did not finish: read its `Stop` commit. If the merge check said
  "compliance review has no result", the script did not write the file; revert and report
  the bug. If a whole run is dearer and not luck, check the verify rounds; an extra round
  is noise, so revert and do not retry.
- NEED MORE RUNS: as for experiment 1, with `r5-compliance-by-risk-b` and no seeds.

The fallback uses the tree of experiment 1, with `seeds` off. Check the specification
results in the same way, for a problem that names a frame.

## What not to try, and why

- Haiku reviewers (round 1) and the writing check before verify (round 2): done.
- Fewer review rounds: an extra round costs about $0.19 a run on average (13%). But the
  four causes seen differ from each other, and the gate cannot see fewer rounds. Six runs
  with rounds 1, 1, 1, 2, 2, 1 against six runs with one round each give a 23% chance of
  luck.
- A shorter `DES-writing-style` (the writing rules): it is a synced copy of
  `WRITING-GUIDELINES.md`, so an edit fails `python3 scripts/sync_shared.py --check`.
- A rule that the main session reads each pdlc document once. It reads the writing rules
  one to three times a run (3.6k tokens each), about $0.04 a run. The context at the end
  of a run spreads 9%, so a 3% change in it is not measurable.
- Skipping privacy by risk: the `privacy-log` planted defect (a usage log in `/tmp`) needs
  the privacy reviewer on every change that touches code.
- Dropping the frames from the specification review altogether: it saves about 6% but
  removes a check, and nothing measures that loss. The transcript keeps the check.
- A cheaper model for recon, the test writer, or the builder: 2% to 6%. The benchmark
  cannot see a weaker code map or weaker checks on a two-file fixture.
- A Haiku reviewer for compliance and privacy only: it needs a new agent file, which the
  spec format cannot add. It also repeats the risk of round 1.
- Smaller packets for the other remits (no repeated requirements, no full text of a new
  file next to its diff): about 1% each.
- Shorter skills and README: the pdlc documents are 11% of a run in the main session. A
  30% cut saves about 3%, and a rewrite of eight documents is not a mechanical edit.

## Outside the loop

- Every cache write in every run is a 1-hour write (`ephemeral_1h_input_tokens`), at $4 a
  million tokens against $2.50 for a 5-minute write. A run writes 193k to 278k tokens to
  the cache, and the turns come seconds apart. At the 5-minute rate the same runs would
  cost about a fifth less. This is a Claude Code setting, and a user's cost follows the
  user's setting, so it is not a pdlc lever. It is worth a look at the CLI's options.
- Output tokens are 37k to 48k a run (thinking 4.5k to 6.7k), 25% to 30% of the cost at
  list price. They are the records that pdlc writes (specs, the change spec, handoffs, the
  proposal, the visual script) and the files the agents write. No mechanical edit cuts
  them safely.
- The main session reads the source of `record_gif.mjs` in every run (about 1k tokens),
  because the visual adapter does not give the format of `visual.json`. A line in the
  adapter that points to the header comment would save the read. Too small to measure.
- The reviewer that answers in its reply and writes no `result.md` happened once in 48
  calls in the reference runs. Leave it.
