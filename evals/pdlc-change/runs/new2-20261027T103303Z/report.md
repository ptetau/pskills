# Vet Report: pdlc:change

**Skill:** `pdlc:change` · version `567200adcb83`
**Suite:** `evals/pdlc-change/suite.json` · `1715fd2392de`
**Run:** `new2-20261027T103303Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

SKILL.md changed since this suite was written; the rubric may be stale. `/vet pdlc:change --regen` rebuilds it.

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 96.4 | Weighted share of the rubric met across all runs |
| Stability | 55.4 | How little the output changed between runs |
| **Overall** | **73.1 (C)** | √(quality × stability) |

Per-run quality: min 91.3 · median 95.7 · max 100

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 96.4 | 57.2 | 74.3 (C) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The fixed declarative change skill (0.4.0, commit 5324a17) does the work as well as the old one. Quality is 96.4 in both, and R4 (a usable Interface) is back to 100%. But `compare_vet.py` still shows REGRESSION, because stability falls from 65.4 to 55.4 and overall falls from 79.4 to 73.1. The drift is in items where the old version also drifted: the order of the error checks (R4, R10) and the README step (R6). The other drifted items are the order of "Relies on" (R1) and one run that shortened a copied line (R3). A second run of the old version measures how much of this fall is noise.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 The change spec has the path, the header, and the sections … | structure | 2 | 100% | 60 · minor_drift | 100% | 60 · minor_drift |
| R2 The user gets one change for each spec of IN-0001 (the --to… | outcome | 3 | 100% | 95 · equivalent | 100% | - |
| R3 The "Requirements" section copies each requirement of the c… | behavior | 2 | 91.7% | 62.5 · major_drift | 83.4% | - |
| R4 A test writer who cannot see the code can write each check … | outcome | 3 | 100% | 30 · contradictory | 50% | - |
| R5 "Files" and "Check files" list only what this job change is… | behavior | 2 | 100% | 100 · identical | 100% | - |
| R6 The "Steps" section has one step for each requirement and a… | structure | 2 | 75% | 25 · major_drift | 33.3% | 0 · contradictory |
| R7 The intent file lists the changes and holds a new handoff f… | structure | 2 | 100% | 60 · minor_drift | 83.4% | 60 · minor_drift |
| R8 The run leaves one Plan commit on main and changes nothing … | structure | 2 | 91.7% | 60 · minor_drift | 83.4% | 60 · minor_drift |
| R9 The last message tells the user where the work stands and w… | outcome | 3 | 100% | 60 · minor_drift | 100% | - |
| R10 Each decision that the run makes without an instruction is … | behavior | 2 | 100% | 12.5 · contradictory | 50% | - |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 defaults | typical | 95.7 | 56.1 | 3/3 |
| P02 IN-0001 | named intent, interactive | 97.1 | 58.3 | 3/3 |

---

## Where it falls short

### R6 The "Steps" section has one step for each requirement and a last step for the README, and… — met in 75% of runs

met 3 · partial 3 · missed 0

> Step order (assumed): R7 (print N words) first — P01#1
> - JOB-report-word-frequencies.R7 · The README describes the option `--top N` · Read `README.md` against "Done when" of Step 4. — P01#2

## Where it varies

### R4 · P01 — contradictory · 1 / 1 / 1 of 3

- 1 runs (P01#1): Command entry in __main__.py plus main() in cli.py with all three error texts and exit 2; says only that N is checked before FILE is read, and leaves the usage-vs-TOP_INVALID order open
- 1 runs (P01#2): Command entry plus main(); gives an explicit assumed error order: a double --top gives usage, then TOP_INVALID, then usage for the file count, then the read error. So '--top 0' with no file gives TOP_INVALID
- 1 runs (P01#3): Command entry plus main(), with a separate errors list; gives an assumed order in which the usage error comes before TOP_INVALID, which comes before the read error. So '--top 0' with no file gives the usage line

All runs list the same command, main(), error texts, exit codes, and 'Test seams: none'. But for a call such as '--top 0' with no FILE, run 2 specifies TOP_INVALID, run 3 specifies the usage line, and run 1 leaves the case open.

### R10 · P01 — contradictory · 1 / 1 / 1 of 3

- 1 runs (P01#1): Two assumed decisions, both recorded under the 'CH-0001:' prefix: step order R7 first, and no check for the README. The error-precedence question is left open
- 1 runs (P01#2): Three assumed decisions, each recorded under a requirement: an error order that puts TOP_INVALID before the file-count usage, the next argument is always the --top value, and three or more --top give usage
- 1 runs (P01#3): One assumed decision, recorded under R7: the usage error comes before TOP_INVALID

No run asks a question, and each run marks its decisions with '(assumed)' in Notes and in Decided on defaults. But the decision sets differ. Runs 2 and 3 give opposite answers on error precedence, and run 1 leaves that question open.

### R6 · cross — contradictory · 1 / 1 / 1 / 1 of 4

- 1 runs (P01#1): Steps run R7, R5, R8, then README, so they are not in number order. Each Check names the underscored class. The README step has Check 'none (assumed)'. Manual checks says 'none'.
- 1 runs (P01#2): Steps run R5, R7, R8, then README. Each Check names the underscored test-method prefix. The README step has Check 'manual check', and Manual checks lists a README item, not 'none'.
- 1 runs (P02#1): Steps run R5, R7, R8, then README. Each Check names the underscored group and method prefix. The README step has Check 'none'. Manual checks says 'None.'
- 1 runs (P02#2): Steps run R5, R7, R8, then README. Each Check names the underscored method glob in its class. The README step has an automated check that reads README.md. Manual checks says 'none'.

The runs make three different choices for the README step: no check, a manual check that is also listed under 'Manual checks', and an automated check that reads README.md. The P01#2 manual-check choice contradicts the 'none' that the other runs put in 'Manual checks'. P01#1 also puts the steps in a different order (R7 first).

### R6 · P01 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P01#1): Steps in order R7, R5, R8 (assumed), then the README step with 'Check: none (assumed)'. Checks name the class JOB_report_word_frequencies_RN. Done when adds 'earlier checks still pass'. Manual checks: none
- 1 runs (P01#2): Steps in order R5, R7, R8, then the README step with 'Check: manual check'. Checks name test_JOB_report_word_frequencies_RN_... methods. Manual checks lists the README item
- 1 runs (P01#3): Steps in order R5, R7, R8, then the README step with 'Check: none' (the spec review reads it). Checks name the class JOB_..._RN with one check per line. Manual checks: none

Run 1 puts the steps out of number order. Run 2 makes the README a manual check and lists it under 'Manual checks', where runs 1 and 3 write 'none'. The Check and Done when wording also differs in each run.

### R3 · P02 — major_drift · 2 / 1 of 3

- 2 runs (P02#2, P02#3): Copies the three requirements and all acceptance lines exactly as in the spec, with no Status line or description, and keeps the 27-word R5 line as it is.
- 1 runs (P02#1): Copies the three requirements and the 18 R7 lines, but splits the third R5 acceptance line into two sentences, so its words differ from the spec.

P02#1 rewrote the third R5 line to shorten it. P02#2 and P02#3 explicitly kept the copy exact, so one run's copy differs from the spec.

### R6 · P02 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P02#1): Three requirement steps whose Check names the underscored group, plus a README step with 'Check: none' and all four Done-when conditions, which give the unittest discover command; Manual checks none.
- 1 runs (P02#2): Three requirement steps whose Check starts with test_JOB_..._R*, plus a README step that plans a test_..._R7_readme_* check that reads README.md, with all four conditions; Manual checks none.
- 1 runs (P02#3): Three requirement steps with group checks and short Done-when lines, plus a README step with 'Check: none' whose run-checks condition names only the config 'all' command, not the unittest command; Manual checks none.

P02#2 adds an automated README check, but the other runs say that no check reads the README. P02#3 leaves out the explicit unittest command. The Check lines also start in different forms.

### R10 · P02 — major_drift · 2 / 1 of 3

- 2 runs (P02#1, P02#3): No (assumed) markers anywhere, and Decided on defaults says 'none'; the short name top-option is not treated as a decision.
- 1 runs (P02#2): Marks the short name top-option as (assumed) in the change spec's Progress log, the intent Notes, and Decided on defaults in the form '<item>: <question> → <answer> (assumed)'.

P02#2 records the short name as an assumed decision in three places. P02#1 and P02#3 record no decision and no marker, so the item is present in one run and absent in two.

## What to fix

1. Constraints, Requirements: "copy each acceptance line word for word, also a long one" → moves R3 (an exact copy of each requirement).
2. Constraints, Steps: "one step for each requirement, in number order", and one form for the README step → moves R6 (the steps and the README step).
3. Constraints, Relies on: give the entries in one order (capabilities, then the design specs in name order) → moves R1 (the template sections and "Relies on").

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
