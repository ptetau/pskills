# Vet Report: [skill]

*(schema: `skill`, `skillSha256`, `suiteSha256`, `runId`, `config` — from `results.json`)*

**Skill:** `[skill]` · version `[skillSha256, first 12 chars]`
**Suite:** `evals/[skill]/suite.json` · `[suiteSha256, first 12 chars]`
**Run:** `[runId]` · [len(config.prompts)] prompts × [config.runs] runs ·
[scores.usableRuns]/[scores.totalRuns] runs usable · confidence [scores.confidence]
**Models:** skill runs on `[config.agents.run.model, with config.sessionModel if "session"]` ·
judges on `[config.agents.grade.model, …]`
**Agents:** preset `[config.agents.preset]` · waves of [config.wave] · [each role whose
effort or batch is different from the preset default, for example "grade effort low", or "no overrides"]

*(If `skillSha256` is different from the hash in the suite, add one line: "SKILL.md
changed after this suite was written. The rubric can be out of date. `/vet [skill] --regen`
builds the suite again.")*

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | [scores.quality] | Weighted share of the rubric met across all runs |
| Stability | [scores.stability] | How little the output changed between runs |
| **Overall** | **[scores.overall] ([scores.grade])** | √(quality × stability) |

Per-run quality: min [qualitySpread.min] · median [qualitySpread.median] · max [qualitySpread.max]

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

*(schema: `trajectory[]` and `settle`. Give one row for each wave. The stability in this
table is within-prompt only. Thus, the final row can be different from the headline
scores, which add the cross-prompt check.)*

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | [runsPerPrompt] | [quality] | [stability] | [overall] ([grade]) | [moved] |

[One sentence: "Settled at wave N (M runs per prompt)" or "Not settled: the grade still
moved by X points at the last wave, so more runs will help." If
`settle.stopWhenSettled` stopped the eval early, tell how many runs the early stop saved.]

## Verdict

*(Write 2-4 plain sentences. Does the skill do what it says, and does the skill do it the
same way each time? Name the single biggest issue. Do not add more doubt than the
numbers support.)*

[verdict]

---

## Rubric items

*(schema: `items[]`. The stability columns show the score and the class. For "same
prompt", give the worst class across prompts. Agreement is `agreementWithin`, the
average share of runs in the largest group. Write `-` where a value is not measured.)*

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 [criterion, shortened] | structure | 2 | [passRate]% | [stabilityWithin] · [worst class] | [agreementWithin]% | [stabilityCross] · [classCross] |

## Prompts

*(schema: `prompts[]`, joined with the `axis` of each prompt from the suite.)*

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 [prompt text, shortened] | [axis] | [quality] | [stability] | [usableRuns]/[config.runs] |

---

## Where it falls short

*(List the items with a passRate under 80, lowest first. For each item, give what the
item asks, the met/partial/missed counts, and one or two evidence quotes with run labels,
from `runs[].verdicts`. If no item has a passRate under 80, write "Every item met in at
least 80% of runs.")*

### R[n] [criterion] — met in [passRate]% of runs

[met X · partial Y · missed Z] — [one sentence on the pattern]

> [evidence] — [run label]

## Where it varies

*(List each similarity judgement with the class major_drift or contradictory, from
`similarity[]`, worst first. Show the groups, so that the reader sees how the runs split.
If there is no such judgement, write "No item drifted beyond minor_drift.")*

### R[n] [criterion] · [scope: P01, or across prompts] — [class] · [tally.split]

- [N] runs ([labels]): [group description]
- [N] runs ([labels]): [group description]

[reason]

## What to fix

*(Give 3-5 concrete edits to SKILL.md. For each edit, name the section to change and the
items that the edit moves. Suggest only what the evidence above supports. A vague rule in
SKILL.md is the usual cause of drift. Show the rule, and tell how to make the rule
exact.)*

1. [section] — [change] → moves [R-ids]

## Excluded runs and lost judges

*(Use `excluded[]`, `lostJudges[]`, and each `similarity[]` entry whose `tally.clean` is
false (the judge did not place each run exactly one time). If all of these are empty,
write "None.")*

- [label] — [reason]

---

## Appendix

- Captures: `evals/[skill]/runs/[runId]/outputs/` (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, which validates against `vet/references/results.schema.json`
