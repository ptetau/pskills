# Vet Report: pdlc:intake

**Skill:** `pdlc:intake` · version `fd2462012b50`
**Suite:** `evals/pdlc-intake/suite.json` · `a88a6fc2b7b8`
**Run:** `new-20261027T112920Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

SKILL.md changed since this suite was written; the rubric may be stale. `/vet pdlc:intake --regen` rebuilds it.

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 89.8 | Weighted share of the rubric met across all runs |
| Stability | 61.4 | How little the output changed between runs |
| **Overall** | **74.3 (C)** | √(quality × stability) |

Per-run quality: min 81.8 · median 89.8 · max 100

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 89.8 | 60.3 | 73.6 (C) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The first declarative version of intake (0.4.0, commit 887d6ce) scores higher overall than the old one: 74.3 against 71.3. Stability also rises by 6.3 points. But `compare_vet.py` shows REGRESSION, because R1 (all of the request, in the user's words) falls from 100% to 75%. In each run of P01 (one new option, with `defaults`), the run assumes that a "whole number" has digits only, so `+3` gives the error. The old runs make the same assumption, but their judge marked it as met. The assumption does narrow the user's words, so the next commit adds a constraint against it, and a new eval measures the constraint.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 The specs hold all of the request of the user, in the exact… | outcome | 3 | 75% | 60 · minor_drift | 83.4% | - |
| R2 The user can find each detail that the run decided alone, a… | outcome | 3 | 83.3% | 30 · contradictory | 33.3% | - |
| R3 After the run, each spec tells a reader the current truth. … | outcome | 3 | 83.3% | 42.5 · major_drift | 66.7% | - |
| R4 The run records its work in a `Specify` commit on main, and… | structure | 2 | 100% | 90 · equivalent | 100% | 90 · equivalent |
| R5 Each requirement, spec, and error row that the run adds or … | structure | 2 | 91.7% | 60 · minor_drift | 33.3% | 60 · minor_drift |
| R6 Each stub spec that the run changes also gets the requireme… | structure | 2 | 100% | 60 · minor_drift | 33.3% | 60 · minor_drift |
| R7 The intent file records the request, its requirements, its … | structure | 2 | 91.7% | 60 · minor_drift | 33.3% | 60 · minor_drift |
| R8 Each part of the request is in the spec where pdlc says tha… | behavior | 2 | 91.7% | 75 · minor_drift | 83.4% | - |
| R9 The run asks the user only about a point with two possible … | behavior | 2 | 100% | 75 · minor_drift | 100% | - |
| R10 The final reply tells the user what intake did and what com… | structure | 1 | 100% | 90 · equivalent | 100% | 60 · minor_drift |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 defaults Add a --top N option to wordfreq. With i… | typical: one new option, with `defaults` | 87.1 | 64.8 | 3/3 |
| P02 Stop ignoring case when wordfreq counts words. `R… | change of a behaviour that exists, without `defaults`, with one plain meaning | 92.4 | 55.9 | 3/3 |

---

## Where it falls short

### R1 The specs hold all of the request of the user, in the exact terms of the user. — met in 75% of runs

met 3 · partial 3 · missed 0

> N has digits only (assumed), so `2.0` and `+3` are not whole numbers. — P01#1
> A whole number has digits only (assumed), so `+3` and `3.0` are not whole numbers. — P01#2

## Where it varies

### R2 · P02 — contradictory · 1 / 1 / 1 of 3

- 1 runs (P02#1): One assumed decision: ties sort with capitals first (`Rose`, `a`, `rose`, `saw`). The mark comes with a reason outside the brackets. The JOB has no order line, and "Decided on defaults" has one line.
- 1 runs (P02#2): Two assumed decisions: ties sort alphabetically without case, then uppercase first (`a`, `Rose`, `rose`, `saw`). The CAP R2 and JOB R4 order lines are marked, and "Decided on defaults" has two lines.
- 1 runs (P02#3): Two assumed decisions: ties sort by character code (`Rose`, `a`, `rose`, `saw`). The mark is also in the CAP summary, the JOB R4 order line is marked, and "Decided on defaults" has two lines.

The assumed tie order is opposite between runs: P02#1 and P02#3 put `Rose` before `a`, and P02#2 puts `a` before `Rose`. The number of listed decisions also differs (one or two).

### R3 · P01 — major_drift · 2 / 1 of 3

- 2 runs (P01#1, P01#2): The job summary names --top N. The changed usage requirement has a was/now Note. A README Note maps the line 'prints each word with its count' to R4 (top option).
- 1 runs (P01#3): The job summary names --top N and the error. The changed usage requirement has a was/now Note. The run decides that no README line shows old behaviour, so it writes no README Note.

All runs update the summary and add the was/now Note. Runs 1 and 2 treat the README line as replaced and add a README Note. Run 3 decides that the README line is not replaced and adds none.

## What to fix

1. Constraints: an `(assumed)` detail adds to the words of the intent. The detail does not remove a value that the plain reading of those words permits, for example `+3` for "a whole number" → moves R1 (all of the request, in the user's words). This fix is in the next commit.
2. Constraints: tell the run to search each spec for the old wording of a changed behaviour → moves R3 (the current truth in each spec).

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
