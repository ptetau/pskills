# Vet Report: [skill]

*(schema: `skill`, `skillSha256`, `suiteSha256`, `runId`, `config` — from `results.json`)*

**Skill:** `[skill]` · version `[skillSha256, first 12 chars]`
**Suite:** `evals/[skill]/suite.json` · `[suiteSha256, first 12 chars]`
**Run:** `[runId]` · [len(config.prompts)] prompts × [config.runs] runs ·
[scores.usableRuns]/[scores.totalRuns] runs usable · confidence [scores.confidence]

*(If `skillSha256` differs from the suite's, add one line: "SKILL.md changed since this
suite was written; the rubric may be stale. `/vet [skill] --regen` rebuilds it.")*

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | [scores.quality] | Weighted share of the rubric met across all runs |
| Stability | [scores.stability] | How little the output changed between runs |
| **Overall** | **[scores.overall] ([scores.grade])** | √(quality × stability) |

Per-run quality: min [qualitySpread.min] · median [qualitySpread.median] · max [qualitySpread.max]

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## Verdict

*(2-4 plain sentences: does the skill do what it says, and does it do it the same way
each time? Name the single biggest issue. No hedging beyond what the numbers support.)*

[verdict]

---

## Rubric items

*(schema: `items[]`. Stability columns show the score and the class; for "same prompt",
give the worst class across prompts. `-` where not measured.)*

| Item | Kind | Wt | Met | Stability, same prompt | Stability, across prompts |
|---|---|---|---|---|---|
| R1 [criterion, shortened] | structure | 2 | [passRate]% | [stabilityWithin] · [worst class] | [stabilityCross] · [classCross] |

## Prompts

*(schema: `prompts[]`, joined with the suite's `axis` for each prompt.)*

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 [prompt text, shortened] | [axis] | [quality] | [stability] | [usableRuns]/[config.runs] |

---

## Where it falls short

*(Items with passRate under 80, lowest first. For each: what the item asks, the
met/partial/missed counts, and one or two evidence quotes with run labels, from
`runs[].verdicts`. Write "Every item met in at least 80% of runs." if none.)*

### R[n] [criterion] — met in [passRate]% of runs

[met X · partial Y · missed Z] — [one sentence on the pattern]

> [evidence] — [run label]

## Where it varies

*(Every similarity judgment classed major_drift or contradictory, from `similarity[]`,
worst first. Show the groups so the reader sees how the runs split. Write "No item
drifted beyond minor_drift." if none.)*

### R[n] [criterion] · [scope: P01, or across prompts] — [class]

- [N] runs ([labels]): [group description]
- [N] runs ([labels]): [group description]

[reason]

## What to fix

*(3-5 concrete edits to SKILL.md, each naming the section to change and the items it
should move. Only suggest what the evidence above supports. A vague rule in SKILL.md
is the usual cause of drift: point at the rule and say how to make it exact.)*

1. [section] — [change] → moves [R-ids]

## Excluded runs and lost judges

*(From `excluded[]` and `lostJudges[]`. Write "None." if both are empty.)*

- [label] — [reason]

---

## Appendix

- Captures: `evals/[skill]/runs/[runId]/outputs/` (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
