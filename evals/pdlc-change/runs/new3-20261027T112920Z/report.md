# Vet Report: pdlc:change

**Skill:** `pdlc:change` · version `b5dac5f52048`
**Suite:** `evals/pdlc-change/suite.json` · `1715fd2392de`
**Run:** `new3-20261027T112920Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

SKILL.md changed since this suite was written; the rubric may be stale. `/vet pdlc:change --regen` rebuilds it.

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 98.9 | Weighted share of the rubric met across all runs |
| Stability | 63.1 | How little the output changed between runs |
| **Overall** | **79 (C)** | √(quality × stability) |

Per-run quality: min 93.5 · median 100 · max 100

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 98.9 | 62.3 | 78.5 (C) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The third declarative version of change (0.4.0, commit 52c0ada) does the work as well as the old one, and as consistently within the noise of the eval. Against the first baseline, overall is 79.0 against 79.4. Against the second baseline, overall is 79.0 against 81.7. `compare_vet.py` shows NO REGRESSION for both. R6 (the steps) rises from 66.7% to 100%, because the skill now gives one form for the README step. The biggest issue left is the order of the errors when two apply to one input (R4 and R10). The old version drifts there too.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 The change spec has the path, the header, and the sections … | structure | 2 | 100% | 60 · minor_drift | 100% | 60 · minor_drift |
| R2 The user gets one change for each spec of IN-0001 (the --to… | outcome | 3 | 100% | 90 · equivalent | 100% | - |
| R3 The "Requirements" section copies each requirement of the c… | behavior | 2 | 100% | 100 · identical | 100% | - |
| R4 A test writer who cannot see the code can write each check … | outcome | 3 | 91.7% | 12.5 · contradictory | 33.3% | - |
| R5 "Files" and "Check files" list only what this job change is… | behavior | 2 | 100% | 100 · identical | 100% | - |
| R6 The "Steps" section has one step for each requirement and a… | structure | 2 | 100% | 60 · minor_drift | 66.7% | 60 · minor_drift |
| R7 The intent file lists the changes and holds a new handoff f… | structure | 2 | 100% | 60 · minor_drift | 66.7% | 60 · minor_drift |
| R8 The run leaves one Plan commit on main and changes nothing … | structure | 2 | 100% | 80 · minor_drift | 100% | 90 · equivalent |
| R9 The last message tells the user where the work stands and w… | outcome | 3 | 100% | 60 · minor_drift | 66.7% | - |
| R10 Each decision that the run makes without an instruction is … | behavior | 2 | 100% | 12.5 · contradictory | 33.3% | - |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 defaults | typical | 97.8 | 57.8 | 3/3 |
| P02 IN-0001 | named intent, interactive | 100 | 66.7 | 3/3 |

---

## Where it falls short

Every item met in at least 80% of runs.
## Where it varies

### R4 · P01 — contradictory · 1 / 1 / 1 of 3

- 1 runs (P01#1): Command entry first, main() as second entry with listed argv forms; error order (assumed) is repeated --top, then TOP_INVALID, then file count, then read; dash arguments are files (assumed)
- 1 runs (P01#2): Command entry first with the CLI forms and errors as Text/Where/When blocks, main() second; error order (assumed) is TOP_INVALID first, then usage (which includes repeated --top), then cannot-read
- 1 runs (P01#3): main() is the only top-level entry and the command is a sub-line; error order (assumed) is repeated --top, then the --top value, then file count, then the file

All runs give the same error texts and exit codes. P01#3 makes main() the top entry, and the others make the command the top entry. The assumed error order conflicts: P01#2 checks TOP_INVALID before a repeated --top, but P01#1 and P01#3 check a repeated --top first, so `--top 1 --top abc FILE` gets a different error.

### R10 · P01 — contradictory · 1 / 1 / 1 of 3

- 1 runs (P01#1): Two assumed decisions (error order with repeated --top first; dash arguments are files), marked in the Interface, the Notes and Decided on defaults, with (assumed) placed mid-answer
- 1 runs (P01#2): One assumed decision: TOP_INVALID, then usage, then cannot-read, marked in the Interface, the Notes and Decided on defaults
- 1 runs (P01#3): One assumed decision: repeated --top, then the --top value, then file count, then the file, marked in the Interface, the Notes and Decided on defaults

No run asks a question, and each run records its decisions in the same three places. P01#1 records two decisions, and the others record one. P01#2 gives the reverse answer to the same question: TOP_INVALID comes before a repeated --top, where P01#1 and P01#3 put the repeated --top first.

### R4 · P02 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P02#1): Short command entry `python3 -m wordfreq ARGUMENTS...` in __main__.py. The argv forms, the N rules, the outputs, and the three errors sit under `main` in cli.py. Main checks N before it reads FILE, and the usage-versus-…
- 1 runs (P02#2): Full command entry `python3 -m wordfreq [--top N] FILE` with the inputs, outputs, and the three error texts with exit code 2. `main` refers back to the command. N is checked before FILE, and there is no full precedence …
- 1 runs (P02#3): Full command entry, as in new2, plus an assumed four-level error order: a repeated --top gives the usage error, then a wrong file count gives the usage error, then TOP_INVALID, then cannot-read. `main` refers back to th…

All runs list the command and main with the error texts and exit code 2, and all give Test seams: none. P02#1 puts the details under main, not under the command. P02#3 adds an assumed error-precedence rule that the other two leave open, and that rule changes what a test writer would check.

### R10 · P02 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P02#1): The only assumed decision is the short name top-option. It is marked in the Progress log and listed in the handoff Decided on defaults, but not in the intent Notes
- 1 runs (P02#2): The run makes no assumed decision. Decided on defaults says 'none from this stage'
- 1 runs (P02#3): The run assumes the error precedence and marks it (assumed) in the Interface and the Progress log. It also records the decision in the intent Notes and in Decided on defaults

The runs make different decisions on their own: P02#1 assumes the short name, P02#2 assumes nothing, and P02#3 assumes an error order. Each run records its decision in different places.

## What to fix

1. Constraints, Interface: when two errors can apply to one input and the acceptance lines do not say which wins, the Interface gives one order, marks it `(assumed)`, and lists it in "Decided on defaults" → moves R4 and R10.
2. Better still: the ready stage settles that order before the change stage, so that the change stage has no choice to make.

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
