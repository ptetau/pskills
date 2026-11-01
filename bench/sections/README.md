# Sections of the pdlc pipeline

A complete run of pdlc varies a lot, because each stage depends on the stages before it. To optimise
one section, replay only that section, many times, from the same starting state.

A snapshot is a git bundle of the project of a finished run. Three snapshots exist:

| Snapshot | File | App | Run it comes from |
|---|---|---|---|
| `wordfreq` (the default) | `wordfreq.bundle` | `bench/fixture-app`, one change | `r8-base-wordfreq` |
| `todo-rust` | `todo-rust.bundle` | `bench/fixtures/todo-rust`, three changes, stacked CH-0001, CH-0003, CH-0002 | `r8-base-todo-rust-2` |
| `r5` | `project.bundle` | `bench/fixture-app`, from an early pdlc | `r5-compliance-by-risk-3` |

`python3 bench/run_bench.py stage --stage <stage> --label <label> [--snapshot <name>]` clones a
snapshot, puts the project at the commit where the stage starts, and runs that stage alone in a
fresh session. `python3 bench/run_bench.py prepare --state <state> --snapshot <name> --dest <folder>`
makes the same project for a tool that drives the run, for example `/vet`. Each run brings the
pdlc files of the project up to the plugin under test with the upgrade script, and commits the
change as "Upgrade pdlc".

## Stages of `wordfreq` and `todo-rust`

| Section | Starts at the commit | Finishes with the commit |
|---|---|---|
| intake | Set up pdlc | Specify IN-0001 |
| ready | Specify IN-0001 | Ready IN-0001 |
| change | Ready IN-0001 | Plan IN-0001 |
| acceptance | Plan IN-0001 | Acceptance reviewed IN-0001 |
| tests | Acceptance reviewed IN-0001 | Tests reviewed CH-0001 |
| build | Tests reviewed CH-0001 | Built CH-0001 |
| verify | Built CH-0001 | Verified CH-0001 |
| show | Verified CH-0001 | Propose CH-0001 |

The state `done` is the tip of the newest pdlc branch, the proposal. The branch of a state comes
from the `Branch:` field of the change spec (`build`, `verify`, `show`) or of the intent (the other
stages) at the start commit. The value `none` means main. The last commit of main that comes
before the start commit is the main of the project.

## The old snapshot `r5`

`r5` keeps its own table. The stages are `intake`, `ready`, `change`, `tests`, `build`, `verify`, and `show`,
with no `acceptance` stage. The show stage there finishes with "Visual review CH-0001". Use
`--snapshot r5` to make again the results from before round 8. An `r5` project now also gets the
upgrade: four refreshed default specs and `pdlc/version.json`, in the "Upgrade pdlc" commit. So an
`r5` result is close to, but not the same as, a result from before round 8.

The shares of a complete run in `bench/reference.json` (`intake` 14%, `tests` 26%, `build` 9%, `show` 10%, `verify` 33%) come from `r5`.

## Record a snapshot

1. Run `python3 bench/run_bench.py e2e --label <label> --runs 1 --out <folder>` (add
   `--fixture todo-rust` for the other app).
2. Check the run: all probes pass, no "Stop" commit, the merge check is `ok`.
3. From the root of the repository, run
   `git -C <project> switch -q main && git -C <project> bundle create "$PWD/bench/sections/<snapshot>.bundle" --all`.
   The project folder is the `project` field in `<folder>/<label>/run1.json`. The full path
   keeps the bundle out of the project.
4. Write the run name in the table above.
