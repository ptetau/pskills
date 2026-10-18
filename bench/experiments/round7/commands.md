# Round 7: the commands, in order

Run each step from the root of the repository. Do not go to the next step before the step
before it is done. A step that says "read" means: print the output and keep it for the
report. Report every output word for word.

## Step 1: build H6 (count the writing findings)

A Haiku agent builds `bench/experiments/round7/harness-task-H6.md`. Then run the tests:

```
python3 bench/test_bench.py
python3 improve-writing/scripts/test_check_writing.py
python3 scripts/sync_shared.py --check
python3 quiz-visual/scripts/test_quiz_visual.py
(cd plugins/pdlc && python3 -m unittest discover -s tests)
```

Then do the hand check of section 5 of the task. It reads the old stage results again, for
free, and must print the counts that the task gives:

```
for s in tests intake ready change build show verify; do python3 bench/run_bench.py recheck bench/results/s-$s-base; done
python3 - <<'EOF'
import json
for s in ("tests", "intake", "ready", "change", "build", "show", "verify"):
    runs = json.load(open("bench/results/s-%s-base/e2e.json" % s))["runs"]
    print(s, [r["outcome"]["writing"]["count"] for r in runs])
EOF
python3 bench/run_bench.py gate bench/results/s-tests-base/e2e.json bench/results/s-tests-base/e2e.json --target writing
```

## Step 2: new stage baselines (tests, intake, ready)

Keep the old files, then replay each stage on the plugin as it is now. The tests replay
starts 12 sessions and takes about 10 minutes. Then intake and ready run together.

```
cp bench/sections/tests.json bench/sections/tests-before-round-6.json
cp bench/sections/intake.json bench/sections/intake-before-round-6.json
cp bench/sections/ready.json bench/sections/ready-before-round-6.json
python3 bench/run_bench.py stage --stage tests --label s7-tests-base --runs 12 2>&1 | tee bench/results/s7-tests-base.log
python3 bench/run_bench.py stage --stage intake --label s7-intake-base --runs 6 > bench/results/s7-intake-base.log 2>&1 &
python3 bench/run_bench.py stage --stage ready --label s7-ready-base --runs 6 > bench/results/s7-ready-base.log 2>&1 &
wait
```

Read the runs. Every `ok` must be True, and every count must be a number:

```
python3 - <<'EOF'
import json
for s in ("tests", "intake", "ready"):
    runs = json.load(open("bench/results/s7-%s-base/e2e.json" % s))["runs"]
    print(s, "ok", [r["outcome"]["check"]["ok"] for r in runs])
    print(s, "writing", [r["outcome"]["writing"]["count"] for r in runs])
    print(s, "cost", [round(r["totals"]["cost_usd"], 3) for r in runs])
EOF
```

If a run is not ok, or a run is missing, replay 3 more with the label `s7-<stage>-base-b` and
give both `e2e.json` files to `freeze`. Then freeze each baseline:

```
python3 bench/run_bench.py freeze bench/results/s7-tests-base/e2e.json --out bench/sections/tests.json --label s7-tests-base
python3 bench/run_bench.py freeze bench/results/s7-intake-base/e2e.json --out bench/sections/intake.json --label s7-intake-base
python3 bench/run_bench.py freeze bench/results/s7-ready-base/e2e.json --out bench/sections/ready.json --label s7-ready-base
python3 bench/test_bench.py
```

Cost: about $7.6.

## Step 3: check the five specs

Each check must print `plugin tests: OK` and no `NEW FINDINGS`:

```
for s in bench/experiments/round7/s7-*.json; do echo "== $s"; python3 bench/run_experiment.py check "$s"; done
```

## Step 4: wave 1 (three experiments at the same time, 18 sessions)

```
python3 bench/run_experiment.py start bench/experiments/round7/s7-commit-writing-hook.json
python3 bench/run_experiment.py start bench/experiments/round7/s7-progress-log-form.json
python3 bench/run_experiment.py start bench/experiments/round7/s7-intake-spec-text.json
```

Wait for each one. Run the `wait` command again until it prints DONE:

```
python3 bench/run_experiment.py wait bench/experiments/round7/s7-commit-writing-hook.json --seconds 540
python3 bench/run_experiment.py wait bench/experiments/round7/s7-progress-log-form.json --seconds 540
python3 bench/run_experiment.py wait bench/experiments/round7/s7-intake-spec-text.json --seconds 540
```

Cost: about $6.2.

## Step 5: wave 2 (two experiments, 12 sessions)

Start wave 2 only when each `wait` of wave 1 printed DONE.

```
python3 bench/run_experiment.py start bench/experiments/round7/s7-ready-line-length.json
python3 bench/run_experiment.py start bench/experiments/round7/s7-test-writer-wrong-versions.json
python3 bench/run_experiment.py wait bench/experiments/round7/s7-ready-line-length.json --seconds 540
python3 bench/run_experiment.py wait bench/experiments/round7/s7-test-writer-wrong-versions.json --seconds 540
```

