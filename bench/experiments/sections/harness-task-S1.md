# Harness task S1: replay one stage from a frozen snapshot

Add a `stage` command to `bench/run_bench.py`. It replays one pdlc stage, in a fresh session,
from the commit where that stage starts in a frozen project. Each section of the pipeline can
then be measured and changed alone. Change only `bench/run_bench.py` and `bench/test_bench.py`.

The snapshot is `bench/sections/project.bundle`: a git bundle of the project of the reference run
`r5-compliance-by-risk-3`. Its `main` ends at "Plan IN-0001: top option". Its branch
`pdlc/CH-0001-top-option` holds the commits from "Start CH-0001" to "Propose CH-0001".

## 1. Constants (put them after `INTENT`)

```python
SECTIONS = HERE / "sections"
SNAPSHOT = SECTIONS / "project.bundle"
CHANGE_BRANCH = "pdlc/CH-0001-top-option"
# stage: (subject that starts the entry commit, branch to work on, prompt, subject that proves the stage finished)
STAGE_REPLAY = {
    "intake": ("Set up pdlc", "main", "/pdlc:intake defaults " + INTENT, "Specify IN-"),
    "ready": ("Specify IN-0001", "main", "/pdlc:ready defaults", "Ready IN-"),
    "change": ("Ready IN-0001", "main", "/pdlc:change defaults", "Plan IN-"),
    "tests": ("Plan IN-0001", "main", "/pdlc:tests defaults", "Tests reviewed CH-"),
    "build": ("Tests reviewed CH-0001", CHANGE_BRANCH, "/pdlc:build defaults", "Built CH-"),
    "show": ("Built CH-0001", CHANGE_BRANCH, "/pdlc:show defaults", "Visual review CH-"),
    "verify": ("Visual review CH-0001", CHANGE_BRANCH, "/pdlc:verify defaults", "Verified CH-"),
}
```

## 2. Functions (put them before `# ---------------------------------------------------------------- the commands`)

`entry_commit(project, subject)`: run `git log --all --format=%H %s` (use the `git` helper). Return
the full hash of the newest commit whose subject starts with `subject` (the log is newest first,
so the first match). Raise `RuntimeError("no commit starts with %r" % subject)` if none matches.

`tip_branch(project)`: return the name of the local branch, other than `main`, whose last commit is
the newest (`git for-each-ref --sort=-committerdate --format=%(refname:short) refs/heads/`, first
name that is not `main`). Return `"main"` if there is no other branch.

`make_stage_project(dest, stage, plugin)`:
1. `subprocess.run(["git", "clone", "-q", str(SNAPSHOT), str(dest)], check=True)`.
2. `git(dest, "remote", "remove", "origin")`. The project then has no remote, as in a real run.
3. `subject, branch, prompt, done = STAGE_REPLAY[stage]`, `entry = entry_commit(dest, subject)`.
4. If `branch == "main"`: `git(dest, "checkout", "-q", "-B", "main", entry)`.
   Else: `plan = entry_commit(dest, "Plan IN-0001")`, then `git(dest, "checkout", "-q", "-B", "main", plan)`,
   then `git(dest, "checkout", "-q", "-B", branch, entry)`.
5. `sync_verbatim(dest, plugin)`. If `dest / "pdlc" / ".tools"` does not exist, make the symlink
   `os.symlink(ensure_tools(), dest / "pdlc" / ".tools")`.
6. If `git(dest, "status", "--porcelain").stdout.strip()` is not empty:
   `git(dest, "add", "-A", "pdlc")` and `git(dest, "commit", "-q", "-m", "Upgrade pdlc")`.
7. Return `(Path(dest), entry)`.

`check_stage(project, stage, entry)` returns a dict. Steps:
1. `subjects = git(project, "log", "--all", "--format=%s", "--not", entry).stdout.splitlines()`,
   without the subjects that are exactly `"Upgrade pdlc"`.
2. `done = STAGE_REPLAY[stage][3]`; `finished = any(s.startswith(done) for s in subjects)`;
   `stopped = any(s.startswith("Stop ") for s in subjects)`.
3. `extra = {}`. Then check out the tip that the stage left: `tip = tip_branch(project)`,
   `git(project, "checkout", "-q", tip)`. Then, by stage:
   - `"tests"`: `extra["locked"]` is True when the file `pdlc/changes/<folder>/change.md` (any folder
     under `pdlc/changes/` whose name starts with `CH-`) contains a line that starts with
     `Tests-Locked:`. `extra["checks_fail_first"] = not run_unit_checks(project)["ok"]`.
   - `"build"`: `extra["unit"] = run_unit_checks(project)`, `extra["probes"] = run_probes(project)`.
   - `"show"`: `extra["gif"]` is True when any `pdlc/changes/CH-*/review.gif` exists, and
     `extra["frames"]` is the number of files that match `pdlc/changes/CH-*/frames/*.png`.
   - `"verify"`: run `python3 pdlc/bin/check_merge.py` in the project (as `inspect_project` does) and
     set `extra["merge"]` to the first line of its output, stripped.
   Then `git(project, "checkout", "-q", "main")`.
