# Vet Report: pdlc:show

**Skill:** `pdlc:show` · version `0fd54b344108`
**Suite:** `evals/pdlc-show/suite.json` · `0c3500a61ac6`
**Run:** `base-20261027T191547Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 92 | Weighted share of the rubric met across all runs |
| Stability | 67.2 | How little the output changed between runs |
| **Overall** | **78.6 (C)** | √(quality × stability) |

Per-run quality: min 84.1 · median 93.2 · max 95.5

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 92 | 65.2 | 77.4 (C) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The old version of show (0.3.0) is the baseline for the declarative version. Overall is 78.6 (C), with quality at 92 and stability at 67.2. All 6 runs are usable. Each run records all 22 acceptance lines, with the real command and the exit code. Thus, R1 (each line has its own step) and R2 (each step proves its line) are at 100%.

The only weak item is R7 (the handoff, frame by frame), at 50%. In each run, "Done" puts the frames of the bad-N lines in one group, for example "frames 12 to 19".

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 A reviewer can find each acceptance line of CH-0001 (top op… | outcome | 3 | 100% | 60 · minor_drift | 66.7% | - |
| R2 Each step proves its acceptance line as a user meets the co… | outcome | 3 | 100% | 60 · minor_drift | 33.3% | - |
| R3 `visual.json` is a terminal script that anyone can record a… | structure | 2 | 91.7% | 42.5 · major_drift | 50% | 60 · minor_drift |
| R4 The change folder holds `review.gif` and its frames from a … | structure | 2 | 100% | 75 · minor_drift | 83.4% | 90 · equivalent |
| R5 The run looks at the recorded frames itself before the comm… | behavior | 2 | 91.7% | 60 · minor_drift | 66.7% | - |
| R6 The run changes only the records of the visual review. The … | behavior | 2 | 100% | 75 · minor_drift | 83.4% | - |
| R7 The handoff to `/pdlc:verify` obeys the template. The hando… | structure | 2 | 50% | 60 · minor_drift | 33.3% | 60 · minor_drift |
| R8 One commit, `Visual review CH-0001`, holds all the files of… | structure | 2 | 91.7% | 90 · equivalent | 100% | 90 · equivalent |
| R9 The final reply tells the user that `/pdlc:verify` is next. | structure | 1 | 100% | 90 · equivalent | 100% | 90 · equivalent |
| R10 The user and the `verify` stage get a true account of the r… | outcome | 3 | 91.7% | 60 · minor_drift | 66.7% | - |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 defaults | typical | 93.9 | 60.9 | 3/3 |
| P02 CH-0001 | change named by its ID, without defaults | 90.2 | 69.5 | 3/3 |

---

## Where it falls short

### R7 The handoff to `/pdlc:verify` obeys the template. The handoff tells what the GIF shows, f… — met in 50% of runs

met 0 · partial 6 · missed 0

> Frames 12 to 19 give the same error and exit code 2. — P01#1
> Frames 12 to 20: these values of N give the `--top` error on standard error — P01#2

## Where it varies

### R3 · P01 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P01#1): The helper makes inputs at run time in a mktemp folder under ${TMPDIR:-/tmp}, so the commit holds no input files. The last step is 'PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests'.
- 1 runs (P01#2): The input files are committed in samples/. The shell helper uses mktemp temp files to capture output. The last step is a plain 'python3 -m unittest discover -s tests'. There is an extra step for the sample files.
- 1 runs (P01#3): The input files are committed in samples/. The Python helper uses no temp paths. visual.json sets width and height. The last step is 'python3 -m unittest discover -s tests; echo "exit code: $?"'.

P01#1 makes its inputs in a /tmp scratch folder and does not commit them. P01#2 and P01#3 commit sample files in the change folder. That is a material structural difference, and the helpers and last-step commands also differ.

## What to fix

1. "Done" in the handoff gives one line for each frame, also when a group of frames shows the same error → moves R7 (the handoff, frame by frame).

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
