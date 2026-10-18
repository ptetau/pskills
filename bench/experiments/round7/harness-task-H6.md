# Harness task H6: count the writing findings that a run leaves, and gate on them

Add a free metric to `bench/run_bench.py`. The metric is the number of writing findings in the
packet text that a stage (or a whole run) wrote. The findings come from `pdlc/bin/check_writing.py`. Add a
gate mode `--target writing`. The mode judges the metric with the permutation test and the
guards of the `waiting` mode. Change only `bench/run_bench.py` and `bench/test_bench.py`. None
of the tests calls a model.

"Packet text" means the files whose writing the specification packet checks. These are the
README and other `.md` files outside `pdlc/`, the specs under `pdlc/specs/`, and the change spec
`pdlc/changes/*/change.md` (see `text_files` in
`plugins/pdlc/skills/init/references/bin/make_packets.py`). Handoffs, proposals, intents,
packets and results are not in a packet, so they do not count.

## 1. The metric (put it after `run_unit_checks`, before `inspect_project`)

```python
# The text whose writing the specification packet checks: the README and other docs outside
# pdlc/, the specs, and the change spec. A finding elsewhere costs no review round.
PACKET_TEXT = re.compile(r"^(?:pdlc/specs/.*\.md|pdlc/changes/[^/]+/change\.md|(?!pdlc/).*\.md)$")


def writing_findings(project, since):
    """The writing-check findings in the packet text that the commits after `since` wrote.

    Returns {"count", "files", "findings"}. It runs the project's own pdlc/bin/check_writing.py
    with --since, so the rules are the ones that the reviewers see. The project must be checked
    out at the tip that holds the text. When the script is missing or fails, "count" is None and
    "error" says why.
    """
    project = Path(project)
    changed = git(project, "diff", "--name-only", since + "...HEAD").stdout.split()
    files = [f for f in changed if PACKET_TEXT.match(f) and (project / f).is_file()]
    if not files:
        return {"count": 0, "files": [], "findings": []}
    script = project / "pdlc" / "bin" / "check_writing.py"
    if not script.is_file():
        return {"count": None, "files": files, "findings": [], "error": "no pdlc/bin/check_writing.py"}
    try:
        done = subprocess.run([sys.executable, str(script), "--since", since, *files], cwd=project,
                              capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as error:
        return {"count": None, "files": files, "findings": [], "error": repr(error)}
    findings = [line for line in done.stdout.splitlines() if " · " in line]
    return {"count": len(findings), "files": files, "findings": findings}
```

## 2. Where the metric is read

`inspect_project(project)`: after `git(project, "checkout", "-q", tip)` and before the unit
checks, add
`root = git(project, "rev-list", "--max-parents=0", "HEAD").stdout.split()[0]` and
`out["writing"] = writing_findings(project, root)`. A whole run writes everything after its
first commit, so the count covers the whole run.

`check_stage(project, stage, entry)`: right after `git(project, "checkout", "-q", tip_branch(project))`,
add `extra["writing"] = writing_findings(project, entry)`, for every stage.

A new function `stage_outcome(stage, check, entry)`, put right after `check_stage`. It returns
the dict that `command_stage` builds today as `analysis["outcome"]`, with two more keys:
`"entry": entry` and `"writing": check["extra"]["writing"]`. Then `command_stage` calls
`analysis["outcome"] = stage_outcome(args.stage, check, entry)` in place of the literal dict.

```python
def stage_outcome(stage, check, entry):
    """The outcome of one stage replay, in the shape that summarise and gate read."""
    return {
        "stage": stage, "entry": entry, "check": check,
        "merge_check": {"stage": ["ok   " + stage] if check["ok"] else ["FAIL " + stage]},
        "probes": check["extra"]["probes"] if stage == "build" else {"passed": len(PROBES), "total": len(PROBES), "failed": []},
        "unit": check["extra"]["unit"] if stage == "build" else {"ok": True, "ran": 0},
        "verify_rounds": None,
        "stops": [s for s in check["subjects"] if s.startswith("Stop ")],
        "writing": check["extra"]["writing"],
    }
```

`command_recheck(args)`: it must also work for a stage folder, so that an old stage result gets
the count without a new replay. Read `stage = summary.get("stage")`. For each run whose project
folder exists: if `stage` is set, do
`entry = run["outcome"].get("entry") or entry_commit(project, STAGE_REPLAY[stage][0])` and
`run["outcome"] = stage_outcome(stage, check_stage(project, stage, entry), entry)`. If not, call
`inspect_project(project)` as today.

`summarise(result)`: add the key
`"writing": [(r["outcome"].get("writing") or {}).get("count") for r in runs]`. A run without the
metric gives `None`.

## 3. The gate mode `writing` (a new branch in `gate`, before `elif target and target.startswith("calls:")`)