Cost: about $3.7.

## Step 6: read each experiment

The project of each run is in `bench/results/<id>-stage/run<n>.json`. This prints the paths:

```
projects() { python3 -c "import json,sys; print('\n'.join(r['project'] for r in json.load(open('bench/results/%s-stage/e2e.json' % sys.argv[1]))['runs']))" "$1"; }
```

For every experiment, print the verdict, the counts, and the costs:

```
for id in s7-commit-writing-hook s7-progress-log-form s7-intake-spec-text s7-ready-line-length s7-test-writer-wrong-versions; do
  echo "== $id"; cat bench/results/$id/DONE; cat bench/results/$id/gate.txt
  python3 -c "import json; runs = json.load(open('bench/results/$id-stage/e2e.json'))['runs']; print('writing', [r['outcome']['writing']['count'] for r in runs]); print('cost', [round(r['totals']['cost_usd'], 3) for r in runs]); print('ok', [r['outcome']['check']['ok'] for r in runs])"
done
```

Then the hand checks of the plan ("Decision tree"):

```
# the hook: how often it reported, and how often the model amended
grep -c 'writing finding' bench/results/s7-commit-writing-hook-stage/run*.stream.jsonl
grep -c 'commit --amend' bench/results/s7-commit-writing-hook-stage/run*.stream.jsonl
grep -c 'commit --amend' bench/results/s7-tests-base/run*.stream.jsonl
# the progress log lines that the tests stage wrote
for p in $(projects s7-progress-log-form); do echo "== $p"; git -C "$p" show pdlc/CH-0001-top-option:pdlc/changes/CH-0001-top-option/change.md | sed -n '/## Progress log/,$p'; done
# the spec text that intake and ready wrote: the summary, and the acceptance lines over 25 words
for id in s7-intake-spec-text s7-ready-line-length; do for p in $(projects $id); do echo "== $id $p"; git -C "$p" show main:pdlc/specs/jobs/JOB-report-word-frequencies.md | sed -n '/## Who and why/,/^## /p'; git -C "$p" show main:pdlc/specs/jobs/JOB-report-word-frequencies.md | grep '^- Given' | awk '{ if (NF > 25) print NF " words: " $0 }'; done; done
# the checks that the test writer wrote, and the result of the tests reviewer
for p in $(projects s7-test-writer-wrong-versions); do echo "== $p"; git -C "$p" show pdlc/CH-0001-top-option:tests/test_JOB_report_word_frequencies.py | grep -c 'subprocess'; git -C "$p" show pdlc/CH-0001-top-option:pdlc/changes/CH-0001-top-option/review/tests/result.md | head -12; done
```

## Step 7: more runs for an experiment (only when the decision tree asks for it)

Make a copy of the spec with the id `<id>-b`. Give it the runs that the decision tree gives
(6 or 3). Then start it, wait for it, freeze both sets, and gate again:

```
python3 - <<'EOF'
import json, sys
ID = "s7-commit-writing-hook"   # the experiment that needs more runs
RUNS = 6
spec = json.load(open("bench/experiments/round7/%s.json" % ID))
spec["id"] = ID + "-b"
spec["runs"] = RUNS
json.dump(spec, open("bench/experiments/round7/%s-b.json" % ID, "w"), indent=1, ensure_ascii=False)
EOF
python3 bench/run_experiment.py start bench/experiments/round7/<id>-b.json
python3 bench/run_experiment.py wait bench/experiments/round7/<id>-b.json --seconds 540
python3 bench/run_bench.py freeze bench/results/<id>-stage/e2e.json bench/results/<id>-b-stage/e2e.json --out bench/results/<id>/result.json --label <id>
python3 bench/run_bench.py gate bench/sections/<stage>.json bench/results/<id>/result.json --target writing
```

Cost: $2.3 for 6 tests runs, $1.6 for 6 intake runs, $1.4 for 6 ready runs.

## Step 8: apply the kept edits

Apply each kept spec, in rank order. Then run the tests:

```
python3 bench/run_experiment.py apply bench/experiments/round7/s7-commit-writing-hook.json
python3 bench/run_experiment.py apply bench/experiments/round7/s7-progress-log-form.json
python3 bench/run_experiment.py apply bench/experiments/round7/s7-intake-spec-text.json
python3 bench/run_experiment.py apply bench/experiments/round7/s7-ready-line-length.json
python3 bench/run_experiment.py apply bench/experiments/round7/s7-test-writer-wrong-versions.json
(cd plugins/pdlc && python3 -m unittest discover -s tests)
python3 scripts/sync_shared.py --check
python3 plugins/pdlc/skills/init/references/bin/check_writing.py plugins/pdlc/skills plugins/pdlc/agents
```

The writing check of the plugin prints the same six findings as before the round, and no new
one. The six are in `templates/README.md`, `reviews/tests.md`, `adapters/delivery-github.md`,
and `adapters/tracker-github-projects.md`.

