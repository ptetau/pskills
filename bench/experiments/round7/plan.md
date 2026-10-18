# Round 7 plan: fewer failed review rounds

Round 7 attacks the second review round. In 48 saved whole runs, 19 runs (40%) needed a second
verify round, and each one cost about $0.26 more. The specification reviewer caused most of them,
with 41 of 57 problems. 35 of these 41 problems are text problems. They are 21 writing rules,
8 IDs with no description, and 6 spec summaries that do not show the new behaviour. The free script
`check_writing.py` had already printed 24 of the 27 writing problems that cite a line. Nobody
fixed them before the reviewers read them.

The round has one harness task, H6 (count the writing findings that a run leaves), and five
experiments. Each spec is in `bench/experiments/round7/`, passes
`python3 bench/run_experiment.py check`, has green plugin tests, and adds no writing finding.
The exact commands, in order, are in `commands.md` next to this file.

| Rank | Id | Stage | Edit | Expected saving | Sure? | Cost to test |
|---|---|---|---|---|---|---|
| 1 | `s7-commit-writing-hook` | tests | Six edits. The commit hook `hooks/commits.py` runs the writing check on the text that each commit wrote, on any branch, and reports the findings to Claude once. Ten unit tests. | Catches the 24 of 27 script-visible problems before a reviewer sees them. About 0.08 fewer specification-reviewer calls a run, $0.02 a run. Its amend turns cost about $0.02 a run back. Net $0.00 to $0.03, plus a safety net. | High on the mechanism (a hook runs by itself). Medium on the net cost. | 6 tests replays, $2.3 |
| 2 | `s7-progress-log-form` | tests | Five edits. The tests, build, and verify skills and the change template give the form of a progress log line at the point of use: a description next to each ID, 25 words or fewer. | The progress log holds 14 of the 27 cited writing problems. About 0.1 fewer specification-reviewer calls a run, $0.03 a run. | High. The round 6 handoff edit cut bare IDs from 23 of 36 to 6 of 41 the same way. | 6 tests replays, $2.3 |
| 3 | `s7-intake-spec-text` | intake | Four edits. Intake and the job and capability templates ask for acceptance lines of 25 words or fewer, a description next to each ID, and a summary that shows the new behaviour. | Removes long acceptance lines (6 of 27 cited problems) and the 6 summary problems at the source. About 0.07 fewer calls a run, $0.02 a run. | Medium. The intake replay already writes the summary right 5 of 6 times. The whole runs never did (0 of 6). | 6 intake replays, $1.6 |
| 4 | `s7-ready-line-length` | ready | One edit. Where ready settles the bad forms of an input, it keeps each acceptance line at 25 words or fewer. | Ready leaves 5 to 12 findings a run, mostly long lines that list many values. About 0.03 fewer calls a run, $0.01 a run. | Medium. One sentence in a skill. | 6 ready replays, $1.4 |
| 5 | `s7-test-writer-wrong-versions` | tests | Four edits. The test writer gets the three most-failed rules of the tests remit: a value close to the allowed values, the exit code of the process, a check for each listed error message. | The tests reviewer failed 10 of 48 runs, 5 of them on close values. A tests re-round costs about $0.20. About $0.02 a run. | Medium. The tests replay cannot show it, because the frozen spec already names the close values. | 6 tests replays, $2.3 |

Together, the five edits aim at about 0.25 fewer specification-reviewer calls a run. That is
1.33 to about 1.1 in the terms of `bench/reference.json`, and $0.05 to $0.08 a run (4% to 6%). The
new baselines cost $7.6, and the experiments cost $9.9. That is $17.5 of the $28. The whole-run
confirmation costs about $8.7 of its $9. The reserve for top-ups is $5.

## Words used here

- A **repeat**: a second (or third) verify round for one change. The reviewers run again.
- A **finding**: one line of output of `pdlc/bin/check_writing.py`.
- The **packet view**: the files whose writing the specification packet checks. These are the
  README, the specs, and the change spec. A handoff or a proposal is not in the packet view.
- The **writing count**: the findings in the packet view of the text that a stage wrote. H6
  (count the writing findings) adds this number to each result.
- A **stage baseline**: `bench/sections/<stage>.json`, six replays of one stage.

## Where the text problems come from

I ran the writing check on the text that each saved stage replay wrote (its own lines only,
since the entry commit of the stage). The counts are for the packet view, with one line for
each of the six runs.

