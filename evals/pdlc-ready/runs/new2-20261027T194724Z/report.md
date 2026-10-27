# Vet Report: pdlc:ready

**Skill:** `pdlc:ready` · version `b1f078b709d3`
**Suite:** `evals/pdlc-ready/suite.json` · `82a346c92ed1`
**Run:** `new2-20261027T194724Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

SKILL.md changed since this suite was written; the rubric may be stale. `/vet pdlc:ready --regen` rebuilds it.

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 82.2 | Weighted share of the rubric met across all runs |
| Stability | 53.6 | How little the output changed between runs |
| **Overall** | **66.4 (D)** | √(quality × stability) |

Per-run quality: min 70.5 · median 82.9 · max 93.2

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 82.2 | 50.9 | 64.7 (D) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

VERDICT-TO-WRITE

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 The user can go straight to the plan: at the end, IN-0001 (… | outcome | 3 | 100% | 75 · minor_drift | 83.4% | - |
| R2 After the run, the specs give one result for each command l… | outcome | 3 | 91.7% | 0 · contradictory | 50% | - |
| R3 A test writer can write each check of the intent with no gu… | outcome | 3 | 66.7% | 25 · major_drift | 33.3% | - |
| R4 The run asks the user only in the permitted form. Each mess… | structure | 2 | 100% | 80 · minor_drift | 66.7% | 60 · minor_drift |
| R5 Each acceptance line and sentence that the run writes in a … | structure | 1 | 66.7% | 60 · minor_drift | 33.3% | 60 · minor_drift |
| R6 The intent keeps a full record of this stage. The record is… | structure | 2 | 83.3% | 60 · minor_drift | 66.7% | 60 · minor_drift |
| R7 The run ends in a commit on main with the subject `Ready IN… | structure | 2 | 100% | 95 · equivalent | 100% | 90 · equivalent |
| R8 The final reply gives the result first, then what changed. … | structure | 2 | 58.3% | 60 · minor_drift | 33.3% | 60 · minor_drift |
| R9 The run examines the behaviour that the intent implies but … | behavior | 2 | 50% | 60 · minor_drift | 33.3% | - |
| R10 When the run changes what a requirement does, no spec text … | behavior | 2 | 91.7% | 25 · major_drift | 33.3% | - |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 defaults | typical: defaults, no intent named | 82.6 | 51.1 | 3/3 |
| P02 IN-0001 | interactive: intent named by ID, no defaults | 81.8 | 50.7 | 3/3 |

---

## Where it falls short

### R9 The run examines the behaviour that the intent implies but does not state. The handoff ho… — met in 50% of runs

met 0 · partial 6 · missed 0

> how many digits can N have? → any number, so a very large N prints all words (assumed) — P01#1
> R7: can N be very large? → yes, any run of digits with a value of at least 1 is valid — P01#2

### R8 The final reply gives the result first, then what changed. The reply says that `/pdlc:cha… — met in 58.3% of runs

met 1 · partial 5 · missed 0

> R7 has new lines for N equal to the number of distinct words — P01#1
> R7 has new lines for a very large N — P01#2

### R3 A test writer can write each check of the intent with no guess. Each acceptance line has … — met in 66.7% of runs

met 2 · partial 4 · missed 0

> when the user runs `wordfreq --top abc FILE`, then the result is the `--top` error (`TOP_INVALID`). — P01#2
> then standard error is `error: cannot read missing.txt` and the exit code is 2. This is the error of R6 (file cannot be read). — P01#3

### R5 Each acceptance line and sentence that the run writes in a spec keeps the pdlc form. — met in 66.7% of runs

met 3 · partial 2 · missed 1

> then the error is `USAGE_INVALID` and the exit code is 2. Standard error is `usage: wordfreq FILE` and standard output is empty. — P02#1
> then the error is `USAGE` and the exit code is 2. Standard error is `usage: wordfreq FILE` and standard output is empty. — P02#2

## Where it varies

### R2 · P01 — contradictory · 1 / 1 / 1 of 3