```python
    elif target == "writing":
        before, after = base["writing"], cand["writing"]
        if not before or not after or None in before or None in after:
            missing = "baseline" if (not before or None in before) else "candidate"
            change, needed, few, p_value, detail = 0.0, min_gain, False, None, {}
            gain_text = none_text = ("the %s has no writing count, so the findings cannot be judged "
                                     "(run `recheck` on its folder)" % missing)
        else:
            chance = permutation_p(before, after)
            p_value = chance
            needed = min_gain
            few = min(len(before), len(after)) < min_runs
            mean_before, mean_after = statistics.mean(before), statistics.mean(after)
            change = (mean_after - mean_before) / mean_before if mean_before else 0.0
            detail = {"target": "writing", "findings_before": mean_before, "findings_after": mean_after}
            if run_change > max(base["noise"], 0.25) or (run_change > 0.10 and permutation_p(cand["costs"], base["costs"]) <= alpha):
                worse.append("a run costs %.0f%% more, and that is not luck" % (run_change * 100))
            if chance > alpha:
                change = 0.0
            gain_text = "writing findings fell from %.1f to %.1f a run (%.0f%% fewer), and the chance that this is luck is %.0f%%" % (
                mean_before, mean_after, -change * 100, chance * 100)
            none_text = "writing findings changed from %.1f to %.1f a run (%+.0f%%), and the chance that this is luck is %.0f%% (it must be %.0f%% or less)" % (
                mean_before, mean_after, change * 100, chance * 100, alpha * 100)
```

The cost guard differs from the `waiting` mode in one point. A stage that costs up to 10% more
is not a regression here, also when the rise is not luck. The reason is this: the edits that
this mode judges can add one amend turn to a stage (about 4% of the tests stage). Their saving
is in a later stage. A rise above 10% is a regression when it is not luck. A rise above the
noise of the baseline, and above 25%, is a regression also when it could be luck. The `waiting`
and `calls:` modes use the same test for a rise.

The other guards stay as they are in `gate`. These are a stage that did not finish or failed
its check (`completed`), the probes, and the project's own checks. The planted defects and the
speed limit also stay.

In `command_gate`, print a line for this mode, after the `waiting` line:

```python
    elif detail and detail["target"] == "writing":
        print("writing    %.1f -> %.1f findings a run, and a run costs %+.0f%%" % (
            detail["findings_before"], detail["findings_after"], result["cost_change"] * 100))
```

The help of `--target` gets the new mode. Its new text is "an agent that the edit aims at,
for example pdlc:reviewer; or waiting; or writing (the writing findings that a run leaves)".
The docstring at the top of the file gets one more line under the `gate` command. The
line is "With `--target writing`, the gate judges the writing findings that a run leaves in its
specs, change spec and README."

## 4. Tests (in `bench/test_bench.py`, none of them calls a model)

A class `WritingFindingsTest`. A helper `project()` makes a git repository in a temp folder
(cleaned up with `addCleanup`). The repository holds three files: `pdlc/bin/check_writing.py`,
copied from `run_bench.DEFAULT_PLUGIN / "skills/init/references/bin/check_writing.py"`,
`pdlc/specs/jobs/JOB-x.md` with `"# JOB-x · Do a thing\n\nA short line.\n"`, and `README.md`
with `"# App\n\nA short line.\n"`. The helper commits them as "base" with `run_bench.git`.

- `test_counts_the_findings_in_the_packet_text_written_since_a_commit`: take `base` = the hash
  of HEAD. Then write five changes. `pdlc/changes/CH-0001-x/change.md` gets a 30-word
  sentence and the line "The R3 checks pass.". `pdlc/changes/CH-0001-x/handoff.md` gets "The
  R4 checks pass.". `pdlc/inbox/IN-0001-x.md` gets a 30-word sentence. `README.md` gets the
  line "It picks a color.". The line of `JOB-x.md` becomes "A short line. See R2 for more.".
  Commit. Then `writing_findings(root, base)` gives `count` 4 and `files` equal to
  `["README.md", "pdlc/changes/CH-0001-x/change.md", "pdlc/specs/jobs/JOB-x.md"]`, and no
  finding names `handoff.md` or `inbox`.
- `test_lines_from_before_the_commit_do_not_count`: commit a 30-word sentence in `JOB-x.md`,
  take `since` = HEAD, then commit a short new line in the same file. `writing_findings(root, since)["count"]` is 0.
- `test_no_text_file_gives_zero`: commit only `app.py`. The result is
  `{"count": 0, "files": [], "findings": []}`.
- `test_without_the_script_the_count_is_none`: delete `pdlc/bin/check_writing.py`, commit
  "It picks a color." in `README.md`. `count` is None and `"error"` is in the result.

A class `WritingGateTest`, like `WaitingGateTest`. A helper `writing_result(costs, findings, completed=True)`
builds a result with one run for each cost. A run has `totals` with that `cost_usd` and
`duration_s` 300, `wall_s` 300, empty `stages`, and `waiting` of zero. Its `outcome` has
`merge_check` `{"stage": ["ok   tests"]}` (or `["FAIL tests"]` when not completed), 8 of 8
probes, `unit` ok, `verify_rounds` None, and `writing` `{"count": n, "files": [], "findings": []}`.
When `n` is None, leave the `writing` key out. Baseline costs are
`[0.36, 0.39, 0.37, 0.39, 0.38, 0.38]` and baseline findings `[4, 1, 2, 2, 6, 3]`.