| Stage | Findings a run | What the findings are |
|---|---|---|
| intake | 9, 7, 12, 9, 7, 13 (after round 6: 4, 2, 9, 4, 2, 7) | Long acceptance lines and long requirement sentences. IDs such as `R4` with no name in the requirement text. |
| ready | 12, 11, 8, 5, 8, 8 | Lines that list many bad values, 26 to 33 words. The sentence "If N is not valid, …" of 31 words. `R1` and `R2` with no name. |
| change | 1, 1, 1, 1, 1, 1 | One acceptance line of 27 words, copied from the frozen spec. The change skill writes no finding of its own. |
| tests | 4, 1, 2, 2, 6, 3 | All in the progress log line of the red run: "3 R5 checks pass", "The 14 R7 checks fail". Also 3 to 11 findings a run in the handoff, which no reviewer reads. |
| build | 0, 0, 0, 3, 0, 0 | One run wrote bare IDs in its progress log line. |
| show | 0 in each run | Show writes only the handoff. |
| verify | 0, 0, 0, 0, 1, 0 | One `IN-0002` with no name in the progress log. The handoff, the proposal, and the new intent hold 3 to 15 findings, outside the packet view. |

In the whole runs, the tests stage also edits acceptance lines on the branch after a failed
tests review. Those lines then enter the packet's writing check, which is how 6 long
acceptance lines reached the specification reviewer with a script finding.

So the judges are clear. The tests replay judges the progress log edits and the hook. The
intake and ready replays judge the spec text edits. The change, build, show, and verify
replays can show nothing here. The change replay copies a frozen spec, and the other three
leave almost no finding. The round makes no baseline for them.

## The remedies, and what each replay can show

**R1 (measure the repeat).** H6 adds the writing count to `check_stage`, `inspect_project`,
`summarise`, and a gate mode `--target writing`. The mode uses the permutation test and the
guards of the `waiting` mode. The guards are the same: the stage finished and passed its check,
the probes and the project's checks pass, and no planted defect is lost. The stage must not be
clearly dearer. One guard differs. A stage that costs up to 10% more is not a regression. The
reason is that the hook adds one amend turn (about 4% of the tests stage) and saves in a later
stage. A rise above 10% is a regression when it is not luck. A rise above the noise of the
baseline and above 25% is a regression also when it could be luck. `recheck` now also works on
a stage folder, so an old result gets the count without a new replay. The whole-run count (since the first
commit) comes for free in `inspect_project`.

A stage replay can show that a stage leaves fewer findings. It cannot show the second verify
round itself, because the replay stops at the end of its stage. Only the whole runs show the
repeat, through `--target calls:pdlc:reviewer/specification`.

**R2 (the sources of writing breaks).** Two specs. `s7-progress-log-form` edits the tests
skill (step 3), the build skill (step 4.2), the verify skill (steps 4 and 5), and the change
template. The change template alone is not enough. The change skill replaces the guide text
when it writes `change.md`, so the tests and build stages never see the template. The rule
must sit in the skill step that writes the line, as the round 6 handoff edit sits in the
handoff template. `s7-intake-spec-text` edits the intake skill and the job and capability
templates. The tests replay judges the first spec through the writing count (baseline about 3
a run). The intake replay judges the second (baseline about 5 a run after round 6). Neither
replay sees the acceptance lines that the tests stage edits after a failed tests review. The
tests skill gets no line-length rule from these specs, so that the two specs stay separate.

**R3 (the commit hook).** `s7-commit-writing-hook`. The design is in the next section. The
tests replay judges it. Its five commits ("Start", "Tests", "Lock tests", "Review tests",
"Tests reviewed") write the progress log line and the handoff. So the hook fires once or
twice a replay. The replay shows the fall in findings and the cost of the amend turns. It
cannot show the saving in verify.

The hook runs inside a replay because `claude -p --plugin-dir <scratch copy>` loads
`hooks/hooks.json` from that copy, and `${CLAUDE_PLUGIN_ROOT}` points at the copy.
`run_experiment.py check` copies the whole plugin, hooks included, and runs the plugin tests
in the copy. I confirmed this: the ten new hook tests ran and passed in the scratch copy
`/tmp/pdlc-exp-s7-commit-writing-hook-*/pdlc`.