- 1 runs (P01#1): Fault order in R7: --top twice first, then bad N, then file count; `--top 0` with no FILE gives TOP_INVALID, but `--top 0 --top 2 FILE` gives the usage line; Notes line records the order.
- 1 runs (P01#2): New R9 (order of the checks): bad --top value first, then usage (file count or --top twice), then read error; both conflict cases give the --top error, with acceptance lines and Notes.
- 1 runs (P01#3): Order inline in R5/R7/R8 sentences: bad N first, then --top twice, then file count; both conflict cases (`--top abc` no file, `--top 0 --top 2 FILE`) give the --top error, with two Notes lines.

For `wordfreq --top 0 --top 2 FILE`, P01#1 gives the usage line, and P01#2 and P01#3 give the --top error. These outcomes are incompatible. P01#2 also puts the order in a new requirement, and P01#3 puts it in the existing sentences.

### R2 · P02 — contradictory · 2 / 1 of 3

- 2 runs (P02#1, P02#3): Each --top value is checked first, so a bad N with no FILE and a bad N with a second --top both give the TOP_INVALID error; acceptance lines and a Notes line record the order.
- 1 runs (P02#2): Order is repeated --top (R8) first, then N, then files: a bad N with no FILE gives TOP_INVALID, but `--top 0 --top 2 FILE` gives the USAGE line.

P02#1 and P02#3 give the --top error for a bad N together with a second --top. P02#2 puts the R8 (one --top only) check first, so `wordfreq --top 0 --top 2 FILE` gives the usage line. The two outcomes are incompatible.

### R3 · P01 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P01#1): Every line uses a concrete file and the full exact stderr text plus exit code; every failure line names a code; DES-errors gains USAGE and FILE_UNREADABLE.
- 1 runs (P01#2): Concrete files and codes on every failure line (USAGE_INVALID, FILE_UNREADABLE added), but most R7 failure lines say 'the result is the `--top` error' in place of the exact text.
- 1 runs (P01#3): Concrete files and full exact text on every line; DES-errors gains only USAGE_INVALID; the missing.txt read-error line names no code and refers to R6 instead.

All runs replace 'any file' with a concrete file. P01#2 keeps a shorthand reference in the 'then' of most lines. P01#3 leaves the read-error line with no code and adds no FILE_UNREADABLE row. P01#1 fixes all three problems.

### R10 · P01 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P01#1): Central numbered fault-order list in R7; R5 and R8 sentences point to R7 for the order; no was/now note for the R5 sentence behaviour, only for its title.
- 1 runs (P01#2): Moves the order to a new R9 and moves the missing.txt lines into it; R5, R7 and R8 sentences point to R9; was/now Notes lines for R5 and R7.
- 1 runs (P01#3): States the exception inline: R5 and R8 sentences say a bad --top value gives TOP_INVALID instead; R7 says N is checked before R5 and R8; was/now Notes line for R5.

The runs keep the specs consistent in three different ways: a central list in R7 with cross-references, a new requirement R9, or inline exceptions in R5 and R8. The was/now notes also differ.

### R3 · P02 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P02#1): Adds USAGE_INVALID and FILE_UNREADABLE and gives the exact stderr text in each line, but R7 lines still say "Given any file".
- 1 runs (P02#2): Adds only USAGE; unreadable-file lines name no code; most R7 lines give the code but no exact stderr text; "Given any file" stays.
- 1 runs (P02#3): Replaces "Given any file" with a concrete file content, gives the exact text plus the code in each line, and adds USAGE and FILE_UNREADABLE.

The runs fix different subsets of the three problems. Only P02#3 replaces "any file". P02#2 drops the exact text from most failure lines and never adds a code for the unreadable file.

### R10 · P02 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P02#1): Changes the plus sign and the check order, and fixes R7, R8 and Notes, but the R5 sentence does not state that a bad N comes before the usage line.
- 1 runs (P02#2): Changes the order to put R8 first, and updates R5, R7, R8 and Notes consistently; the plus sign stays an error.
- 1 runs (P02#3): Changes the plus sign and puts a bad N first, and updates R5, R7, R8 and Notes consistently, with the old lines removed.

P02#1 leaves the R5 (usage line) sentence without the new exception, while the others update every place. The runs also change different behaviours.

## What to fix

FIX-TO-WRITE

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
