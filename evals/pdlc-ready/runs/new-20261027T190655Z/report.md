# Vet Report: pdlc:ready

**Skill:** `pdlc:ready` · version `43be5042baed`
**Suite:** `evals/pdlc-ready/suite.json` · `82a346c92ed1`
**Run:** `new-20261027T190655Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

SKILL.md changed since this suite was written; the rubric may be stale. `/vet pdlc:ready --regen` rebuilds it.

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 77.3 | Weighted share of the rubric met across all runs |
| Stability | 52.8 | How little the output changed between runs |
| **Overall** | **63.9 (D)** | √(quality × stability) |

Per-run quality: min 70.5 · median 75 · max 90.9

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 77.3 | 50 | 62.2 (D) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The first declarative version of ready (0.4.0, commit 887d6ce) does the work about as well as the old one. Overall is 63.9 against 65.9, in the range of the noise of the eval. `compare_vet.py` shows NO REGRESSION. R1 (the plan can start) and R7 (the commit) stay at 100%.

R2 (one result for each command line) falls from 91.7% to 75%. Three runs give the old usage line for a bad N, but the intent gives the --top error for each bad N. The old ready told the run to recommend the plain reading of the words of the intent. The new ready only pointed to "Spec patches", which is about patches, not about the recommended answer. The next commit adds the rule back, and a new eval measures it.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 The user can go straight to the plan: at the end, IN-0001 (… | outcome | 3 | 100% | 95 · equivalent | 100% | - |
| R2 After the run, the specs give one result for each command l… | outcome | 3 | 75% | 0 · contradictory | 50% | - |
| R3 A test writer can write each check of the intent with no gu… | outcome | 3 | 66.7% | 25 · major_drift | 50% | - |
| R4 The run asks the user only in the permitted form. Each mess… | structure | 2 | 100% | 75 · minor_drift | 100% | 60 · minor_drift |
| R5 Each acceptance line and sentence that the run writes in a … | structure | 1 | 58.3% | 60 · minor_drift | 50% | 60 · minor_drift |
| R6 The intent keeps a full record of this stage. The record is… | structure | 2 | 75% | 60 · minor_drift | 66.7% | 60 · minor_drift |
| R7 The run ends in a commit on main with the subject `Ready IN… | structure | 2 | 100% | 90 · equivalent | 100% | 90 · equivalent |
| R8 The final reply gives the result first, then what changed. … | structure | 2 | 66.7% | 60 · minor_drift | 50% | 60 · minor_drift |
| R9 The run examines the behaviour that the intent implies but … | behavior | 2 | 50% | 30 · contradictory | 83.4% | - |
| R10 When the run changes what a requirement does, no spec text … | behavior | 2 | 66.7% | 25 · major_drift | 33.3% | - |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 defaults | typical: defaults, no intent named | 81.8 | 48 | 3/3 |
| P02 IN-0001 | interactive: intent named by ID, no defaults | 72.7 | 52 | 3/3 |

---

## Where it falls short

### R9 The run examines the behaviour that the intent implies but does not state. The handoff ho… — met in 50% of runs

met 0 · partial 6 · missed 0

> +- Lines for each bad form of N, for the size of N, and for N next to the file count. — P01#1
> +Ready added lines for these inputs: — P01#2

### R5 Each acceptance line and sentence that the run writes in a spec keeps the pdlc form. — met in 58.3% of runs

met 1 · partial 5 · missed 0

> The exit code is 2 (error code `USAGE_INVALID`). — P01#2
> If the number of files is not one, the error is `USAGE_INVALID`. — P01#3

### R3 A test writer can write each check of the intent with no guess. Each acceptance line has … — met in 66.7% of runs

met 2 · partial 4 · missed 0

> when the user runs `wordfreq --top 00 FILE`, then the error is `TOP_INVALID` and the exit code is 2. — P01#3
> Given no file `missing.txt`, when the user runs `wordfreq --top 2 missing.txt`, then standard error is `error: cannot read missing.txt`. Standard output is emp… — P02#1

### R8 The final reply gives the result first, then what changed. The reply says that `/pdlc:cha… — met in 66.7% of runs

met 2 · partial 4 · missed 0

> R7 now accepts `+3`, `03`, `3.0`, `1e2`, and ` 3`. — P01#1
> R5, R7, and R8 stay `ready`. — P01#3

### R10 When the run changes what a requirement does, no spec text still shows the old behaviour. — met in 66.7% of runs

met 2 · partial 4 · missed 0

> @@ -61,11 +61,15 @@ A file with no words gives no output, and the exit code is 0. — P01#2
> If the number of files is not one, the error is `USAGE_INVALID`. — P01#3

### R2 After the run, the specs give one result for each command line. This includes a bad N tog… — met in 75% of runs

met 3 · partial 3 · missed 0

> when the user runs `wordfreq --top 0 --top 2 FILE`, then standard error is `usage: wordfreq FILE` — P01#2
> Given the arguments `--top 0`, when the user runs `wordfreq --top 0`, then standard error is `usage: wordfreq FILE` — P02#2

### R6 The intent keeps a full record of this stage. The record is a new "Handoff" in the templa… — met in 75% of runs

met 3 · partial 3 · missed 0

> +- DES-errors: new codes `USAGE_INVALID` for a wrong number of files or a second --top, and `FILE_UNREADABLE` for a file that cannot be read — P01#3
> The user settled four open items. Ready added the missing acceptance lines, the error codes `USAGE_INVALID` and `FILE_UNREADABLE`, and the order of the checks. — P02#2