**R4 (the spec summary).** One short paragraph in the intake skill, after "Leave no old
wording". For each requirement that intake adds, the summary of the spec shows the new
behaviour in one short sentence. Intake is the right place, because intake writes the summary,
has the full writing rules loaded, and already fixes the summary for changed requirements. A
script check is not possible, because "shows what the change adds" is a judgement. The intake
replay cannot show the effect: 5 of 6 saved intake replays already wrote `--top N` into the
summary. The 12 whole runs of round 6 never did (0 of 12 at the "Specify" commit). The
specification reviewer failed 6 of 48 runs on this point. So the whole-run confirmation judges
R4 (the spec summary), with a free hand check at the "Specify" commit. The intake replay is
its guard: the stage must finish, and must not cost clearly more.

**R5 (the test writer).** `s7-test-writer-wrong-versions` edits `agents/test-writer.md` only.
The guard already lets the test writer read `pdlc/reviews/tests.md`: the file is under `pdlc/`
and not under a `review/` folder (`guard.py`, line 96). The edit names that file and gives the
three most-failed rules in the agent's own words. The guard does not change. The tests replay
cannot show the effect: all 12 saved tests replays already use `+3` and `3.0`, because the
frozen spec names them. The replay is a guard: the stage must finish, the checks must fail
first, and the stage must not cost clearly more. The target `calls:pdlc:reviewer/tests` prints
the tests-review calls a run (1.0 in each saved replay). The whole runs judge the effect, with
`--target calls:pdlc:reviewer/tests` as a hand check.

**R6 (the security repeats).** I planned nothing for them. The 4 security problems are real
faults in the app, for example a 5000-digit `--top` value that crashes `int()`. 3 of them
became new intents for the user. A reviewer that finds a real fault is pdlc at work.

**R7 (confirm with whole runs).** Six whole runs and the planted-defect check on the plugin
with every kept edit, against `bench/reference.json` (label r6). The gates are
`--target calls:pdlc:reviewer/specification` and the whole-run cost. See "Measurement and
power" for what six runs can and cannot say.

## Why R2, R3, and R4 are three specs and not one

R2 (the source rules) and R4 (the spec summary) both edit `skills/intake/SKILL.md`, so they
share one spec (`s7-intake-spec-text`). The same replay judges both, and the two edits do not
conflict. R2 (the source rules) for the progress log and R3 (the hook) touch different files.
Both aim at the same findings in the tests replay. They stay
apart, so that each gets its own verdict: the hook fires only on findings that the source rule
did not prevent. Each experiment runs from its own copy of the plugin, so they can run at the
same time. If both are kept, `apply` puts both into the plugin, and the whole runs test them
together.

## The design of the hook

`hooks/commits.py` already runs after every Bash call and checks the trailers of a new commit
on a pdlc branch. The new part:

1. After a commit or an amend with one parent, on any branch, the hook lists the `.md` files
   of the commit. It takes the files under `pdlc/specs/`, `pdlc/inbox/`, and `pdlc/changes/`,
   without the `review/` folders. It runs `pdlc/bin/check_writing.py --since HEAD~1 <files>`, so only
   the lines that this commit wrote count. Code blocks are skipped by the script.
2. The hook makes a key from the set of findings (without line numbers) and records it under
   `.git/pdlc-writing-reported` with the hash of the parent commit. A set that it already
   reported for that parent, or a fourth set for one parent, gets no report. The record is
   under `.git`, so `git status --porcelain` stays clean, as the README requires.
3. When there are new findings, the hook exits 2 and prints them to Claude, after the trailer
   problems if there are any. The commit stands. The message says to amend what can be fixed,
   and that a finding that cannot be fixed can stay.

Why on any branch: intake, ready, and change commit on `main` when no pdlc branch is unmerged.
They write the long acceptance lines and the summary. A hook only on pdlc branches would
miss them. Why not the review folders: a packet is a copy of the specs and the code, and a
result is the text of a reviewer. Why not `pdlc/README.md`, the templates, the adapters, and
the reviews: they come from the plugin, and the plugin's own text has six findings today. Why
exit 2: that is how the trailer check reaches Claude today, and a PostToolUse hook cannot block
a commit that already exists. Why once for each set: round 1 saw a run stop because writing
findings did not converge. The record bounds the reports, so the hook cannot loop.

What the hook costs: one `python3` call of under a second after each commit, and one amend turn
(about $0.015) each time it reports. It fires only when a commit wrote a finding.

This is not the round 2 edit. Round 2 told the verify skill to run the check before the
packets, and the model could skip the instruction. A hook runs by itself, at the moment the
text is written, in every stage.

## New baselines

Every stage baseline in `bench/sections/` is from before round 6, and each stage reads the
README that round 6 changed. The round needs three new baselines, each on the plugin as it is
now:

| Stage | Runs | Cost | Why |
|---|---|---|---|
| tests | 12 | $4.6 | Three experiments share it. Twelve runs give the permutation test more power for the hook and the progress log. |
| intake | 6 | $1.6 | Judges `s7-intake-spec-text`. |
| ready | 6 | $1.4 | Judges `s7-ready-line-length`. |

The commands are `python3 bench/run_bench.py stage --stage <s> --label s7-<s>-base --runs <n>`
and then `python3 bench/run_bench.py freeze bench/results/s7-<s>-base/e2e.json --out bench/sections/<s>.json --label s7-<s>-base`.
I checked that `stage` takes these options and that `freeze` reads a stage `e2e.json`
(`command_freeze` reads `runs` and `plugin_commit`, which `command_stage` writes). The old
files stay in git, and `commands.md` copies each to `bench/sections/<s>-before-round-6.json`
first. H6 must be built before the baselines run, so that each run carries its writing count.
No baseline is needed for change, build, show, or verify.

## Measurement and power

The writing count is a small whole number, so the permutation test on six against six works
when the fall is large. With the saved tests counts `[4, 1, 2, 2, 6, 3]` as the baseline:

- A candidate at `[0, 0, 1, 0, 0, 0]` has a 0.2% chance of luck. The gate keeps it.
- A candidate at `[1, 0, 2, 1, 1, 0]` has a 2% chance. The gate keeps it.
- A candidate at `[2, 1, 1, 2, 3, 1]` has a 12% chance. The gate says NO GAIN.

The saved intake counts after round 6 are `[4, 2, 9, 4, 2, 7]`. A fall to `[1, 0, 3, 1, 0, 2]`
has a 2% chance of luck, and a fall by half has a 10% chance. So the intake experiment needs a
clear fall. The twelve-run tests baseline sharpens the three tests experiments.

The whole-run gate on specification-reviewer calls has a power problem. `bench/reference.json`
has the calls `[2, 2, 1, 1, 1, 1]` (mean 1.33). A perfect candidate, `[1, 1, 1, 1, 1, 1]`, has a
23% chance of luck in the permutation test (210 of 924 splits). So the gate with
`--target calls:pdlc:reviewer/specification` cannot say SAME OR BETTER with six runs on each
side, whatever the edits do. The twelve whole runs of round 6 as the baseline give 16%. All 48
saved whole runs as the baseline give 2% for a perfect candidate and 11% for one repeat in six.
The decision for the user is in "What the user must decide". The whole runs still give their
full guards. Every run must finish, 8 of 8 probes must pass, and the project's checks must
pass. The reviewers must catch 5 of 5 planted defects with no false alarm, and the gate
compares the whole-run cost with the reference.

## Files that each experiment touches

| Rank | Id | Files |
|---|---|---|
| 1 | `s7-commit-writing-hook` | `hooks/commits.py`, `tests/test_commits_hook.py` |
| 2 | `s7-progress-log-form` | `skills/tests/SKILL.md`, `skills/build/SKILL.md`, `skills/verify/SKILL.md`, `skills/init/references/templates/change.md` |
| 3 | `s7-intake-spec-text` | `skills/intake/SKILL.md`, `skills/init/references/templates/job.md`, `skills/init/references/templates/capability.md` |
| 4 | `s7-ready-line-length` | `skills/ready/SKILL.md` |
| 5 | `s7-test-writer-wrong-versions` | `agents/test-writer.md` |

No file is in two experiments. Three experiments replay the tests stage, each from its own
copy of the plugin. Run at most three experiments at the same time. Wave 1 is ranks 1, 2, and
3 (18 sessions). Wave 2 is ranks 4 and 5 (12 sessions).

## Decision tree

For each experiment, after `python3 bench/run_experiment.py wait <spec>` prints DONE:

- SAME OR BETTER: keep. Apply the spec after the round, in rank order.
- NO GAIN with a fall in the mean of 30% or more: the edit works and six runs are too few.
  Start `<id>-b` with the same edits and `"runs": 6`, freeze both sets into
  `bench/results/<id>/result.json`, and gate again by hand.
- NO GAIN with a smaller fall: read the text that the stage wrote (the checks below). If the
  model ignored the instruction, report which sentence, and do not retry.
- REGRESSION because the stage costs more than 10% more: for the hook, count the amend turns
  in the streams (`grep -c '"command": "git commit --amend' bench/results/<id>-stage/run*.stream.jsonl`).
  If the rise is the amend turns and the findings fell, report both numbers. The user then
  decides whether the whole runs test the hook.
