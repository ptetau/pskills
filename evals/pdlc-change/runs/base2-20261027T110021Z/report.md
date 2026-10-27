# Vet Report: pdlc:change

**Skill:** `pdlc:change` · version `c50b050e9e1b`
**Suite:** `evals/pdlc-change/suite.json` · `1715fd2392de`
**Run:** `base2-20261027T110021Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 97.1 | Weighted share of the rubric met across all runs |
| Stability | 68.7 | How little the output changed between runs |
| **Overall** | **81.7 (B)** | √(quality × stability) |

Per-run quality: min 89.1 · median 100 · max 100

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 97.1 | 70.2 | 82.6 (B) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

This is the second run of the old change skill (0.3.0), to measure the noise of the eval. Overall is 81.7, against 79.4 in the first run, and `compare_vet.py` shows NO REGRESSION between the two. Thus, the score of the same skill moves by about 2 points between runs, and stability by about 3 points. The old skill writes the README step the same way in each run: its "Check" is "none", and the specification review reads the README.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 The change spec has the path, the header, and the sections … | structure | 2 | 100% | 60 · minor_drift | 83.4% | 60 · minor_drift |
| R2 The user gets one change for each spec of IN-0001 (the --to… | outcome | 3 | 100% | 95 · equivalent | 100% | - |
| R3 The "Requirements" section copies each requirement of the c… | behavior | 2 | 100% | 100 · identical | 100% | - |
| R4 A test writer who cannot see the code can write each check … | outcome | 3 | 83.3% | 60 · minor_drift | 66.7% | - |
| R5 "Files" and "Check files" list only what this job change is… | behavior | 2 | 100% | 100 · identical | 100% | - |
| R6 The "Steps" section has one step for each requirement and a… | structure | 2 | 100% | 60 · minor_drift | 50% | 60 · minor_drift |
| R7 The intent file lists the changes and holds a new handoff f… | structure | 2 | 100% | 60 · minor_drift | 50% | 60 · minor_drift |
| R8 The run leaves one Plan commit on main and changes nothing … | structure | 2 | 91.7% | 80 · minor_drift | 83.4% | 60 · minor_drift |
| R9 The last message tells the user where the work stands and w… | outcome | 3 | 100% | 60 · minor_drift | 50% | - |
| R10 Each decision that the run makes without an instruction is … | behavior | 2 | 100% | 25 · major_drift | 50% | - |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 defaults | typical | 100 | 67.8 | 3/3 |
| P02 IN-0001 | named intent, interactive | 94.2 | 72.6 | 3/3 |

---

## Where it falls short

Every item met in at least 80% of runs.
## Where it varies

### R10 · P01 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P01#1): One assumed decision on error precedence, marked in the Interface and recorded in Notes and Decided on defaults; the short name is not marked.
- 1 runs (P01#2): One assumed decision on the short name 'top-option', recorded in Notes and Decided on defaults; error precedence is left in Open, not decided.
- 1 runs (P01#3): Two assumed decisions (the short name and the step order), recorded in Notes, Decided on defaults and the progress log; error precedence is neither decided nor flagged.

The runs record different assumed decisions. Run 1 decides error precedence by default, run 2 leaves it open, and run 3 does not raise it. Runs 2 and 3 mark the short name, and run 1 does not.

### R10 · P02 — major_drift · 2 / 1 of 3

- 2 runs (P02#1, P02#2): No (assumed) marker in the change spec, 'Decided on defaults' is 'none', and Notes is unchanged
- 1 runs (P02#3): Makes an assumed decision on error precedence and marks it (assumed) in the Interface, in 'Decided on defaults', and in the Notes of the intent

Only P02#3 makes and records a default decision, in all three required places. P02#1 and P02#2 record no decision and say 'none'.

## What to fix

1. None for this run. It measures noise. See the first baseline for the fixes.

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