## Where it varies

### R2 · P01 — contradictory · 2 / 1 of 3

- 2 runs (P01#1, P01#3): Checks the --top value first: `--top 0` with no FILE and `--top 0 --top 2 FILE` both give TOP_INVALID, with acceptance lines and a check-order line in Notes.
- 1 runs (P01#2): Order is --top twice first, then bad N, then file count: a bad N with a wrong file count gives TOP_INVALID, but `--top 0 --top 2 FILE` gives the usage line (USAGE_INVALID).

Runs 1 and 3 give the --top error for `--top 0 --top 2 FILE`. Run 2 checks the second --top first and gives the usage line for the same command, so the outcomes are opposite.

### R9 · P01 — contradictory · 2 / 1 of 3

- 1 runs (P01#1): Reverses the digits-only guess so that +3, 3.0, 1e2 and ' 3' are valid. Adds very-large-N lines (20 digits, 5,000 nines, 1e999999999) and records the settlements in Notes, with no list of kinds.
- 2 runs (P01#2, P01#3): Keeps digits-only N, so ' 3' and a non-ASCII digit are errors. Adds a 20-digit N line, records the upper-limit decision in Notes, and has no list of kinds.

All runs add a very large N line, and none lists the kinds. But run 1 accepts ' 3', +3, 3.0 and 1e2, and runs 2 and 3 reject them, so the same implied inputs get opposite results.

### R2 · P02 — contradictory · 1 / 1 / 1 of 3

- 1 runs (P02#1): A bad N always wins: `--top 0` with no FILE, `--top 0 a.txt b.txt` and `--top 0 --top 2 FILE` all give TOP_INVALID, with acceptance lines and a Notes line.
- 1 runs (P02#2): The usage line wins (recommended, user took it): `--top 0` with no FILE and `--top 0 --top 2 FILE` give USAGE_INVALID.
- 1 runs (P02#3): Mixed order: a repeated --top gives USAGE first, then a bad N beats the file count, so `--top 0 a.txt b.txt` gives TOP_INVALID but `--top 0 --top 2 FILE` gives USAGE.

The runs settle the same conflict in opposite ways. P02#1 puts the --top error first, P02#2 puts the usage line first, and P02#3 splits the two cases, so `wordfreq --top 0 --top 2 FILE` gets incompatible results.

### R3 · P01 — major_drift · 2 / 1 of 3

- 2 runs (P01#1, P01#2): Every failure line has a concrete file, the exact stderr text, empty stdout, exit code 2 and an error code; DES-errors gets USAGE_INVALID and FILE_UNREADABLE.
- 1 runs (P01#3): Concrete files and codes on every failure line, and the new DES-errors rows. But most R7 (top N words) failure lines and one R8 (one --top only) line give only the code and exit code, with no exact stderr text.

Runs 1 and 2 write the exact message on each failure line. Run 3 drops the message from about a dozen lines and leaves only the code, which is a material difference.

### R10 · P01 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P01#1): Changes N validity and the check order. Updates the R5 (usage line) sentence with the exception, the R5 title, the R7 acceptance lines and the Notes lines, so no old behaviour stays.
- 1 runs (P01#2): Puts a double --top first. Updates the R5 and R8 (one --top only) sentences and the Notes, but the R5 title still says 'wrong number of arguments'.
- 1 runs (P01#3): Puts the --top values first. Retitles R5, and R8 states the exception, but the R5 sentence does not say that a bad N comes before the usage line.

The runs change different behaviours. Run 1 removes every old trace, while runs 2 and 3 each miss a different place: the R5 title in run 2 and the R5 sentence in run 3.

### R3 · P02 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P02#1): Concrete file in each line and exact text in each failure line, adds only USAGE_INVALID; the cannot-read lines name no code.
- 1 runs (P02#2): Concrete file and codes USAGE_INVALID plus FILE_UNREADABLE in every failure line, but 11 R7 lines still say 'the same TOP_INVALID error' with no exact text.
- 1 runs (P02#3): Fixes all three: concrete file, exact text in every failure line, codes USAGE plus FILE_UNREADABLE named in every failure line.

Each run fixes a different subset of the three problems. P02#1 leaves the cannot-read lines without a code, P02#2 keeps 'the same error' wording, and only P02#3 fixes everything, with a different code name (USAGE).

### R10 · P02 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P02#1): Makes R5 and R8 yield to TOP_INVALID; updates the R5 sentence and title, the R8 and R7 sentences, and adds Notes lines; no stale text.
- 1 runs (P02#2): Makes R7 yield to R5 and R8; updates the R5 sentence and title, the R7 and R8 sentences, and edits the existing Notes line on --top without a value.
- 1 runs (P02#3): Makes R5 yield to R7, with R8 first; updates the R5, R7 and R8 sentences, adds an order list and a was/now Notes line, but the R5 title still says 'wrong number of arguments'.

Each run changes a different requirement's behaviour and fixes a different set of places. P02#3 leaves the old R5 title, which P02#1 and P02#2 fix.

## What to fix

1. Constraints: the recommended answer is the plain reading of the words of the intent, for each value → moves R2 (one result for each command line). This fix is in the next commit.
2. Constraints: "Done" in the handoff and the "Notes" list the same decisions → moves R6 (the record of this stage).

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
