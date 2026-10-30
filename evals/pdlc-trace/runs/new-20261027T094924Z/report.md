# Vet Report: pdlc:trace

**Skill:** `pdlc:trace` · version `9e0f3c5ac70e`
**Suite:** `evals/pdlc-trace/suite.json` · `0d06ef760af0`
**Run:** `new-20261027T094924Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

SKILL.md changed since this suite was written; the rubric may be stale. `/vet pdlc:trace --regen` rebuilds it.

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 83.3 | Weighted share of the rubric met across all runs |
| Stability | 68.2 | How little the output changed between runs |
| **Overall** | **75.4 (C)** | √(quality × stability) |

Per-run quality: min 71.4 · median 86.4 · max 90.6

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 83.3 | 69 | 75.8 (C) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The new trace skill (0.4.0) gives true facts and changes nothing: R2 (true facts) rises to 100%, and R9 (no change) passes in each run. Against the old version (0.3.0), overall rises from 71.2 to 75.4, and `compare_vet.py` shows NO REGRESSION. Stability rises by 9.7 points, but quality falls by 3.4 points, inside the tolerance of 5. The biggest issue is the answer to "why does this line exist?": no run says in full which requirement the line serves and gives the chain (R3). Also, no run cites a source for each link (R6).

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 The first lines of the reply answer the question that the u… | outcome | 3 | 83.3% | 75 · minor_drift | 83.4% | - |
| R2 Each fact in the answer is true for the project, and the an… | outcome | 3 | 100% | 60 · minor_drift | 83.4% | - |
| R3 For a question about code with trace trailers, the reply fo… | structure | 2 | 50% | 60 · minor_drift | 66.7% | - |
| R4 For a question about an intent, the reply gives the require… | structure | 2 | 100% | 60 · minor_drift | 66.7% | - |
| R5 For a question about a requirement, the reply gives the req… | structure | 2 | - | - | - | - |
| R6 Each link in the answer names its source, so that the user … | structure | 2 | 50% | 60 · minor_drift | 66.7% | 60 · minor_drift |
| R7 When the trace reaches a change, the reply links to the fil… | structure | 1 | 100% | 75 · minor_drift | 83.4% | 60 · minor_drift |
| R8 The reply tells the user about each missing link that the t… | structure | 2 | 100% | 60 · minor_drift | 33.3% | - |
| R9 The run changes nothing in the project. | behavior | 2 | 100% | 90 · equivalent | 100% | - |
| R10 Each ID in the prose of the reply comes with a short descri… | behavior | 1 | 50% | 75 · minor_drift | 100% | - |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 Why does line 26 of wordfreq/cli.py exist? | typical | 75 | 64.3 | 3/3 |
| P02 defaults. What did IN-0001 (the --top option) cha… | reverse direction (from an intent to code), with defaults | 90.6 | 73.1 | 3/3 |

---

## Where it falls short

### R3 For a question about code with trace trailers, the reply follows the chain from the code … — met in 50% of runs

met 0 · partial 3 · missed 0

> The commit covers all three requirements. Line 26 serves R7 only. — P01#1
> Requirement: JOB-report-word-frequencies.R7 (print only the N most common words), status `verified`. — P01#2

### R6 Each link in the answer names its source, so that the user can open it. — met in 50% of runs

met 0 · partial 6 · missed 0

> Tests are locked at b1f1432. — P01#1
> Intent IN-0002 (wordfreq top huge number) records it with status `new` — P01#2

### R10 Each ID in the prose of the reply comes with a short description. — met in 50% of runs

met 0 · partial 6 · missed 0

> `proposal.md` says R7 has 19 checks. — P01#1
> IN-0001 and CH-0001 have no ticket (`Ticket: none`). — P01#2

## Where it varies

No item drifted beyond minor_drift.
## What to fix

1. Outputs: "the answer names the one requirement that the asked line serves, then the chain of the commit" → moves R3 (the chain from code to ticket) and R1 (plain answer).
2. Outputs: give one form for each link. A commit link gives the short hash and subject, and a spec, intent or change link gives the file path → moves R6 (a source for each link).
3. Constraints: each short ID in the reply, such as "R7", keeps a short description → moves R10 (a description for each ID).

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
