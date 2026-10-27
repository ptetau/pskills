# Vet Report: pdlc:intake

**Skill:** `pdlc:intake` · version `2dda99f9aa32`
**Suite:** `evals/pdlc-intake/suite.json` · `a88a6fc2b7b8`
**Run:** `new3-20261027T123815Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

SKILL.md changed since this suite was written; the rubric may be stale. `/vet pdlc:intake --regen` rebuilds it.

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 87.9 | Weighted share of the rubric met across all runs |
| Stability | 61.7 | How little the output changed between runs |
| **Overall** | **73.6 (C)** | √(quality × stability) |

Per-run quality: min 81.8 · median 89.8 · max 90.9

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 87.9 | 60.7 | 73 (C) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

VERDICT-TO-WRITE

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 The specs hold all of the request of the user, in the exact… | outcome | 3 | 91.7% | 42.5 · major_drift | 66.7% | - |
| R2 The user can find each detail that the run decided alone, a… | outcome | 3 | 75% | 60 · minor_drift | 66.7% | - |
| R3 After the run, each spec tells a reader the current truth. … | outcome | 3 | 100% | 42.5 · major_drift | 50% | - |
| R4 The run records its work in a `Specify` commit on main, and… | structure | 2 | 100% | 90 · equivalent | 100% | 90 · equivalent |
| R5 Each requirement, spec, and error row that the run adds or … | structure | 2 | 50% | 60 · minor_drift | 50% | 60 · minor_drift |
| R6 Each stub spec that the run changes also gets the requireme… | structure | 2 | 100% | 60 · minor_drift | 50% | 60 · minor_drift |
| R7 The intent file records the request, its requirements, its … | structure | 2 | 91.7% | 60 · minor_drift | 66.7% | 60 · minor_drift |
| R8 Each part of the request is in the spec where pdlc says tha… | behavior | 2 | 75% | 60 · minor_drift | 83.4% | - |
| R9 The run asks the user only about a point with two possible … | behavior | 2 | 100% | 90 · equivalent | 100% | - |
| R10 The final reply tells the user what intake did and what com… | structure | 1 | 100% | 60 · minor_drift | 83.4% | 60 · minor_drift |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 defaults Add a --top N option to wordfreq. With i… | typical: one new option, with `defaults` | 84.8 | 55.9 | 3/3 |
| P02 Stop ignoring case when wordfreq counts words. `R… | change of a behaviour that exists, without `defaults`, with one plain meaning | 90.9 | 65.5 | 3/3 |

---

## Where it falls short

### R5 Each requirement, spec, and error row that the run adds or changes has the pdlc form (thi… — met in 50% of runs

met 0 · partial 6 · missed 0

> N can be any whole number greater than zero, as in `3` or `+3`. N can also be a number — P01#1
> A missing N gives the same error (assumed). The command checks N before it reads the file (assumed). — P01#2

### R2 The user can find each detail that the run decided alone, and can change the detail later. — met in 75% of runs

met 3 · partial 3 · missed 0

> N can be any whole number greater than zero, as in `3` or `+3`. — P01#1
> Given the values `+3` and `007`, when I run `wordfreq --top VALUE FILE` for each value, then the output is the same as for `--top 3`. — P01#2

### R8 Each part of the request is in the spec where pdlc says that the part belongs. — met in 75% of runs

met 3 · partial 3 · missed 0

> wordfreq counts a word with a capital letter apart from the same word in lowercase. The — P02#1
> `wordfreq` counts `Rose` and `rose` as two different words. It prints each word in the case that the file gives it. — P02#2

## Where it varies

### R1 · P01 — major_drift · 2 / 1 of 3

- 2 runs (P01#1, P01#3): R4 (top option) and R5 (bad value) hold the exact message and exit code 2; acceptance lines cover 0, -1, 2.5, abc and an empty value; a bad N gets the --top error ahead of other errors
- 1 runs (P01#2): Exact message and exit code 2 are kept, but the edge lines use 1.5 instead of 2.5, and an (assumed) rule sends `wordfreq --top 0` with no FILE to the usage line instead of the user's --top error

Every run keeps the user's message and exit code. P01#2 tests 1.5 instead of 2.5 and decides that a bad N with no FILE gives the usage line, which narrows the user's rule. P01#1 picks the opposite precedence, and P01#3 tests 0, -1 and 2.5 directly.

### R3 · P01 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P01#1): Summary names --top N and the error; R3 (usage line) changes to `usage: wordfreq [--top N] FILE` with was/now Notes; README note maps the 'prints each word' line to R4
- 1 runs (P01#2): Summary names --top N and the error; R1 (word lines) and R3 (usage) both change in place with was/now Notes; the usage line stays the same; README note present
- 1 runs (P01#3): Summary names only --top N; R3 (usage) has a was/now Note and keeps the old usage line; there is no README note, because the run says the README has no line with old wording

The README note appears in two runs but not in P01#3. Only P01#2 rewrites R1 to show the old behaviour as replaced. Only P01#1 changes the usage line, and only P01#3 leaves the error out of the summary.

## What to fix

FIX-TO-WRITE

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
