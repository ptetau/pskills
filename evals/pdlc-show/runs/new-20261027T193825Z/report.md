# Vet Report: pdlc:show

**Skill:** `pdlc:show` · version `19ab20c11daf`
**Suite:** `evals/pdlc-show/suite.json` · `0c3500a61ac6`
**Run:** `new-20261027T193825Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

SKILL.md changed since this suite was written; the rubric may be stale. `/vet pdlc:show --regen` rebuilds it.

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 90.9 | Weighted share of the rubric met across all runs |
| Stability | 70.5 | How little the output changed between runs |
| **Overall** | **80.1 (B)** | √(quality × stability) |

Per-run quality: min 86.4 · median 90.9 · max 95.5

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 90.9 | 72.2 | 81 (B) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The declarative version of show (0.4.0, commit 887d6ce) does the work as well as the old one. Overall is 80.1 (B) against 78.6, and stability rises by 3.3 points. `compare_vet.py` shows NO REGRESSION. R1 (each line has its own step), R2 (each step proves its line), and R10 (a true account) are at 100%.

R3 (a script that anyone can record again) falls from 91.7% to 58.3%. Its weight is 2, so the gate does not fail on it. Five runs make their input files in a temporary folder, and the rubric wants them in the change folder. Two old runs did the same. Neither version of the skill has a rule about input files, only about helper scripts. A script that makes its input files with `mktemp` still records again.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 A reviewer can find each acceptance line of CH-0001 (top op… | outcome | 3 | 100% | 90 · equivalent | 100% | - |
| R2 Each step proves its acceptance line as a user meets the co… | outcome | 3 | 100% | 42.5 · major_drift | 66.7% | - |
| R3 `visual.json` is a terminal script that anyone can record a… | structure | 2 | 58.3% | 42.5 · major_drift | 66.7% | 60 · minor_drift |
| R4 The change folder holds `review.gif` and its frames from a … | structure | 2 | 100% | 90 · equivalent | 100% | 90 · equivalent |
| R5 The run looks at the recorded frames itself before the comm… | behavior | 2 | 100% | 75 · minor_drift | 83.4% | - |
| R6 The run changes only the records of the visual review. The … | behavior | 2 | 91.7% | 75 · minor_drift | 83.4% | - |
| R7 The handoff to `/pdlc:verify` obeys the template. The hando… | structure | 2 | 58.3% | 42.5 · major_drift | 33.3% | 25 · major_drift |
| R8 One commit, `Visual review CH-0001`, holds all the files of… | structure | 2 | 91.7% | 90 · equivalent | 100% | 60 · minor_drift |
| R9 The final reply tells the user that `/pdlc:verify` is next. | structure | 1 | 100% | 90 · equivalent | 100% | 90 · equivalent |
| R10 The user and the `verify` stage get a true account of the r… | outcome | 3 | 100% | 90 · equivalent | 100% | - |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 defaults | typical | 89.4 | 75 | 3/3 |
| P02 CH-0001 | change named by its ID, without defaults | 92.4 | 69.3 | 3/3 |

---

## Where it falls short

### R3 `visual.json` is a terminal script that anyone can record again from the project root, an… — met in 58.3% of runs

met 1 · partial 5 · missed 0

> SAMPLES = ROOT / "pdlc" / ".tools" / "s" — P01#1
> with tempfile.TemporaryDirectory() as folder: — P01#2

### R7 The handoff to `/pdlc:verify` obeys the template. The handoff tells what the GIF shows, f… — met in 58.3% of runs

met 1 · partial 5 · missed 0

> Frames 11 to 19: R7 (top N). A bad N gives the `TOP_INVALID` error and exit code 2. — P01#1
> Frames 11 to 19 show `--top` with `0`, `-1`, `abc`, `2.5`, `3.0`, `+3`, `1e2`, an empty value, and no value. — P01#2

## Where it varies

### R2 · P02 — major_drift · 2 / 1 of 3

- 2 runs (P02#1, P02#2): Each step runs a committed helper shell script (wf.sh or try.sh). The helper writes the Given content to a temp folder, runs python3 -m wordfreq, and prints the file content, standard output, standard error, and the exi…
- 1 runs (P02#3): Each step runs python3 -m wordfreq directly on committed sample files, with '; echo "exit code: $?"', so the outputs are merged and the frame shows the real command.

P02#1 and P02#2 wrap the command in a helper script, so the frame shows 'sh .../wf.sh' or 'sh .../try.sh', not the real command. P02#3 runs 'python3 -m wordfreq' directly and echoes the exit code. All three runs use the same arguments and input content.

### R3 · P02 — major_drift · 2 / 1 of 3

- 2 runs (P02#1, P02#2): The terminal visual.json calls a helper script in the change folder. The helper makes the input files at run time in a mktemp folder outside the change folder, so the input files are not committed. The last step is 'PYT…
- 1 runs (P02#3): The terminal visual.json has no helper. It reads input files committed under the change folder's samples/ with relative paths, sets width and height explicitly, and ends with a plain 'python3 -m unittest discover -s tes…

The runs supply inputs in different ways. P02#1 and P02#2 make the inputs in a temp folder (/tmp) at run time, through a helper. P02#3 commits sample files in the change folder and uses them by relative path.

### R7 · P02 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P02#1): The handoff has the show → verify title and the six sections. Done puts the frames in groups by requirement (frames 01-03 R5, 04-21 R7, 22 R8, 23 checks) and says '22 of 22'.
- 1 runs (P02#2): The handoff has the show → verify title and the six sections. Done has a table that describes all 23 frames one by one and says '22 of 22'.
- 1 runs (P02#3): The handoff has the show → verify title and the six sections. Done describes the frames one by one, but puts frames 12-19 in one bullet, and says '22 acceptance lines out of 22'.

Done describes the frames in a different way in each run. P02#1 gives requirement ranges only, P02#2 gives a full table of all 23 frames, and P02#3 describes most frames one by one but groups frames 12-19.

### R7 · cross — major_drift · 2 / 1 / 1 of 4

- 2 runs (P01#1, P01#2): A bulleted Done list, mostly one bullet for each frame, with some ranges (frames 1 to 3, 11 to 19). It says '22 of 22'. P01#1 lists two assumed defaults and P01#2 writes 'none'.
- 1 runs (P02#1): Done puts the frames in coarse groups for each requirement (01 to 03, 04 to 21, 22, 23) and says '22 of 22'. Decided on defaults is 'none'.
- 1 runs (P02#2): Done has a table with one row for each frame, 1 to 23, and says '22 of 22'. Decided on defaults is 'none'.

All runs have the same title, a real timestamp, the six sections in order, and the '22 of 22' count. The Done section differs in a real way. One run gives a full table of the frames, one by one. Two runs give a list that is mostly one by one but has some ranges. One run puts 18 frames in one range, which is the example of a partial result in the rubric.

## What to fix

1. Constraints: each input file of a step is in the change folder, as each helper script is → moves R3 (a script that anyone can record again).
2. "Done" in the handoff gives one line for each frame, also when a group of frames shows the same error → moves R7 (the handoff, frame by frame).

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
