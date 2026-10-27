# Vet Report: pdlc:init

**Skill:** `pdlc:init` · version `d791f6440460`
**Suite:** `evals/pdlc-init/suite.json` · `bbf60075f805`
**Run:** `base-20261027T100858Z` · 2 prompts × 3 runs · 5/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 96.8 | Weighted share of the rubric met across all runs |
| Stability | 75.3 | How little the output changed between runs |
| **Overall** | **85.4 (B)** | √(quality × stability) |

Per-run quality: min 94.7 · median 94.7 · max 100

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 96.8 | 76.3 | 85.9 (B) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The old init skill sets up a correct `pdlc/` folder each time: R1 (the copied files), R3 (the code maps), R5 (the check settings) and R9 (one clean commit) pass in each usable run. Every item passes in at least 80% of runs. The biggest issue is the list of unsure items in the final reply (R10). Some runs list unsure items and still put one of them in a code map, and other runs say that nothing is unsure. One run of P02 died on an API error that was not about the skill, so 5 of 6 runs are usable.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 The new `pdlc/` folder holds each file that init copies fro… | structure | 2 | 100% | 100 · identical | 100% | 100 · identical |
| R2 Each new job spec and capability spec is a stub in the form… | structure | 2 | 100% | 60 · minor_drift | 41.7% | 60 · minor_drift |
| R3 The code maps split the code of wordfreq into clear boundar… | outcome | 3 | 100% | 90 · equivalent | 100% | - |
| R4 `pdlc/config.md` has a chosen value in place of each placeh… | structure | 2 | 90% | 80 · minor_drift | 66.7% | 60 · minor_drift |
| R5 The six check settings work for this Python `unittest` proj… | outcome | 3 | 100% | 90 · equivalent | 100% | - |
| R6 With `defaults`, the run asks the user nothing, and the fin… | behavior | 2 | 100% | 60 · minor_drift | 66.7% | - |
| R7 Without `defaults`, the run asks one question at a time, ea… | behavior | 2 | 100% | 60 · minor_drift | 50% | - |
| R8 Each answer of the user that differs from the proposal of t… | outcome | 2 | - | - | - | - |
| R9 One commit on `main` records the new `pdlc/` folder, and th… | structure | 3 | 100% | 95 · equivalent | 100% | 100 · identical |
| R10 The final reply tells the user how to start with pdlc. | structure | 2 | 80% | 12.5 · contradictory | 58.4% | 25 · major_drift |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 defaults | typical: `defaults`, no questions | 96.5 | 76.3 | 3/3 |
| P02 set up pdlc for this project | interactive: no `defaults`, the user takes each recommended answer | 97.4 | 76.3 | 2/3 |

---

## Where it falls short

Every item met in at least 80% of runs.
## Where it varies

### R10 · P02 — contradictory · 1 / 1 of 2

- 1 runs (P02#1): Gives /pdlc:ship and the one-stage start with /pdlc:intake, and says that nothing in the map was unsure
- 1 runs (P02#2): Gives /pdlc:ship and /pdlc:intake, and lists three unsure recon items (empty __init__.py, README word definition, UTF-8 error). One item, __init__.py, is still in the CAP code map

The two runs give the same start instructions but reach opposite conclusions about unsure items. P02#1 says that nothing was unsure. P02#2 lists three unsure items, and still keeps __init__.py, one of those items, in a spec.

### R10 · P01 — major_drift · 2 / 1 of 3

- 1 runs (P01#1): Gives /pdlc:ship and /pdlc:intake as the two ways to start. Has an 'Unsure' list that names wordfreq/__init__.py, but the run put that file in the capability's code map. The list also names the checks that have no requi…
- 2 runs (P01#2, P01#3): Gives /pdlc:ship and 'one stage at a time, start with /pdlc:intake'. Says that nothing is unsure, and lists no unsure item.

All runs give the same two ways to start. Run 1 adds an Unsure list, and a spec holds one item on that list. Runs 2 and 3 say that nothing is unsure, although run 3 makes the same placement of __init__.py.

### R10 · cross — major_drift · 2 / 2 of 4

- 2 runs (P01#2, P02#1): The final reply gives /pdlc:ship <what you want> for all stages, and says to run one stage at a time starting with /pdlc:intake. It reports that nothing is unsure.
- 2 runs (P01#1, P02#2): The final reply gives both ways to start, and also lists unsure items. One of those items, wordfreq/__init__.py, is in the code map of the capability spec.

All runs give both ways to start. Two runs report no unsure items, and the other two list unsure items, including one that a spec's code map also holds. So the unsure-item part is present in some runs and absent in others, even for the same prompt.

## What to fix

1. "### 2. Map existing code": say what counts as an unsure item, for example an empty file such as `__init__.py` → moves R10.
2. "### 7. Finish": tell the run to check that no spec holds an item that the reply calls unsure → moves R10.

## Excluded runs and lost judges

- P02#3 — run agent died

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
