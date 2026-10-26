# Vet Report: pdlc:trace

**Skill:** `pdlc:trace` · version `790f22afc524`
**Suite:** `evals/pdlc-trace/suite.json` · `0d06ef760af0`
**Run:** `base-20261026T203041Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 86.7 | Weighted share of the rubric met across all runs |
| Stability | 58.5 | How little the output changed between runs |
| **Overall** | **71.2 (C)** | √(quality × stability) |

Per-run quality: min 78.6 · median 86.4 · max 96.9

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 86.7 | 60.7 | 72.5 (C) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The old trace skill answers the question and changes nothing: R1 (plain answer) and R2 (true facts) pass in 11 of 12 verdicts, and R9 (no change) passes in each run. The biggest issue is how it cites its sources (R6): each run uses a different form, and most runs give no path for the intent. Bare short IDs such as "R7" also stay in the prose (R10). One wave of 3 runs per prompt is a small sample, so the stability score is rough.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 The first lines of the reply answer the question that the u… | outcome | 3 | 91.7% | 75 · minor_drift | 83.4% | - |
| R2 Each fact in the answer is true for the project, and the an… | outcome | 3 | 91.7% | 60 · minor_drift | 83.4% | - |
| R3 For a question about code with trace trailers, the reply fo… | structure | 2 | 66.7% | 60 · minor_drift | 66.7% | - |
| R4 For a question about an intent, the reply gives the require… | structure | 2 | 100% | 60 · minor_drift | 66.7% | - |
| R5 For a question about a requirement, the reply gives the req… | structure | 2 | - | - | - | - |
| R6 Each link in the answer names its source, so that the user … | structure | 2 | 66.7% | 25 · major_drift | 33.3% | 25 · major_drift |
| R7 When the trace reaches a change, the reply links to the fil… | structure | 1 | 100% | 60 · minor_drift | 50% | 60 · minor_drift |
| R8 The reply tells the user about each missing link that the t… | structure | 2 | 100% | 25 · major_drift | 33.3% | - |
| R9 The run changes nothing in the project. | behavior | 2 | 100% | 95 · equivalent | 100% | - |
| R10 Each ID in the prose of the reply comes with a short descri… | behavior | 1 | 50% | 60 · minor_drift | 66.7% | - |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 Why does line 26 of wordfreq/cli.py exist? | typical | 79.8 | 59.3 | 3/3 |
| P02 defaults. What did IN-0001 (the --top option) cha… | reverse direction (from an intent to code), with defaults | 92.7 | 61.9 | 3/3 |

---

## Where it falls short

### R10 Each ID in the prose of the reply comes with a short description. — met in 50% of runs

met 0 · partial 6 · missed 0

> The table in `proposal.md` says 19 checks for R7 — P01#1
> Line 26 serves R7. — P01#2

### R3 For a question about code with trace trailers, the reply follows the chain from the code … — met in 66.7% of runs

met 1 · partial 2 · missed 0

> R5 (usage line) and R8 (one `--top` option only) are other lines of the same commit. — P01#2
> R5 (usage line) covers lines 20 to 22. R8 (one `--top` only) covers lines 13 to 15. — P01#3

### R6 Each link in the answer names its source, so that the user can open it. — met in 66.7% of runs

met 2 · partial 4 · missed 0

> Intent: IN-0001 (wordfreq top option) is `in review` on the branch. — P01#1
> IN-0002 (wordfreq top huge number) records it. — P01#2

## Where it varies

### R6 · P01 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P01#1): Gives the commit hash and subject, the requirement spec path, the change.md path, and the test file with its class. It gives no file path for IN-0001 (wordfreq top option) or IN-0002 (wordfreq top huge number).
- 1 runs (P01#2): Gives plain backtick paths for the requirement spec, DES-errors.md, the IN-0001 inbox file, change.md, and the test file with its class. IN-0002 has no path.
- 1 runs (P01#3): Gives clickable markdown links for every source: requirement, intent, change, proposal, test file, review result, and the IN-0002 file. It also names each check one by one.

The runs cite their sources in different ways. P01#1 leaves the intent with no path. P01#2 uses plain paths. P01#3 links every file and lists the checks by name, so the coverage and the format both differ.

### R6 · P02 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P02#1): Plain paths for the job spec, the change folder and the test file. The intent has no file path. The branch commits show a hash with a stage label in a table, not the full subjects.
- 1 runs (P02#2): Clickable Markdown links to change.md, the job spec, proposal.md and review.gif. The intent has no file path. The commits show a hash with a short parenthesized role, not the subjects.
- 1 runs (P02#3): Plain paths for every record, the intent file `pdlc/inbox/IN-0001-...` among them. Each commit has its hash and its subject. Each check has its class and its test file.

Only P02#3 gives the path of the intent file and the commit subjects with the hashes. P02#1 and P02#2 leave out the intent path and label the commits by stage. P02#2 also uses Markdown links where the other runs use plain paths. So source coverage differs materially.

### R8 · P02 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P02#1): Six numbered gaps: 19 vs 20 checks, no acceptance file, the 'Upgrade pdlc' commit with no trailers, IN-0002, invalid UTF-8 and non-ASCII digits. Ends by confirming that every IN-0001 commit and every requirement has its…
- 1 runs (P02#2): Three gaps: no acceptance file, 19 vs 20 checks, and the 'Upgrade pdlc' and 'Set up pdlc' commits with no trailers.
- 1 runs (P02#3): Three gaps: no acceptance file, 19 vs 20 checks, and older checks in test_cli.py with no requirement ID. It does not flag the 'Upgrade pdlc' commit with no trailers. A separate follow-up section gives IN-0002 and UTF-8.

All runs have a missing-links section with the acceptance gap and the gap in the count of checks. P02#3 does not flag the commit with no trailers that P02#1 and P02#2 report. P02#3 adds a gap that no other run gives (old checks with no requirement ID), and P02#1 adds several more gaps. So the reported gaps differ materially.

### R6 · cross — major_drift · 2 / 1 / 1 of 4

- 1 runs (P01#2): Sources every link: commit short hash with its subject, quoted trailers, file paths for the requirement spec, the error spec (DES-errors.md), the intent file, the change.md and the test file with its check class.
- 1 runs (P01#1): Commit short hash with its subject and quoted trailers. Paths for the job spec, change.md and the test file with its class. The intent and the TOP_INVALID error code have no file path.
- 2 runs (P02#1, P02#2): All commits by short hash, but most branch commits carry a stage label instead of their subject. Paths for the job spec, the change files and the test file with check classes. The intent has no file path. P02#1 writes b…

Only P01#2 sources each link, including a path to the intent file. P01#1 leaves the intent and the error code without a path. The P02 runs replace most commit subjects with stage labels and give no intent path. So the runs would grade differently, pass against partial.

## What to fix

1. "This skill answers trace questions" (the opening rule): give one form for each link, for example "commit: short hash and subject; spec, intent, change: the file path" → moves R6.
2. "From code": tell the run to name the requirement that the asked line serves, then the other requirements of the commit → moves R3 and R1.
3. Add a rule: each short ID in the reply, such as R7, keeps a short description → moves R10.

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
