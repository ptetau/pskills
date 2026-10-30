# Vet Report: pdlc:intake

**Skill:** `pdlc:intake` · version `af6a7e5a98c5`
**Suite:** `evals/pdlc-intake/suite.json` · `a88a6fc2b7b8`
**Run:** `new2-20261027T120100Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

SKILL.md changed since this suite was written; the rubric may be stale. `/vet pdlc:intake --regen` rebuilds it.

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 86 | Weighted share of the rubric met across all runs |
| Stability | 60.4 | How little the output changed between runs |
| **Overall** | **72.1 (C)** | √(quality × stability) |

Per-run quality: min 72.7 · median 86.4 · max 93.2

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 86 | 62 | 73 (C) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The second version of intake (0.4.0, commit 1eca1aa) fixes R1 (all of the request, in the user's words), which is now at 100%. Overall is 72.1 against 71.3 for the old version. But `compare_vet.py` shows REGRESSION, because R3 (the current truth in each spec) falls from 100% to 75%.

In each run of P02 (stop ignoring case), the run changes CAP-word-counting.R2 (order of the pairs), but writes no was-and-now Note for it. The old skill told the run to add that Note for each changed requirement. The new skill gave the Note only in the rule "The newest words win". Thus, a change for a different reason got no Note. The next commit adds the rule back, and a new eval measures it.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 The specs hold all of the request of the user, in the exact… | outcome | 3 | 100% | 75 · minor_drift | 83.4% | - |
| R2 The user can find each detail that the run decided alone, a… | outcome | 3 | 66.7% | 30 · contradictory | 33.3% | - |
| R3 After the run, each spec tells a reader the current truth. … | outcome | 3 | 75% | 60 · minor_drift | 50% | - |
| R4 The run records its work in a `Specify` commit on main, and… | structure | 2 | 91.7% | 75 · minor_drift | 66.7% | 60 · minor_drift |
| R5 Each requirement, spec, and error row that the run adds or … | structure | 2 | 75% | 60 · minor_drift | 50% | 60 · minor_drift |
| R6 Each stub spec that the run changes also gets the requireme… | structure | 2 | 100% | 60 · minor_drift | 50% | 60 · minor_drift |
| R7 The intent file records the request, its requirements, its … | structure | 2 | 91.7% | 60 · minor_drift | 66.7% | 25 · major_drift |
| R8 Each part of the request is in the spec where pdlc says tha… | behavior | 2 | 75% | 75 · minor_drift | 83.4% | - |
| R9 The run asks the user only about a point with two possible … | behavior | 2 | 100% | 75 · minor_drift | 66.7% | - |
| R10 The final reply tells the user what intake did and what com… | structure | 1 | 100% | 60 · minor_drift | 66.7% | 60 · minor_drift |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 defaults Add a --top N option to wordfreq. With i… | typical: one new option, with `defaults` | 90.2 | 65.5 | 3/3 |
| P02 Stop ignoring case when wordfreq counts words. `R… | change of a behaviour that exists, without `defaults`, with one plain meaning | 81.8 | 58.6 | 3/3 |

---

## Where it falls short

### R2 The user can find each detail that the run decided alone, and can change the detail later. — met in 66.7% of runs

met 2 · partial 4 · missed 0

> When N is not a whole number greater than zero (`+3` counts), wordfreq fails with — P01#1
> when `wordfreq --top 10 FILE` runs, then it prints `the 3`, `and 2`, `bat 1`, `cat 1`, and `hat 1`. — P01#2

### R3 After the run, each spec tells a reader the current truth. The summaries show the new beh… — met in 75% of runs

met 3 · partial 3 · missed 0

> CAP-word-counting.R2 (order of the pairs): changed — P02#1
> CAP-word-counting.R2 (order of the pairs): changed — P02#2

### R5 Each requirement, spec, and error row that the run adds or changes has the pdlc form (thi… — met in 75% of runs

met 3 · partial 3 · missed 0

> The lines keep the format and the order of the output without the option. N can be any whole number greater than zero, for example `3`, `+3`, or `02`. The opti… — P01#3
> When two words differ only in case, the word with the capital letter at the first difference comes first (assumed). — P02#2

### R8 Each part of the request is in the spec where pdlc says that the part belongs. — met in 75% of runs

met 3 · partial 3 · missed 0

> The command `wordfreq FILE` counts words that differ in case as different words. — P02#1
> It counts words that differ in case as different words, and prints one line for each. — P02#2

## Where it varies

### R2 · P02 — contradictory · 1 / 1 / 1 of 3

- 1 runs (P02#1): Assumes code-point order (every uppercase before every lowercase, so Rose before a); marked (assumed) in the summary, R2 body and an acceptance line; one Decided-on-defaults line
- 1 runs (P02#2): Assumes case-insensitive alphabetical order with the capital first on a tie; marks only the capital-first rule; the `Zebra apple` line, the summary sentence and the TEA/Tea order are unmarked; one Decided-on-defaults li…
- 1 runs (P02#3): Assumes case-insensitive alphabetical order with the capital first; two separate (assumed) marks (R equals r, capital first) plus a marked full-order acceptance line; one Decided-on-defaults line

P02#1 assumes that uppercase words sort before all lowercase words (Rose before a). P02#2 and P02#3 assume case-insensitive order (a before Rose), so the recorded defaults conflict. P02#2 also leaves several invented ordering details unmarked, and P02#3 marks them all.

### R7 · cross — major_drift · 3 / 1 of 4

- 3 runs (P01#1, P01#2, P02#1): The intent file has the template header line and the user's words in 'What and why'. Requirements are listed with added/changed. Notes lines use the template forms. The handoff has the 'intake → ready' title, a Time lin…
- 1 runs (P02#2): The same header, sections, notes forms and handoff, but the file keeps the template's guidance paragraphs. These are the header-field note, the instructions in Requirements, Changes and Acceptance checks, and the Notes …

All runs share the sections, their order, the header and the handoff layout. P02#2 keeps the template's guidance prose in each section and the other three runs remove it, so the file layout is materially different.

## What to fix

1. Constraints: each changed requirement gets the Note `<ID>: was "<old>", now "<new>"`, for each reason of the change → moves R3 (the current truth in each spec). This fix is in the next commit.
2. Constraints: when the run makes a new order, each part of the order gets the mark `(assumed)`. An example is the order of words that differ only in case → moves R2 (each decision that the user can find) and R5 (the pdlc form).

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