## Step 9: the whole-run confirmation

Six whole runs at the same time, and the planted-defect check. About 12 minutes.

```
for n in 1 2 3 4 5 6; do python3 bench/run_bench.py e2e --label r7-whole-$n --runs 1 > bench/results/r7-whole-$n.log 2>&1 & done
python3 bench/run_bench.py seeds --label r7-whole-seeds > bench/results/r7-whole-seeds.log 2>&1 &
wait
cat bench/results/r7-whole-*.log
mkdir -p bench/results/r7-whole
python3 bench/run_bench.py freeze bench/results/r7-whole-{1,2,3,4,5,6}/e2e.json --seeds bench/results/r7-whole-seeds/seeds.json --out bench/results/r7-whole/result.json --label r7
```

The gates, against the reference of round 6:

```
python3 bench/run_bench.py gate bench/reference.json bench/results/r7-whole/result.json --target calls:pdlc:reviewer/specification | tee bench/results/r7-whole/gate-calls.txt
python3 bench/run_bench.py gate bench/reference.json bench/results/r7-whole/result.json | tee bench/results/r7-whole/gate.txt
python3 bench/run_bench.py gate bench/reference.json bench/results/r7-whole/result.json --target calls:pdlc:reviewer/tests
```

The hand checks on the six projects:

```
wholes() { for n in 1 2 3 4 5 6; do python3 -c "import json; print(json.load(open('bench/results/r7-whole-$n/e2e.json'))['runs'][0]['project'])"; done; }
# the summary names the new option at the Specify commit (0 of 12 did in round 6)
for p in $(wholes); do h=$(git -C "$p" log --all --format='%H %s' | grep ' Specify IN-0001' | head -1 | cut -d' ' -f1); echo "$p: $(git -C "$p" show $h:pdlc/specs/jobs/JOB-report-word-frequencies.md | sed -n '/## Who and why/,/^## /p' | grep -c -- '--top')"; done
# the verify rounds and the failed remits of each run
for p in $(wholes); do echo "== $p"; git -C "$p" log --all --format=%s | grep -E '^(Verify|Send back|Review tests|Stop) '; done
# the hook at work, and the findings each run left
grep -c 'writing finding' bench/results/r7-whole-*/run1.stream.jsonl
python3 -c "import json; print([json.load(open('bench/results/r7-whole-%d/e2e.json' % n))['runs'][0]['outcome']['writing']['count'] for n in range(1, 7)])"
```

Cost: about $8 for the runs and $0.7 for the seeds.

## Step 10 (optional): the writing count and the calls on more whole runs

The projects of the round 6 reference are still on disk. This adds the writing count to them,
without a new run, and gates the findings:

```
for n in 1 2 3 4 5 6; do python3 bench/run_bench.py recheck bench/results/r6-whole-b-$n; done
python3 bench/run_bench.py freeze bench/results/r6-whole-b-{1,2,3,4,5,6}/e2e.json --seeds bench/results/r6-whole-seeds/seeds.json --out bench/results/r6-whole-b/result-with-writing.json --label r6
python3 bench/run_bench.py gate bench/results/r6-whole-b/result-with-writing.json bench/results/r7-whole/result.json --target writing
```

Only if the user chose it: the calls gate against the 40 saved whole runs that finished. The
permutation test enumerates about 20 million splits, so the command takes several minutes.

```
python3 bench/run_bench.py freeze bench/results/baseline-{1,2,3,4,5,6}/e2e.json bench/results/r2-{1,2,3,4}/e2e.json bench/results/r2b-{1,2,3,4,5,6}/e2e.json bench/results/r3-foreground-agents-{1,2,3,4,5,6}/e2e.json bench/results/r3-lean-packets-{1,2,3,4,5,6}/e2e.json bench/results/r5-compliance-by-risk-{1,2,3,4,5,6}/e2e.json bench/results/r6-whole-b-{1,2,3,4,5,6}/e2e.json --out bench/results/r7-whole/history-40.json --label history-40
python3 bench/run_bench.py gate bench/results/r7-whole/history-40.json bench/results/r7-whole/result.json --target calls:pdlc:reviewer/specification
```

## Step 11: if the round is kept

Keep the old reference, and freeze the new one:

```
cp bench/reference.json bench/reference-after-round-6.json
python3 bench/run_bench.py freeze bench/results/r7-whole-{1,2,3,4,5,6}/e2e.json --seeds bench/results/r7-whole-seeds/seeds.json --out bench/reference.json --label r7
```

Then the orchestrator writes the result in the progress log of `plans/pdlc-speed.plan.md`.

## The budget

| Step | Cost |
|---|---|
| Baselines (tests 12, intake 6, ready 6) | $7.6 |
| Wave 1 (hook, progress log, intake) | $6.2 |
| Wave 2 (ready, test writer) | $3.7 |
| Top-ups (step 7), at most | $5.0 |
| Whole runs and seeds | $8.7 |
| Total | $31.2 of $42 |
