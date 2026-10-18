# Sections of the pdlc pipeline

A whole run of pdlc varies a lot, because each stage depends on the stages before it. To optimise
one section, replay only that section, many times, from the same starting state.

`project.bundle` is a git bundle of the project of the reference run `r5-compliance-by-risk-3`.
`python3 bench/run_bench.py stage --stage <stage> --label <label>` clones it, puts the project at
the commit where the stage starts, and runs that stage alone in a fresh session.

| Section | Starts at the commit | Finishes with the commit | Share of a whole run |
|---|---|---|---|
| intake | Set up pdlc | Specify IN-0001 | 14% |
| ready | Specify IN-0001 | Ready IN-0001 | under 1% |
| change | Ready IN-0001 | Plan IN-0001 | 1% |
| tests | Plan IN-0001 | Tests reviewed CH-0001 | 26% |
| build | Tests reviewed CH-0001 | Built CH-0001 | 9% |
| show | Built CH-0001 | Visual review CH-0001 | 10% |
| verify | Visual review CH-0001 | Verified CH-0001 | 33% |

The shares come from `bench/reference.json`. The start-up turns of a whole run (7%) belong to no
stage. A replay starts each stage with a fresh context. A whole run carries the context of every
earlier stage. So the sum of the replays shows how much that carried context costs.

To make a new snapshot, take the project folder of a reference run that finished, and run
`git -C <project> bundle create bench/sections/project.bundle --all`. Then update the run name
above.
