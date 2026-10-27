# Vet Report: pdlc:change

**Skill:** `pdlc:change` · version `bfbce365a687`
**Suite:** `evals/pdlc-change/suite.json` · `1715fd2392de`
**Run:** `new-20261027T100530Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

SKILL.md changed since this suite was written; the rubric may be stale. `/vet pdlc:change --regen` rebuilds it.

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 91.3 | Weighted share of the rubric met across all runs |
| Stability | 55.6 | How little the output changed between runs |
| **Overall** | **71.2 (C)** | √(quality × stability) |

Per-run quality: min 84.8 · median 91.3 · max 95.7

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 91.3 | 57.4 | 72.4 (C) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The first declarative version of change (0.4.0, commit 887d6ce) plans the right single change and lists the right files: R2 and R5 pass in each run. Against the old version (0.3.0), overall falls from 79.4 to 71.2, and `compare_vet.py` shows REGRESSION. The cause is R4 (an Interface that a test writer can use alone): it falls from 100% to 66.7%. The new runs leave out details that the old runs gave, for example where `--top` can stand and the order of words with equal counts.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 The change spec has the path, the header, and the sections … | structure | 2 | 100% | 80 · minor_drift | 100% | 60 · minor_drift |
| R2 The user gets one change for each spec of IN-0001 (the --to… | outcome | 3 | 100% | 95 · equivalent | 100% | - |
| R3 The "Requirements" section copies each requirement of the c… | behavior | 2 | 91.7% | 62.5 · major_drift | 83.4% | - |
| R4 A test writer who cannot see the code can write each check … | outcome | 3 | 66.7% | 25 · major_drift | 33.3% | - |
| R5 "Files" and "Check files" list only what this job change is… | behavior | 2 | 100% | 100 · identical | 100% | - |
| R6 The "Steps" section has one step for each requirement and a… | structure | 2 | 66.7% | 0 · contradictory | 33.3% | 0 · contradictory |
| R7 The intent file lists the changes and holds a new handoff f… | structure | 2 | 100% | 60 · minor_drift | 66.7% | 60 · minor_drift |
| R8 The run leaves one Plan commit on main and changes nothing … | structure | 2 | 100% | 75 · minor_drift | 83.4% | 60 · minor_drift |
| R9 The last message tells the user where the work stands and w… | outcome | 3 | 100% | 60 · minor_drift | 83.4% | - |
| R10 Each decision that the run makes without an instruction is … | behavior | 2 | 91.7% | 12.5 · contradictory | 50% | - |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 defaults | typical | 89.9 | 49.3 | 3/3 |
| P02 IN-0001 | named intent, interactive | 92.8 | 65.4 | 3/3 |

---

## Where it falls short

### R4 A test writer who cannot see the code can write each check from the "Interface" section, … — met in 66.7% of runs

met 2 · partial 4 · missed 0

> in: `FILE` is a path to a UTF-8 file. `--top N` is optional, and can come once only. — P01#1
> Both give nothing on standard output and exit code 2. — P01#3

### R6 The "Steps" section has one step for each requirement and a last step for the README, and… — met in 66.7% of runs

met 2 · partial 4 · missed 0

> - JOB-report-word-frequencies.R7 · the README line "Each line has a word, a space, and the count." changes to cover `--top` · read the "Use" section of the REA… — P01#2
> ### Step 1 · Print only the N most common words · [ ] - Requirement: JOB-report-word-frequencies.R7 — P01#3

## Where it varies

### R6 · P01 — contradictory · 1 / 1 / 1 of 3

- 1 runs (P01#1): Steps R5, R7, R8 in number order with Check starting with the underscored ID; the README step names an R7 check that reads README.md; all four README conditions; Manual checks 'none'
- 1 runs (P01#2): Steps R5, R7, R8 in number order with Check text 'the checks in the group JOB_..._RN'; the README step Check is 'manual check'; Manual checks lists the README line item
- 1 runs (P01#3): Steps in the order R7, R5, R8 (not number order) with Check 'the checks in the class JOB_..._RN'; the README step says no check reads it; Manual checks 'None.'

The runs give incompatible answers for how the README is checked: an automated R7 check (P01#1), a manual check (P01#2), or no check at all (P01#3). Manual checks is 'none' in two runs and lists an item in P01#2. P01#3 also breaks the number order of the steps.

### R10 · P01 — contradictory · 1 / 1 / 1 of 3

- 1 runs (P01#1): No (assumed) markers; Decided on defaults is 'none' and Notes get no entry; the bad-N-plus-wrong-file-count case is left as an open item
- 1 runs (P01#2): Marks the short name 'top-option (assumed)' in the progress log, and lists it in Decided on defaults and in Notes in '<id>: <question> → <answer> (assumed)' form; the error-order question is left open
- 1 runs (P01#3): Marks an assumed error order (usage line, then TOP_INVALID, then file error) in Interface, and lists it in Decided on defaults and in Notes in the arrow form

P01#3 decides the error order on defaults, but P01#1 and P01#2 list that same question as open. P01#1 reports no decisions, and P01#2 reports a different decision (the short name).

### R6 · P02 — contradictory · 1 / 1 / 1 of 3

- 1 runs (P02#1): Steps in order R5, R7, R8, then README; the README step's Check is an automated readme check in the R7 group; Manual checks says none
- 1 runs (P02#2): Steps in order R7, R5, R8, then README; the README step's Check is 'manual check', and Manual checks lists a README item
- 1 runs (P02#3): Steps in order R7, R8, R5, then README; the README step's Check is 'none, no check reads it'; Manual checks says none

The step order differs in each run. The README is checked by an automated check in P02#1, by a manual check in P02#2, and by no check in P02#3, so Manual checks says none in two runs and lists an item in one.

### R6 · cross — contradictory · 2 / 1 / 1 of 4

- 2 runs (P01#1, P02#1): Steps 1-3 cover R5, R7, R8 in number order with underscored-ID checks. Step 4 (README) uses an automated R7 check that reads README.md, its Done when has all four conditions, and Manual checks says "none".
- 1 runs (P01#2): Steps 1-3 cover R5, R7, R8 in number order. Step 4 (README) has Check `manual check`, its Done when has the four conditions, and Manual checks lists a README item, not "none".
- 1 runs (P02#2): The steps come in the order R7, R5, R8, not number order. Step 4 (README) has Check `manual check` and a bulleted Done when with the four conditions. Manual checks lists a README item.

Two runs prove the README step with an automated check and write "none" in Manual checks. The other two make the README a manual check and list it under Manual checks, which is the opposite choice. P02#2 also orders the steps R7, R5, R8 and does not keep number order.

### R3 · P01 — major_drift · 2 / 1 of 3

- 1 runs (P01#1): Copies the three requirements and all 18 R7 lines, but rewrites the third R5 line into two sentences ('... FILE`. Standard output is empty ...') to shorten it
- 2 runs (P01#2, P01#3): Copies the three requirements and all 18 R7 lines verbatim, with the 27-word R5 line kept as it stands in the spec

P01#1 chose to edit an acceptance line of R5 (usage line), and P01#2 and P01#3 explicitly chose to copy it as it is. The headings, the R7 and R8 lines, and the absence of Status lines are the same in all three runs.

### R4 · P01 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P01#1): Command entry in __main__.py with inline in/out/errors (TOP_INVALID, usage line, cannot read, exit 2), plus untyped main(argv, stdout, stderr) in cli.py; a check can run the command or call main; seams none
- 1 runs (P01#2): Command entry and typed main entry, plus separate entries for TOP_INVALID (with its trigger condition, and the value is checked before the file is read) and for the two uncoded errors; a check can call either; seams non…
- 1 runs (P01#3): Intro says checks must drive the command in a new process; command entry with inline errors, typed main entry, plus an assumed error-order entry (usage line, then TOP_INVALID, then file error); seams none

All three runs give the command, its inputs, its output and the three errors with exit code 2, and all say there are no seams. P01#3 adds an assumed error order and a new-process rule that the other runs do not have. P01#2 splits the errors into their own entries and adds a trigger condition and a check order.

### R4 · P02 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P02#1): Command entry in __main__.py with inputs, the '<word> <count>' output with exit 0, all three error texts with exit 2, plus main() in cli.py; Test seams is 'none'
- 1 runs (P02#2): Command entry whose 'out' gives only streams and exit codes, not the '<word> <count>' line form; adds an assumed fault-precedence list that carries the usage and cannot-read texts; Test seams is 'None'
- 1 runs (P02#3): Command and main() entries marked existing, with full output and error texts; Test seams lists clock, randomness and vendors as none, and names main's stdout/stderr parameters as a seam

P02#2 drops the output line format and adds a new fault-order rule. P02#3 names main's stream arguments as a test seam, where P02#1 says none.

### R10 · P02 — major_drift · 2 / 1 of 3

- 2 runs (P02#1, P02#3): No (assumed) markers in the change spec; Decided on defaults says none; no question asked
- 1 runs (P02#2): One assumed decision (the fault precedence order) marked '(assumed)' in Interface, listed in Decided on defaults in the arrow form, and recorded in the intent Notes; no question asked

P02#2 makes an assumed decision and records it in three places. P02#1 and P02#3 make no such decision and say none.

## What to fix

1. Constraints, the Interface entries: say what "in", "out" and each error must give. "In" gives each form of input that a line uses. "Out" gives the full result with its order. Each error gives its exact text, where it shows, and its exit code → moves R4. This fix is in the next commit, and a new eval measures it.
2. Constraints, Steps: say "one step for each requirement, in number order" → moves R6.

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