4. `passed` is True for intake, ready and change. For tests: `extra["locked"] and extra["checks_fail_first"]`.
   For build: `extra["unit"]["ok"] and not extra["probes"]["failed"]`. For show: `extra["gif"] and extra["frames"] > 0`.
   For verify: `extra["merge"].startswith("ok")`.
5. Return `{"ok": finished and not stopped and passed, "finished": finished, "stopped": stopped,
   "subjects": subjects, "extra": extra}`.

`command_stage(args)`:
1. `plugin = Path(args.plugin).resolve()`, `out_dir = Path(args.out) / args.label`, make it.
   `prompt = STAGE_REPLAY[args.stage][2]`.
2. A function `one(number)` that: makes `work = Path(tempfile.mkdtemp(prefix="pdlc-stage-"))`;
   `project, entry = make_stage_project(work / "app", args.stage, plugin)`;
   `events, wall, err = run_claude(prompt, project, plugin, out_dir / ("run%d.stream.jsonl" % number), timeout=args.timeout, budget_usd=args.budget)`;
   `analysis = analyse(events)`; `check = check_stage(project, args.stage, entry)`; then
   ```python
   analysis["outcome"] = {
       "stage": args.stage, "check": check,
       "merge_check": {"stage": ["ok   " + args.stage] if check["ok"] else ["FAIL " + args.stage]},
       "probes": check["extra"]["probes"] if args.stage == "build" else {"passed": len(PROBES), "total": len(PROBES), "failed": []},
       "unit": check["extra"]["unit"] if args.stage == "build" else {"ok": True, "ran": 0},
       "verify_rounds": None,
       "stops": [s for s in check["subjects"] if s.startswith("Stop ")],
   }
   analysis.update({"wall_s": wall, "project": str(project), "stderr": err[-500:]})
   ```
   writes `out_dir / ("run%d.json" % number)` and returns `analysis`. Wrap the body in
   `try/except Exception as error` and return None (after printing the error) so one failure does
   not stop the others.
3. Run `one` for 1..args.runs in a `ThreadPoolExecutor(max_workers=args.runs)`. Keep the results
   that are not None, in run order.
4. `summary = {"label": args.label, "stage": args.stage, "plugin_commit": git(plugin, "rev-parse", "--short", "HEAD").stdout.strip(), "model": MODEL, "effort": EFFORT, "runs": runs}`.
   Write it to `out_dir / "e2e.json"`, so that `freeze`, `gate` and `report` read it as they are.
5. Print one line for each run: `"run %d: $%.2f, %ss, ok %s"`.

CLI: add a sub-parser `stage`. Its options are `--stage` (required, `choices=sorted(STAGE_REPLAY)`),
`--label` (required), `--runs` (int, default 6), and `--plugin` (default `str(DEFAULT_PLUGIN)`). It
also takes `--out` (default `str(HERE / "results")`), `--timeout` (int, default 1800), and
`--budget` (float, default 6.0). Wire it in `main()` like the other commands.

## 3. Tests (a class `StageReplayTest` in `bench/test_bench.py`; none of them calls a model)

Make each project in a temp folder (`tempfile.mkdtemp()`, cleaned up with `addCleanup`).

- `test_each_stage_starts_at_its_entry_commit`: call `make_stage_project` for every stage. The
  subject of `HEAD` starts with the entry subject of the stage. (When the subject of `HEAD` is
  "Upgrade pdlc", use `HEAD~1`.) `git rev-parse --abbrev-ref HEAD` is the stage's branch.
- `test_main_ends_at_the_plan_for_a_change_branch_stage`: for "build", the subject of `main` starts with "Plan IN-0001".
- `test_a_stage_project_has_no_remote`: `git remote` prints nothing.
- `test_a_stage_with_no_work_is_not_finished`: right after `make_stage_project(..., "show", ...)`,
  `check_stage(project, "show", entry)` gives `finished` False and `ok` False.
- `test_the_snapshot_passes_the_checks_of_earlier_stages`: make the "verify" project (its branch is
  at "Visual review CH-0001"). Then `check_stage(project, "show", entry_commit(project, "Built CH-0001"))`,
  `check_stage(project, "build", entry_commit(project, "Tests reviewed CH-0001"))` each give `ok` True.
  Then make the "build" project, whose branch is at "Tests reviewed CH-0001". There,
  `check_stage(project, "tests", entry_commit(project, "Plan IN-0001"))` gives `ok` True. The checks
  are locked, and they fail, because the code is not built yet.
- `test_a_changed_plugin_file_gets_an_upgrade_commit`: copy `DEFAULT_PLUGIN` to a temp folder, add a
  line to `skills/init/references/templates/README.md` in the copy, and `make_stage_project(..., "verify", copy)`.
  The subject of `HEAD` is "Upgrade pdlc", and the project's `pdlc/README.md` has the new line.

Then run `python3 bench/test_bench.py` and the other repository tests in `AGENTS.md`.
