# Vet Report: pdlc:conventions

**Skill:** `pdlc:conventions` · version `658ac9e8061f`
**Suite:** `evals/pdlc-conventions/suite.json` · `970724430e93`
**Run:** `base-20261026T202910Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 96 | Weighted share of the rubric met across all runs |
| Stability | 61.2 | How little the output changed between runs |
| **Overall** | **76.6 (C)** | √(quality × stability) |

Per-run quality: min 90.5 · median 95.2 · max 100

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 96 | 64.8 | 78.9 (C) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The old conventions skill writes a clear rule, finds the right migration intents, and starts no work. R4 (a rule that needs no guess), R5 (exactly the needed migration intents) and R7 (no intent started, no code migrated) are the three outcome and safety items, and they pass in each run. The biggest issue is the check intent. Some runs add a separate intent to build the check, and some runs fold the check into the migration intent (R10, R9). The form of each new intent also drifts, mainly its Handoff section (R6). One wave of 3 runs per prompt is a small sample, so the stability score is rough.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 Before the run writes the convention, it names the subject … | structure | 2 | 83.3% | 60 · minor_drift | 100% | - |
| R2 With `defaults`, the run asks no question and takes its rec… | behavior | 2 | 100% | 60 · minor_drift | 66.7% | - |
| R3 The design spec has the form of the design template. A new … | structure | 2 | 100% | 90 · equivalent | 100% | 90 · equivalent |
| R4 The user gets a rule that a later stage can apply with no g… | outcome | 3 | 100% | 60 · minor_drift | 83.4% | - |
| R5 The user gets exactly one migration intent for each job or … | outcome | 3 | 100% | 90 · equivalent | 100% | - |
| R6 Each intent that the run adds is a file from the intent tem… | structure | 2 | 100% | 25 · major_drift | 33.3% | 25 · major_drift |
| R7 The run does not start the intents, and does not migrate an… | behavior | 3 | 100% | 90 · equivalent | 100% | - |
| R8 The run commits all its work on main, in one commit with th… | structure | 2 | 100% | 90 · equivalent | 100% | 90 · equivalent |
| R9 The closing message tells the user how many migration inten… | structure | 2 | 83.3% | 25 · major_drift | 66.7% | 25 · major_drift |
| R10 The design spec has requirements for the convention, with t… | structure | 2 | 83.3% | 30 · contradictory | 66.7% | 0 · contradictory |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 Change our errors convention, DES-errors. Each er… | typical | 95.2 | 61.9 | 3/3 |
| P02 defaults: set a convention for how numbers show i… | new convention with defaults, terse | 96.8 | 67.6 | 3/3 |

---

## Where it falls short

Every item met in at least 80% of runs.
## Where it varies

### R10 · P01 — contradictory · 1 / 1 / 1 of 3

- 1 runs (P01#1): One proposed requirement R1 with two Given lines, Intents IN-0001, IN-0002, and a separate intent to build the check
- 1 runs (P01#2): Two proposed requirements (R1 read error, R2 usage) that point to IN-0001; no separate check intent (assumed), the check is folded into the migration intent
- 1 runs (P01#3): One proposed requirement R1 with two Given lines that points to IN-0001; no separate check intent, the check is folded into the migration intent

P01#1 adds a separate intent to build the check. P01#2 and P01#3 decide outright not to add one and fold the check into the migration intent. Those are opposite choices. The requirement split also differs: one requirement or two.

### R10 · cross — contradictory · 2 / 1 / 1 of 4

- 1 runs (P01#1): One requirement, DES-errors.R1, status proposed, 'Intents: IN-0001, IN-0002', with a separate check intent IN-0001 apart from the migration intent
- 1 runs (P01#2): Two requirements, R1 and R2, status proposed, 'Intents: IN-0001'; explicitly adds no separate check intent (assumed), so the migration intent builds the checks
- 2 runs (P02#1, P02#2): Two requirements, R1 (no separator) and R2 (no padding), status proposed, 'Intents: IN-0001', with one dedicated check intent IN-0001 and no migration intents

For the same prompt, P01#1 adds a separate intent to build the check, while P01#2 explicitly decides against one and puts the checks in the migration intent. These are opposite choices. The P02 runs agree with each other and use a separate check intent.

### R6 · P01 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P01#1): Two intent files (IN-0001 check, IN-0002 migration) from the template, with 'none yet' in Changes and Handoff
- 1 runs (P01#2): One migration intent file whose Notes entries are wrapped in backticks and whose Handoff section is filled in (Time, Done, Decided, Look here, Next)
- 1 runs (P01#3): One migration intent file from the template, with plain Notes and a one-sentence Handoff placeholder

All three runs use the same header, a migration name that follows the rule, and a spec path in What and why. They differ in content: P01#1 writes two intent files, P01#2 fills a whole handoff block and wraps the notes in backticks, and P01#3 leaves a short handoff placeholder.

### R9 · P01 — major_drift · 2 / 1 of 3

- 1 runs (P01#1): Closing message says 2 intents were added and keeps the check intent IN-0001 apart from the migration intent IN-0002; says the user selects when each runs
- 2 runs (P01#2, P01#3): Closing message says 1 intent (the migration IN-0001, which also builds the check) was added, gives the reason CAP-word-counting needs none, and says the user chooses when it runs

P01#1 reports two intents, and one is a separate check intent. P01#2 and P01#3 report one migration intent that also builds the check. The counts and the content of the closing messages differ in substance.

### R6 · P02 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P02#1): Check intent IN-0001 has the spec path in What and why, Requirements lines with ': added', and Handoff 'none yet. Intake writes the first handoff'
- 1 runs (P02#2): Check intent IN-0001 has no spec path in What and why, Requirements lines without ': added', and a full Handoff headed 'conventions → user'
- 1 runs (P02#3): Check intent IN-0001 has no spec path in What and why, Requirements lines with ': added', and a full Handoff headed 'intake → ready'

All three runs use the same file name pattern and header line. The Handoff section is a placeholder in P02#1 and a full handoff in the other two, with different from-to labels. Only P02#1 puts the spec path in What and why.

### R9 · P02 — major_drift · 2 / 1 of 3

- 1 runs (P02#1): Gives 1 intent in total and 0 migration intents, names IN-0001 as the check, and says the user chooses when IN-0001 runs, with the intake command
- 2 runs (P02#2, P02#3): Gives 0 migration intents apart from check intent IN-0001 and says 'I did not start it', but does not say that the user selects when the intent runs

All runs name the spec and keep the check intent apart from 0 migration intents. Only P02#1 tells the user that they choose when the intent runs. P02#2 and P02#3 say only that the run did not start it.

### R6 · cross — major_drift · 1 / 1 / 1 / 1 of 4

- 1 runs (P01#1): Two inbox files: IN-0001 is a separate check intent and IN-0002 is 'Migrate JOB-report-word-frequencies to DES-errors'; correct header; What and why gives the spec path; Handoff left as '- none yet'
- 1 runs (P01#2): One inbox file, IN-0001 'Migrate JOB-report-word-frequencies to DES-errors', which also carries the checks; Notes lines wrapped in backticks; Handoff section filled with Done/Decided/Open/Look here/Don't redo/Next
- 1 runs (P02#1): One check intent, IN-0001 'Build the check for DES-number-format', with the template header and spec path; Requirements bullets end with ': added'; Handoff is a placeholder sentence ('none yet. Intake writes the first h…
- 1 runs (P02#2): One check intent, IN-0001 'Check the number format', with the template header and spec path; Handoff section filled with the full handoff structure

Every run uses the same intent template and header. For the same prompt, though, P01#1 writes two intent files and P01#2 writes one. The Handoff section is a placeholder in some runs and a full structured handoff in others, and P01#2 wraps its Notes in backticks.

### R9 · cross — major_drift · 1 / 1 / 1 / 1 of 4

- 1 runs (P01#1): Names DES-errors and says 'I added 2 intents' as a total, listing the check intent IN-0001 and the migration intent IN-0002 apart, but gives no explicit migration count; says it did not start them and that the user sele…
- 1 runs (P01#2): Names DES-errors and says '1 migration intent', IN-0001 with a description (it also builds the checks); says it did not start it and 'You select when it runs'
- 1 runs (P02#1): Names DES-number-format, says 1 intent in total (IN-0001, the check) and 0 migration intents with a reason; says the user chooses when IN-0001 runs and gives the intake command
- 1 runs (P02#2): Names DES-number-format, says 0 migration intents with a reason, and lists IN-0001 (the check) as not started; does not say that the user selects when it runs

Every run ends with a summary that names the spec, counts the intents and lists their IDs. The counting differs: P01#1 gives only a total, while the others give a migration count. P02#2 leaves out the statement that the user selects when each intent runs.

## What to fix

1. "3. Write the convention": say whether the check gets its own intent, or rides in the migration intent when there is one → moves R10 (requirements and one check intent) and R9 (the count in the closing message).
2. "4. Add the migration intents": say what a new intent holds in its Handoff section ("none yet") → moves R6 (the form of each new intent).
3. "4. Add the migration intents": say that "What and why" links to the design spec → moves R6 (the form of each new intent).

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
