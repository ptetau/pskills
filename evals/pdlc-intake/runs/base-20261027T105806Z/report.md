# Vet Report: pdlc:intake

**Skill:** `pdlc:intake` · version `86b5b7219e50`
**Suite:** `evals/pdlc-intake/suite.json` · `a88a6fc2b7b8`
**Run:** `base-20261027T105806Z` · 2 prompts × 3 runs · 5/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 92.3 | Weighted share of the rubric met across all runs |
| Stability | 55.1 | How little the output changed between runs |
| **Overall** | **71.3 (C)** | √(quality × stability) |

Per-run quality: min 84.1 · median 88.6 · max 100

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 92.3 | 54.1 | 70.7 (C) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The old intake skill writes the request into the specs in the user's own words: R1 (all of the request), R4 (the commit) and R9 (questions) pass in each usable run, and every item passes in at least 80% of runs. The biggest issue is stability (55.1). The runs differ in which details they mark `(assumed)` (R2), in how much old wording they remove (R3), and in the recon requirements of the stub specs (R6). One run of P01 died on an API error that was not about the skill, so 5 of 6 runs are usable.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 The specs hold all of the request of the user, in the exact… | outcome | 3 | 100% | 60 · minor_drift | 83.4% | - |
| R2 The user can find each detail that the run decided alone, a… | outcome | 3 | 80% | 30 · contradictory | 41.7% | - |
| R3 After the run, each spec tells a reader the current truth. … | outcome | 3 | 100% | 30 · contradictory | 41.7% | - |
| R4 The run records its work in a `Specify` commit on main, and… | structure | 2 | 100% | 90 · equivalent | 100% | 60 · minor_drift |
| R5 Each requirement, spec, and error row that the run adds or … | structure | 2 | 80% | 60 · minor_drift | 41.7% | 60 · minor_drift |
| R6 Each stub spec that the run changes also gets the requireme… | structure | 2 | 90% | 42.5 · major_drift | 41.7% | 60 · minor_drift |
| R7 The intent file records the request, its requirements, its … | structure | 2 | 90% | 60 · minor_drift | 58.4% | 60 · minor_drift |
| R8 Each part of the request is in the spec where pdlc says tha… | behavior | 2 | 90% | 42.5 · major_drift | 83.4% | - |
| R9 The run asks the user only about a point with two possible … | behavior | 2 | 100% | 90 · equivalent | 100% | - |
| R10 The final reply tells the user what intake did and what com… | structure | 1 | 90% | 60 · minor_drift | 66.7% | 60 · minor_drift |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 defaults Add a --top N option to wordfreq. With i… | typical: one new option, with `defaults` | 88.6 | 54.1 | 2/3 |
| P02 Stop ignoring case when wordfreq counts words. `R… | change of a behaviour that exists, without `defaults`, with one plain meaning | 94.7 | 54.1 | 3/3 |

---

## Where it falls short

Every item met in at least 80% of runs.
## Where it varies

### R3 · P01 — contradictory · 1 / 1 of 2

- 1 runs (P01#1): The summary names --top N. Only R3 (usage line) is changed, with a was/now Note that changes the line to `usage: wordfreq [--top N] FILE`. R1 (word counts) stays built and unchanged. Has the README Note.
- 1 runs (P01#2): The summary names --top N. R1 (word lines) and R3 (usage line) are changed, each with a was/now Note. R1 is limited to runs with no --top, and the usage line text stays `usage: wordfreq FILE`. Has the README Note.

The runs disagree on which behaviour the request replaces. Run 1 replaces the usage line text with `usage: wordfreq [--top N] FILE` and leaves R1 alone. Run 2 keeps `usage: wordfreq FILE` and instead changes R1 and the argument rule of R3. The two R3 (usage line) specs and their was/now Notes cannot both hold.

### R2 · P02 — contradictory · 1 / 1 / 1 of 3

- 1 runs (P02#1): Assumes a case-insensitive alphabetical order with the capital first (`a`, `Rose`, `rose`, `saw`), marked in the CAP R2 text and two acceptance lines, with one Decided line under R2.
- 1 runs (P02#2): Assumes character-code order (`Rose` before `a`), marked in the changed CAP R2 text and one acceptance line, with one Decided line under R2.
- 1 runs (P02#3): Assumes character-code order (`Rose` before `a`), marked only in a CAP R3 acceptance line while R2 stays built, with one Decided line keyed to R3.

Every run marks one assumed sort decision in the correct form. But P02#1 puts `a` before `Rose`, and P02#2 and P02#3 put `Rose` before `a`. These are incompatible spec outcomes.

### R6 · P01 — major_drift · 1 / 1 of 2

- 1 runs (P01#1): The job goes from stub to active. R1 (word counts, with order) and R2 (unreadable file) say Status: built with no Source: recon, and the run flags that recon did not run. R3 (usage line) is proposed.
- 1 runs (P01#2): The job goes from stub to active. R2 (unreadable file) says built with Source: recon. R1 (word lines) and R3 (usage line) are recon requirements, changed to proposed and still marked Source: recon.

One run has the Source: recon marker on its recon requirements and the other run has none. The runs also differ on whether R1 stays built or becomes proposed. CAP-word-counting stays a stub in both runs.

### R8 · P02 — major_drift · 2 / 1 of 3

- 1 runs (P02#1): The case rule is in CAP-word-counting.R3, and a new JOB-report-word-frequencies.R4 says again that words that differ in case get separate lines.
- 2 runs (P02#2, P02#3): The case rule is only in CAP-word-counting. The job spec is left unchanged and the run says that it needs no change.

P02#1 changes the job spec and states the case rule there again. P02#2 and P02#3 say that the job needs no change and keep everything in the capability.

## What to fix

1. "4. Write the patches": list the kinds of detail that always get `(assumed)`, for example an error code, an order, or a limit → moves R2.
2. "4. Write the patches": tell the run to search each spec for the old wording of a changed behaviour → moves R3.
3. "3. Deepen stub specs": name the minimum set of recon requirements, one for each behaviour of the code that the request touches → moves R6.

## Excluded runs and lost judges

- P01#3 — run agent died

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
