# Vet Report: pdlc:ready

**Skill:** `pdlc:ready` · version `c64c16bfe52a`
**Suite:** `evals/pdlc-ready/suite.json` · `82a346c92ed1`
**Run:** `base-20261027T120100Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 80.7 | Weighted share of the rubric met across all runs |
| Stability | 53.8 | How little the output changed between runs |
| **Overall** | **65.9 (D)** | √(quality × stability) |

Per-run quality: min 75 · median 78.4 · max 93.2

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 80.7 | 51.1 | 64.2 (D) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The old version of ready (0.3.0) is the baseline for the declarative version. Overall is 65.9 (D), with quality at 80.7 and stability at 53.8. All 6 runs are usable. Two runs of P02 (interactive, no `defaults`) failed with an API safeguard error. A resume of the workflow ran them again, with the same prompt and the same settings.

The runs make each requirement `ready` and commit correctly, so R1 (the plan can start) and R7 (the commit) are at 100%. The weak items are R9 (the implied behaviour, at 50%) and R3 (checks with no guess, at 58.3%). Most runs keep "Given any file", or give an error code with no exact text.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 The user can go straight to the plan: at the end, IN-0001 (… | outcome | 3 | 100% | 60 · minor_drift | 66.7% | - |
| R2 After the run, the specs give one result for each command l… | outcome | 3 | 91.7% | 30 · contradictory | 66.7% | - |
| R3 A test writer can write each check of the intent with no gu… | outcome | 3 | 58.3% | 25 · major_drift | 50% | - |
| R4 The run asks the user only in the permitted form. Each mess… | structure | 2 | 100% | 62.5 · major_drift | 66.7% | 60 · minor_drift |
| R5 Each acceptance line and sentence that the run writes in a … | structure | 1 | 58.3% | 60 · minor_drift | 83.4% | 60 · minor_drift |
| R6 The intent keeps a full record of this stage. The record is… | structure | 2 | 91.7% | 60 · minor_drift | 66.7% | 60 · minor_drift |
| R7 The run ends in a commit on main with the subject `Ready IN… | structure | 2 | 100% | 75 · minor_drift | 83.4% | 90 · equivalent |
| R8 The final reply gives the result first, then what changed. … | structure | 2 | 75% | 60 · minor_drift | 66.7% | 60 · minor_drift |
| R9 The run examines the behaviour that the intent implies but … | behavior | 2 | 50% | 60 · minor_drift | 66.7% | - |
| R10 When the run changes what a requirement does, no spec text … | behavior | 2 | 66.7% | 42.5 · major_drift | 66.7% | - |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 defaults | typical: defaults, no intent named | 76.5 | 50.2 | 3/3 |
| P02 IN-0001 | interactive: intent named by ID, no defaults | 84.8 | 52 | 3/3 |

---

## Where it falls short

### R9 The run examines the behaviour that the intent implies but does not state. The handoff ho… — met in 50% of runs

met 0 · partial 6 · missed 0

> JOB-report-word-frequencies.R7: can N have any number of digits? → yes, a very large N prints all words (assumed) — P01#1
> Edge values of N: new lines for `00`, ` 3`, `1_0`, a full-width digit, and a very large N. — P01#2

### R3 A test writer can write each check of the intent with no guess. Each acceptance line has … — met in 58.3% of runs

met 1 · partial 5 · missed 0

> Given the arguments `a.txt b.txt`, when the user runs `wordfreq a.txt b.txt`, then the command gives the usage error (`USAGE`). — P01#1
> Given any file, when the user runs `wordfreq --top -1 FILE`, then the result is `TOP_INVALID`, with exit code 2. — P01#2

### R5 Each acceptance line and sentence that the run writes in a spec keeps the pdlc form. — met in 58.3% of runs

met 1 · partial 5 · missed 0

> then the command gives the usage error (`USAGE`). Standard error is `usage: wordfreq FILE`, standard output is empty, and the exit code is 2. — P01#1
> then the result is `USAGE_INVALID`. Standard error is `usage: wordfreq FILE`, standard output is empty, and the exit code is 2. — P01#2

### R10 When the run changes what a requirement does, no spec text still shows the old behaviour. — met in 66.7% of runs

met 2 · partial 4 · missed 0

