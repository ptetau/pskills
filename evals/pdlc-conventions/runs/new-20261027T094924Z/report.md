# Vet Report: pdlc:conventions

**Skill:** `pdlc:conventions` · version `003a8d31f2f2`
**Suite:** `evals/pdlc-conventions/suite.json` · `970724430e93`
**Run:** `new-20261027T094924Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

SKILL.md changed since this suite was written; the rubric may be stale. `/vet pdlc:conventions --regen` rebuilds it.

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 95.6 | Weighted share of the rubric met across all runs |
| Stability | 60.8 | How little the output changed between runs |
| **Overall** | **76.2 (C)** | √(quality × stability) |

Per-run quality: min 88.1 · median 95.2 · max 100

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 95.6 | 64 | 78.2 (C) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The new conventions skill (0.4.0) finds the right migration intents and starts no work, as the old one does. R5 (exactly the needed migration intents) and R7 (no intent started, no code migrated) pass in each run. Against the old version (0.3.0), overall moves from 76.6 to 76.2, and `compare_vet.py` shows NO REGRESSION. R1 (the question before the spec) rises to 100%. The biggest issue is the recommendation in P01 (change the errors convention): one run keeps `error: ` after the new prefix, and two runs replace it. Thus, the rule itself differs between runs, and both R1 (the question before the spec) and R4 (a rule that needs no guess) drift.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 Before the run writes the convention, it names the subject … | structure | 2 | 100% | 0 · contradictory | 33.3% | - |
| R2 With `defaults`, the run asks no question and takes its rec… | behavior | 2 | 100% | 60 · minor_drift | 100% | - |
| R3 The design spec has the form of the design template. A new … | structure | 2 | 100% | 90 · equivalent | 100% | 60 · minor_drift |
| R4 The user gets a rule that a later stage can apply with no g… | outcome | 3 | 91.7% | 30 · contradictory | 50% | - |
| R5 The user gets exactly one migration intent for each job or … | outcome | 3 | 100% | 90 · equivalent | 100% | - |
| R6 Each intent that the run adds is a file from the intent tem… | structure | 2 | 100% | 60 · minor_drift | 66.7% | 60 · minor_drift |
| R7 The run does not start the intents, and does not migrate an… | behavior | 3 | 100% | 90 · equivalent | 100% | - |
| R8 The run commits all its work on main, in one commit with th… | structure | 2 | 100% | 75 · minor_drift | 83.4% | 90 · equivalent |
| R9 The closing message tells the user how many migration inten… | structure | 2 | 75% | 60 · minor_drift | 50% | 25 · major_drift |
| R10 The design spec has requirements for the convention, with t… | structure | 2 | 91.7% | 42.5 · major_drift | 50% | 0 · contradictory |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 Change our errors convention, DES-errors. Each er… | typical | 94.4 | 53.8 | 3/3 |
| P02 defaults: set a convention for how numbers show i… | new convention with defaults, terse | 96.8 | 74.3 | 3/3 |

---

## Where it falls short

### R9 The closing message tells the user how many migration intents the run added. It also says… — met in 75% of runs

met 3 · partial 3 · missed 0

> I started neither intent. Run IN-0001 (the migration) first — P01#3
> I added 0 migration intents. — P02#2

## Where it varies

### R1 · P01 — contradictory · 1 / 1 / 1 of 3

- 1 runs (P01#1): Names subject and pipe reason, asks one question with three options (every message keep `error: `, file error only, every message replace `error: `), recommends keeping `error: `
- 1 runs (P01#2): Names subject and pipe reason, asks one question with three options A/B/C, recommends A (both lines, prefix replaces `error: `)
- 1 runs (P01#3): Names subject and reason, lists both current messages, asks only how the read-failure message looks with two options, recommends replacing `error: `; usage prefix fixed in both

All three runs ask one question before they write. Run 1 recommends keeping `error: ` after the prefix, and runs 2 and 3 recommend replacing it, so the recommendations are opposite. Run 3 also asks a narrower question with two options, and the other runs give three.

### R4 · P01 — contradictory · 1 / 1 / 1 of 3

- 1 runs (P01#1): Rule: every error message incl. usage starts with `wordfreq: `, rest of message kept, so output is `wordfreq: error: cannot read missing.txt`
- 1 runs (P01#2): Rule: each line on standard error starts with `wordfreq: `, incl. usage, and the prefix explicitly replaces `error: ` (`wordfreq: cannot read /no/such/file.txt`)
- 1 runs (P01#3): Rule: each error message incl. usage must start with `wordfreq: `; rule text does not say `error: ` is dropped, only the example shows `wordfreq: cannot read ...`

Run 1 makes `wordfreq: error: cannot read <path>` the rule, and runs 2 and 3 make `wordfreq: cannot read <path>` the rule. These outcomes are incompatible. Also, run 2 states the replacement and the stderr scope in the rule, and run 3 shows the replacement only in its example.

### R10 · cross — contradictory · 2 / 1 / 1 of 4

- 1 runs (P01#1): R1 is proposed with Given/when/then lines and 'Intents: IN-0002'. IN-0002 is a separate intent that builds the check, apart from the migration intent.
- 1 runs (P01#2): R1 is proposed with Given/when/then lines and 'Intents: IN-0001', which is the migration intent. No separate check intent exists, because the check is folded into the migration intent.
- 2 runs (P02#1, P02#2): R1 is proposed with Given/when/then lines and 'Intents: IN-0001'. IN-0001 is a separate intent that builds the check, and there are no migration intents.

On the same input, P01#1 adds a separate check intent, and P01#2 deliberately puts the check inside the migration intent. These choices are opposite and cannot both hold. The P02 runs agree with each other.

### R10 · P01 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P01#1): DES-errors.R1 proposed with Intents: IN-0002, three Given/when/then lines, separate check intent IN-0002
- 1 runs (P01#2): DES-errors.R1 proposed with Intents: IN-0001, no separate check intent; the check is folded into the migration intent
- 1 runs (P01#3): DES-errors.R1 proposed with Intents: IN-0001, IN-0002, two Given/when/then lines, separate check intent IN-0002

All runs add a proposed requirement, DES-errors.R1, but run 2 adds no separate check intent and folds the check into the migration intent. Runs 1 and 3 add a separate check intent. The Intents values also differ: IN-0002, IN-0001, and IN-0001 with IN-0002.

### R9 · cross — major_drift · 1 / 1 / 1 / 1 of 4

- 1 runs (P01#1): Summary first. Then 'I added 1 migration intent' with IN-0001 described, and a separate block '1 more intent, to build the check' (IN-0002). It closes with 'Both intents have the status new. Name one to start it'.
- 1 runs (P01#2): Opens with 'I added 1 migration intent'. IN-0001 is described as also building the check, so there is no separate check block. It says 'I did not start it' and 'run /pdlc:intake IN-0001 when you choose'.
- 1 runs (P02#1): 'Done' summary, then bullets with 'Migration intents added: 0' and the reason. The check intent IN-0001 is a separate bullet with 'I did not start it'. It closes with 'To build the check, run /pdlc:intake IN-0001'.
- 1 runs (P02#2): Opens with 'I added 0 migration intents', then the reason. The check intent IN-0001 is listed with 'I did not start it'. No line says that the user selects when the intent runs, and no start command is given.

Every run gives the migration count and says the intents did not start. The P01 runs differ in layout: one has separate migration and check blocks, and the other has one intent that also builds the check. P02#2 drops the statement that the user selects when each intent runs.

## What to fix

1. Constraints: when a new rule meets an old one, say whether the recommendation keeps or replaces the old part. Also say why → moves R4 (a rule that needs no guess) and R1 (the question before the spec).
2. Constraints: say whether the check gets its own intent or rides in the migration intent → moves R10 (requirements and one check intent) and R9 (the count in the closing message).

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
