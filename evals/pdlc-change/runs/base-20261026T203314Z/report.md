# Vet Report: pdlc:change

**Skill:** `pdlc:change` · version `c50b050e9e1b`
**Suite:** `evals/pdlc-change/suite.json` · `1715fd2392de`
**Run:** `base-20261026T203314Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 96.4 | Weighted share of the rubric met across all runs |
| Stability | 65.4 | How little the output changed between runs |
| **Overall** | **79.4 (C)** | √(quality × stability) |

Per-run quality: min 91.3 · median 95.7 · max 100

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 96.4 | 67.8 | 80.8 (B) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The old change skill plans the right single change and copies its requirements exactly. R2 (one change for each spec) passes in each run. R3 (an exact copy of each requirement) and R5 (only the permitted files) also pass in each run, and their output is identical between runs.

The biggest issue is the order of the steps and the decisions that the old change skill records. Some runs put requirement R7 (top N words) before requirement R5 (usage line), and the runs disagree about the README line (R6). Each run records a different set of `(assumed)` decisions (R10). One wave of 3 runs per prompt is a small sample, so the stability score is rough.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 The change spec has the path, the header, and the sections … | structure | 2 | 100% | 80 · minor_drift | 100% | 60 · minor_drift |
| R2 The user gets one change for each spec of IN-0001 (the --to… | outcome | 3 | 100% | 90 · equivalent | 100% | - |
| R3 The "Requirements" section copies each requirement of the c… | behavior | 2 | 100% | 100 · identical | 100% | - |
| R4 A test writer who cannot see the code can write each check … | outcome | 3 | 100% | 60 · minor_drift | 66.7% | - |
| R5 "Files" and "Check files" list only what this job change is… | behavior | 2 | 100% | 100 · identical | 100% | - |
| R6 The "Steps" section has one step for each requirement and a… | structure | 2 | 66.7% | 12.5 · contradictory | 50% | 25 · major_drift |
| R7 The intent file lists the changes and holds a new handoff f… | structure | 2 | 100% | 60 · minor_drift | 83.4% | 60 · minor_drift |
| R8 The run leaves one Plan commit on main and changes nothing … | structure | 2 | 91.7% | 100 · identical | 100% | 60 · minor_drift |
| R9 The last message tells the user where the work stands and w… | outcome | 3 | 100% | 60 · minor_drift | 66.7% | - |
| R10 Each decision that the run makes without an instruction is … | behavior | 2 | 100% | 12.5 · contradictory | 50% | - |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 defaults | typical | 94.2 | 63.9 | 3/3 |
| P02 IN-0001 | named intent, interactive | 98.6 | 71.7 | 3/3 |

---

## Where it falls short

### R6 The "Steps" section has one step for each requirement and a last step for the README, and… — met in 66.7% of runs

met 2 · partial 4 · missed 0

> ### Step 1 · Print only N words · [ ] - Requirement: JOB-report-word-frequencies.R7 — P01#1
> The line "Each line has a word, a space, and the count." is correct for the output with `--top`. — P01#2

## Where it varies

### R6 · P01 — contradictory · 1 / 1 / 1 of 3

- 1 runs (P01#1): Steps in order R7, R5, R8, then README; Done when adds that earlier checks still pass; the README step says the intent's linked line 'Each line has a word...' must change; Manual checks none
- 1 runs (P01#2): Steps in number order R5, R7, R8, then README; Done when is only 'the check passes'; the README step says the linked line is still correct with --top; Manual checks none
- 1 runs (P01#3): Steps in order R7, R5, R8, then README (marked assumed); Check is a test_..._R7_… name in the group; the README step says the linked line still holds and adds text next to it, plus an extra error-message bullet; Manual …

P01#2 uses number order, but P01#1 and P01#3 put R7 before R5. On the README line that the intent links to R7, P01#1 says the line must change, while P01#2 and P01#3 say it still holds, so the runs reach opposite conclusions.

### R10 · P01 — contradictory · 1 / 1 / 1 of 3

- 1 runs (P01#1): Two Interface decisions marked (assumed): the --top value parsing and the error order; both are listed in Decided on defaults and Notes in the form requirement: question → answer (assumed)
- 1 runs (P01#2): No (assumed) marker; Decided on defaults says none; error precedence is left in Open and not decided
- 1 runs (P01#3): One decision, the step order, marked (assumed) in the Progress log and listed in Decided on defaults and Notes under the change ID, not a requirement; the --top parsing rule has no marker

Each run records a different set of default decisions. P01#1 decides the error precedence as assumed, but P01#2 leaves that same question open and says it made no decision. P01#3 instead records only the step order. All three runs ask no question.

### R6 · P02 — major_drift · 2 / 1 of 3

- 2 runs (P02#1, P02#2): Steps R5, R7, R8 in number order, then a README step. Check names the class JOB_report_word_frequencies_RN in the check file. Done when is 'the class checks pass'. The README Done when covers --top, the line in the Note…
- 1 runs (P02#3): Steps are in the order R7, R5, R8 (R7 first for the option parsing), then a README step. Check names test_..._RN_... in the class. Done when is a 'unittest discover -k' command. The README conditions are similar. Manual…

Runs 1 and 2 put the steps in number order with class-based checks. Run 3 builds R7 first, out of number order, and uses a unittest -k command as the Done when, so the structure of the steps differs materially.

### R10 · P02 — major_drift · 2 / 1 of 3

- 2 runs (P02#1, P02#3): Makes no decision on defaults. The spec has no (assumed) markers, Decided on defaults says 'none', and the error-precedence gap stays open. Asks no question
- 1 runs (P02#2): Decides three argument-parsing rules (exact --top match, other arguments count as FILE, usage error before the check of N), each with a plain (assumed) marker in the Interface. Lists them in Decided on defaults in the f…

Run 2 makes and marks three default decisions, one of which settles the error-precedence question. Runs 1 and 3 make no decision and leave that question open, so the runs differ materially in their approach to unstated choices.

### R6 · cross — major_drift · 2 / 1 / 1 of 4

- 1 runs (P01#1): Steps in the order R7, R5, R8, then README. Check reads 'the group JOB_..._RN'. Each Done when also says the earlier steps' checks still pass. README step names R5, R7 and R8 and has four conditions. Manual checks: none.
- 2 runs (P01#2, P02#1): Steps in number order R5, R7, R8, then README. Check reads 'the class JOB_..._RN'. Done when is only 'the check(s) pass'. README step names R7 and has four or five conditions (P02#1 puts the README-line condition in its…
- 1 runs (P02#2): Steps in number order R5, R7, R8, then README. Check starts with the bare underscored ID. Done when repeats the ID. README step names R7 and R8 and has five specific conditions, including the explicit run command, but n…

P01#1 puts the steps in a different order (R7 before R5) and adds a regression clause to each Done when. The other three runs follow number order with a plain pass condition. The Check line form, the README step's requirement list and its set of conditions also differ between runs.

## What to fix

1. "Steps": say "one step for each requirement, in number order" and not "usually" → moves R6 (the steps and the README step).
2. "Interface": name the decisions that the run must settle, for example the order of the errors, and mark each one `(assumed)` → moves R10 (each decision visible to the user).
3. "Steps", the README step: tell the run to read the README line that the intent Notes link to. Also tell the run to say whether that line changes → moves R6 (the steps and the README step).

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