> If the number of files is not one, the command gives the usage error. — P01#1
> If the number of files is not one, the command prints `usage: wordfreq FILE` to standard error (assumed). — P01#2

### R8 The final reply gives the result first, then what changed. The reply says that `/pdlc:cha… — met in 75% of runs

met 3 · partial 3 · missed 0

> New code `USAGE_INVALID` in DES-errors (error codes), for the usage lines of R5 and R8. — P01#2
> R1 is built and outside this intent, so I left it. — P01#3

## Where it varies

### R2 · P01 — contradictory · 2 / 1 of 3

- 1 runs (P01#1): New R9 (order of the checks) puts a repeated --top first, then a bad N, then the file count. A bad N with no FILE gives TOP_INVALID, but `--top abc --top 2 FILE` gives the usage error.
- 2 runs (P01#2, P01#3): A bad N wins over the file count and over a repeated --top. Acceptance lines give TOP_INVALID for `--top` or `--top 0` with no file and for `--top 0 --top 2 FILE`, with a Notes line.

For a bad N together with a second --top, P01#1 gives the usage error, but P01#2 and P01#3 give TOP_INVALID. All three give TOP_INVALID for a bad N with no FILE.

### R3 · P01 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P01#1): Replaces every 'Given any file' with concrete content (`b a b c a b`). Adds USAGE and FILE_UNREADABLE to DES-errors and names a code on each failure line. The 'then' refers to a named error ('the --top error (TOP_INVALI…
- 1 runs (P01#2): Keeps 'Given any file'. Adds only USAGE_INVALID. The 'then' gives a code but no exact text, and the missing.txt read-error line names no code.
- 1 runs (P01#3): Keeps 'Given any file'. Adds USAGE_INVALID and FILE_UNREADABLE, so each failure line names a code. The 'then' says 'the TOP_INVALID error' with no exact text.

Only P01#1 fixes the vague 'any file' givens. P01#2 leaves one failure line without a code and adds no read-error code, while P01#3 codes every line.

### R10 · P01 — major_drift · 2 / 1 of 3

- 1 runs (P01#1): Moves the order of the checks into a new R9 (order of the checks) and moves the matching Notes line and acceptance lines there. The R5 sentence states no exception, and R8 points to the R5 usage error.
- 2 runs (P01#2, P01#3): Puts the 'bad N wins' order in R7 (top option), with a cross-reference in R8 (one option only). The R5 sentence keeps its plain rule with no exception noted.

P01#1 moves the changed behaviour into a separate new requirement and moves the old lines there. P01#2 and P01#3 change R7 and R8 in place.

### R3 · P02 — major_drift · 2 / 1 of 3

- 1 runs (P02#1): Replaces each 'any file' with a concrete file. Each failure line gives the full stderr text, the exit code and a code. Adds the codes USAGE_INVALID and FILE_UNREADABLE to DES-errors.
- 2 runs (P02#2, P02#3): Replaces 'any file' with a concrete file and adds the codes USAGE and FILE_UNREADABLE. Most R7 failure lines give only the code and the exit code, with no exact stderr text. P02#3 also drops the exit code on a few lines.

P02#1 writes the exact message in every failure line. P02#2 and P02#3 drop the message from most R7 failure lines and keep only the code. The code names also differ (USAGE_INVALID against USAGE).

### R4 · P02 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P02#1): Three questions, one per message, each with two options and a recommended option with a reason: --top=3 form, invalid UTF-8, then the R5/R7 contradiction.
- 1 runs (P02#2): Five questions, one per message, with two or three options and a recommended option each: order of errors, other hyphen arguments, error codes, size of N, invalid UTF-8.
- 1 runs (P02#3): Three questions, one per message, each with two options and a recommended option with a reason: error codes, --top=2 form, invalid UTF-8.

All three runs keep the permitted form. But they ask different sets of questions: 3, 5 and 3 questions on different topics. Only some runs ask about the order of the checks, the error codes, or the size of N.

## What to fix

1. Replace each "Given any file" with a concrete file content, and give the exact text of each error → moves R3 (checks with no guess).
2. Settle a very large N with an acceptance line, not only with a line in "Notes" → moves R9 (the implied behaviour).
3. Put the order of the checks in one place. Then a bad N with a second --top gives one result → moves R2 (one result for each command line).

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