- `test_fewer_findings_are_kept`: the candidate has the same costs and findings `[0, 0, 1, 0, 0, 0]`.
  The verdict starts with "SAME OR BETTER".
- `test_the_same_findings_are_no_gain`: the same findings on both sides. "NO GAIN".
- `test_fewer_findings_in_a_slightly_dearer_stage_are_kept`: candidate costs are the baseline
  costs times 1.04, findings `[0, 0, 1, 0, 0, 0]`. "SAME OR BETTER".
- `test_fewer_findings_in_a_clearly_dearer_stage_are_a_regression`: costs times 1.15. The
  verdict starts with "REGRESSION", and a reason has "costs 15% more".
- `test_a_missing_count_cannot_be_judged`: the baseline runs have no `writing` key. "NO GAIN",
  and a reason has "no writing count".
- `test_fewer_findings_in_three_runs_need_more_runs`: three candidate runs with findings
  `[0, 0, 0]`. "NEED MORE RUNS".
- `test_a_stage_that_did_not_finish_beats_fewer_findings`: the candidate has `completed=False`.
  "REGRESSION".
- `test_the_gate_prints_the_writing_line`: write both results to temp files, run
  `command_gate` with `target="writing"` (as `test_the_gate_prints_the_calls_line` does), and
  make sure that the output has `"writing    3.0 -> 0.2 findings a run"`.

Four tests in `StageReplayTest`:

- `test_check_stage_counts_the_writing_findings_of_the_stage`: make the "verify" project. Then
  `check_stage(project, "build", entry_commit(project, "Tests reviewed CH-0001"))["extra"]["writing"]`
  has `count` 0 and `files` equal to
  `["README.md", "pdlc/changes/CH-0001-top-option/change.md", "pdlc/specs/jobs/JOB-report-word-frequencies.md"]`.
- `test_a_stage_outcome_carries_the_writing_count_and_the_entry`: with the same `check` and
  `entry`, `stage_outcome("build", check, entry)` has `writing` equal to
  `check["extra"]["writing"]`, `entry` equal to `entry`, and `merge_check` equal to
  `{"stage": ["ok   build"]}`.
- `test_inspect_project_counts_the_findings_of_a_whole_run`: `inspect_project(project)` on the
  "verify" project gives `writing["count"]` 11, and its `files` include `README.md` and
  `pdlc/specs/jobs/JOB-report-word-frequencies.md`. The number 11 comes from the snapshot at
  its "Visual review CH-0001" commit. If `check_writing.py` changes, compute the number again
  with `python3 pdlc/bin/check_writing.py --since <root> <files>` in a clone of the bundle.
- `test_recheck_reads_a_stage_folder_again`: make the "verify" project, and take
  `shown = entry_commit(project, "Built CH-0001")`. In a temp folder, write `e2e.json` with
  `{"label": "x", "stage": "show", "plugin_commit": "x", "model": "m", "effort": "e", "runs": [run]}`,
  where `run` is `{"totals": {"cost_usd": 0.2, "duration_s": 1.0}, "stages": {}, "waiting": {}, "wall_s": 1.0, "project": str(project), "outcome": {"stage": "show", "entry": shown}}`,
  and `run1.json` with `run`. Call `run_bench.command_recheck(Namespace(folder=str(folder)))`.
  Then the `e2e.json` has `outcome["check"]["ok"]` True, `outcome["writing"]["count"]` 0, and
  `outcome["entry"]` equal to `shown`.

Then run `python3 bench/test_bench.py` and the other repository tests in `AGENTS.md`.

## 5. Check by hand

Run `python3 bench/run_bench.py recheck bench/results/s-tests-base`. Its six projects are
still on disk. The `recheck` writes the count into each run of
`bench/results/s-tests-base/e2e.json`. Then run
`python3 bench/run_bench.py gate bench/results/s-tests-base/e2e.json bench/results/s-tests-base/e2e.json --target writing`.
The gate prints `writing    3.0 -> 3.0 findings a run` and "NO GAIN", because the two sides
hold the same runs. Then run the same `recheck` on `bench/results/s-intake-base`,
`s-ready-base`, `s-change-base`, `s-build-base`, `s-show-base` and `s-verify-base`. The counts
for each run must be: tests `[4, 1, 2, 2, 6, 3]`, intake `[9, 7, 12, 9, 7, 13]`, ready
`[12, 11, 8, 5, 8, 8]`, change `[1, 1, 1, 1, 1, 1]`, build `[0, 0, 0, 3, 0, 0]`, show
`[0, 0, 0, 0, 0, 0]`, and verify `[0, 0, 0, 0, 1, 0]`. The planner measured these with the
same method on 18 October 2026.