- REGRESSION because the stage did not finish: read the `Stop` commit in the project of that
  run. If the cause is the edit, revert. If the cause is a tool or a rate limit, start
  `<id>-b` with `"runs": 3`.
- For rank 5 (the test writer), the gate says NO GAIN by design (1.0 calls a run on each
  side). Keep it when the six replays finish and the checks fail first in each. The stage
  must not cost clearly more. Then the whole runs judge it.

The checks for each experiment, on the projects in `bench/results/<id>-stage/run<n>.json`:

- Rank 1 (the hook): the hook messages in the streams
  (`grep -c 'writing finding' bench/results/s7-commit-writing-hook-stage/run*.stream.jsonl`),
  the amend turns, and the `findings` list in `outcome.writing` of each run.
- Rank 2 (the progress log): the progress log lines of each `change.md` on the change
  branch (`git -C <project> show pdlc/CH-0001-top-option:pdlc/changes/CH-0001-top-option/change.md`).
  Each ID must have a description beside it.
- Rank 3 (intake) and rank 4 (ready): the acceptance lines of the job spec on `main`. Count
  the lines over 25 words. Also look at "Who and why" for `--top`.
- Rank 5 (the test writer): the check files on the change branch. Each error message of the
  Interface has a check, and one check runs `python3 -m wordfreq` as a process and reads the
  exit code.

## Risks to effectiveness

- The hook: a report that the model cannot satisfy could stop a run. The record bounds the
  reports to one for each set and three for each parent. So the model gets at most three
  messages for one commit. The hook never blocks a commit. If `check_writing.py` is missing or
  fails, the hook skips the writing part. The ten unit tests cover these cases.
- The progress log form: a longer line costs a few output tokens. A line split into two
  sentences loses nothing.
- Intake and ready: a split acceptance line keeps its "Given, when, then". A second sentence
  after the "then" is still part of the line, and the test writer reads it as before. The
  summary sentence describes behaviour that is not built yet, which matches "specs before
  code".
- The test writer: more checks (a process check, close values) cost a little in the red run
  and the build. The guard does not change, and the test writer still sees no app code.
- The specification reviewer judges rules that the script cannot see (one topic for each
  paragraph, no imperative in descriptive text, "may"). 9 of the 19 failing rounds had no
  script finding. The round does not reach those. The source rules (R2) reach a part of them.

## What not to try, and why

- The round 2 edit (the writing check in the verify skill, before the packets) was reverted.
  The hook replaces it with a mechanism that does not depend on the model.
- A change to `check_writing.py`: no remedy needs it. The script already skips code blocks,
  reads only `.md` files, and supports `--since <commit>`.
- A reviewer that ignores writing findings, or no writing rules in the packet. The user reads
  these specs. Round 1 showed that the writing findings fail reviews for a reason.
- The held transcript edit and the small frames: not part of this round.
- A fix for the security repeats: they are real faults.

## What the user must decide

1. The whole-run gate on specification-reviewer calls cannot say SAME OR BETTER with six runs
   on each side (see "Measurement and power"). There are three options.
   - Accept the whole runs as a regression guard, and the stage verdicts as the evidence.
     This is my recommendation.
   - Run twelve whole runs on each side (about $16 more).
   - Gate the calls against a freeze of all 48 saved whole runs. `commands.md` has the
     command as an optional step. The 48 runs span seven plugin states, so the comparison
     is rough.
2. The 10% cost floor in the `writing` gate mode, which differs from the other modes.
3. The hook runs on `main` too, not only on pdlc branches, for the reason above.
4. `run_experiment.py check` wrote `bench/results/s7-*/` (spec.json, applied.diff, check.txt)
   as a side effect, as in round 6. Nothing else outside `bench/experiments/round7/` changed.

## Notes on the harness

- `bench/sections/<stage>.json` has no `writing` field. H6's `recheck` adds it to a stage
  folder whose projects are still on disk, so the old baselines can be compared for free. The
  new baselines carry it from the start.
- The stage replay starts 12 sessions for a 12-run baseline (`ThreadPoolExecutor(max_workers=args.runs)`).
  The round 6 plan allowed 18 sessions at once, so this is inside that limit.
- Whole-run intake writes the summary differently from an intake replay (0 of 12 against 5 of
  6 wrote `--top N`). The cause is not known. The `/pdlc:ship` context is the only difference
  in the prompt.
- Nothing blocked the planning.
