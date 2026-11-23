# pdlc bench

The bench runs the pdlc plugin on a small sample project, and measures what a run costs,
how long it takes, and what it makes. Use it to see if an edit to pdlc makes pdlc cheaper
or weaker. The bench needs the `claude` command, and each run spends real money.

## Fixtures

A fixture is a sample project that pdlc works on.

| Fixture | Folder | What it is |
|---|---|---|
| `wordfreq` (default) | `fixture-app/` | A Python command that counts words. The intent adds a `--top N` option. |
| `todo-rust` | `fixtures/todo-rust/` | A to-do web app in Rust. The intent adds a "done" mark, in two changes. |
| `todo-clojure` | `fixtures/todo-clojure/` | The same web app in Clojure. |

The bench checks each result with scripted probes. The text of each intent is in
`run_bench.py`.

## Run one end-to-end run

From the root of the repository, run this command:

```
python3 bench/run_bench.py e2e --label my-try --fixture wordfreq --runs 1
```

The run copies the fixture into a throwaway folder, runs `/pdlc:ship` on it with the plugin
in `plugins/pdlc`, and writes `bench/results/my-try/e2e.json`. To measure a run in full, run
`python3 bench/metrics.py bench/results/my-try`. To compare two result files, run
`python3 bench/run_bench.py gate BASELINE.json CANDIDATE.json`.

A run stops when it has spent `--budget` dollars (the default is 20).

## What a run costs

- One `wordfreq` run costs about $2. `baseline.json` records $2.08.
- One `todo-rust` run costs about $7. The runs in `results/pr27-e2e-M-todo-rust` cost $7.00
  to $9.14.

## What is here

| Path | Holds |
|---|---|
| `run_bench.py` | The bench: the `e2e`, `stage`, `rebuild`, `gate`, and `freeze` commands. |
| `run_experiment.py`, `experiments/` | The scripts and the records of the speed rounds in `plans/archive/pdlc-speed.plan.md`. |
| `metrics.py`, `check_red.py`, `check_trailers.py` | The measures and the scripted verdicts of a run. |
| `baseline.json`, `reference.json` | Frozen results to compare with (baseline `r8-base`, and reference `r7`). |
| `sections/` | Snapshots of finished projects, and the stage baselines. Read `sections/README.md`. |
| `seeds/` | Planted defects, to test if the reviewers find them. |
| `results/` | The results that stay. See below. |
| `test_bench.py` | The tests of the bench. |

## The results folder

`bench/results/` keeps only the `pr27-*` folders. Each one has `e2e.json` and one
`run<N>.shiplog.jsonl` for each run. They are the whole-run results of the pull request that
made pdlc declarative (PR #27). `M` is the run of the master plugin, and `N` is the run of the
new plugin.

| Folder | Fixture |
|---|---|
| `pr27-e2e-M-wordfreq`, `pr27-e2e-N-wordfreq` | `wordfreq` |
| `pr27-e2e-M-todo-rust`, `pr27-e2e-N-todo-rust`, `pr27-e2e-N2-todo-rust` | `todo-rust` |

The older folders are in git history. The stage baselines that they made are in
`sections/`. The raw event streams of a new run (`*.stream.jsonl` and `run*.json`) stay
local, because `.gitignore` excludes them.
