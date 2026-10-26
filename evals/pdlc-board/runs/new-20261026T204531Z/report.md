# Vet Report: pdlc:board

**Skill:** `pdlc:board` · version `9506f2b8a3a6`
**Suite:** `evals/pdlc-board/suite.json` · `d94bfb9c7d39`
**Run:** `new-20261026T204531Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

SKILL.md changed since this suite was written; the rubric may be stale. `/vet pdlc:board --regen` rebuilds it.

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 93.1 | Weighted share of the rubric met across all runs |
| Stability | 63.5 | How little the output changed between runs |
| **Overall** | **76.9 (C)** | √(quality × stability) |

Per-run quality: min 86.8 · median 92.4 · max 100

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 93.1 | 63.7 | 77 (C) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The new board skill (0.4.0) lists the right cards and changes nothing, as the old one does: R1, R4 and R9 pass in each run. Against the old version (0.3.0), overall rises from 73.6 to 76.9, and `compare_vet.py` shows NO REGRESSION. R3 (no claim about the unread board) rises from 66.7% to 83.3%. The biggest issue is still R8: half the runs name the missing GitHub projects tool but give no step to add it.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 The user gets the true list of cards. The list has one card… | outcome | 3 | 100% | 60 · minor_drift | 83.4% | - |
| R2 The dry-run table gives the card key, the current column, a… | structure | 2 | 100% | 60 · minor_drift | 100% | - |
| R3 The user can trust each statement about the board, because … | outcome | 3 | 83.3% | 42.5 · major_drift | 66.7% | - |
| R4 pdlc stays the truth: the run changes no pdlc file and make… | behavior | 3 | 100% | 90 · equivalent | 100% | - |
| R5 The user who set a tracker does not hear that the project h… | outcome | 2 | 100% | 60 · minor_drift | 50% | - |
| R6 When the setup check finds a gap, the reply names the exact… | structure | 2 | 91.7% | 60 · minor_drift | 66.7% | 60 · minor_drift |
| R7 After a sync, the run records each new card key and reports… | structure | 1 | - | - | - | - |
| R8 The user knows what to do next: the reply names each block … | outcome | 2 | 75% | 57.5 · major_drift | 66.7% | - |
| R9 When the user asks for a dry-run, the run makes no board wr… | behavior | 2 | 100% | 90 · equivalent | 100% | - |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 dry-run | typical | 90.4 | 58.7 | 3/3 |
| P02 defaults | sync without dry-run, with defaults | 96.7 | 70 | 3/3 |

---

## Where it falls short

### R8 The user knows what to do next: the reply names each block on the board work, and a step … — met in 75% of runs

met 3 · partial 3 · missed 0

> It needs a tool for GitHub projects. — P01#1
> This session has no tool for GitHub projects, so I did no column check. — P01#2

## Where it varies

### R3 · P01 — major_drift · 2 / 1 of 3

- 2 runs (P01#1, P01#3): Opens with pdlc-side facts (three items, none has a card key), says the board is unreachable, and hedges that a real run looks up each ID before it makes a card.
- 1 runs (P01#2): Opens with 'The board needs 3 new cards', which reads as a fact about the board, then says the board is unreachable and that a card can exist already.

P01#2 opens with an unverified claim that the board needs 3 new cards, and only hedges it later. P01#1 and P01#3 make no claim about what is on the board.

### R8 · P01 — major_drift · 1 / 1 / 1 of 3

- 1 runs (P01#1): Names the block (no GitHub projects tool) and says that a real run needs a tool for GitHub projects, which implies the fix.
- 1 runs (P01#2): Names the block (no GitHub projects tool) but gives no step that removes it.
- 1 runs (P01#3): Names the block (board unreachable) with no step for access. Instead lists the board columns that a real run needs.

Only P01#1 points to the fix for the access block. P01#2 gives no next step, and P01#3 gives a step for a different possible block (missing columns) and not for access.

## What to fix

1. Outputs: for each block, the reply gives the one step that removes it, for example "give this session the `gh project` commands" → moves R8.
2. Constraints, the dry-run rule: say "if the board has no cards yet" when the run cannot read the board → moves R3.

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
