# Vet Report: pdlc:init

**Skill:** `pdlc:init` · version `49640041d0fc`
**Suite:** `evals/pdlc-init/suite.json` · `bbf60075f805`
**Run:** `new-20261027T103303Z` · 2 prompts × 3 runs · 5/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

SKILL.md changed since this suite was written; the rubric may be stale. `/vet pdlc:init --regen` rebuilds it.

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 98.9 | Weighted share of the rubric met across all runs |
| Stability | 72.2 | How little the output changed between runs |
| **Overall** | **84.5 (B)** | √(quality × stability) |

Per-run quality: min 94.7 · median 100 · max 100

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 98.9 | 73.4 | 85.2 (B) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The new init skill (0.4.0) sets up a correct `pdlc/` folder each time, as the old one does: R1, R3, R5 and R9 pass in each usable run. Against the old version (0.3.0), overall moves from 85.4 to 84.5, and `compare_vet.py` shows NO REGRESSION. R10 (how to start) rises to 100%, and R4 (no placeholder in the config) rises to 100%. The biggest issue is R6: one run lists its decisions but omits some topics. One run of P02 died on an API error that was not about the skill, as in the baseline, so 5 of 6 runs are usable.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 The new `pdlc/` folder holds each file that init copies fro… | structure | 2 | 100% | 80 · minor_drift | 75% | 60 · minor_drift |
| R2 Each new job spec and capability spec is a stub in the form… | structure | 2 | 100% | 60 · minor_drift | 58.4% | 60 · minor_drift |
| R3 The code maps split the code of wordfreq into clear boundar… | outcome | 3 | 100% | 80 · minor_drift | 83.4% | - |
| R4 `pdlc/config.md` has a chosen value in place of each placeh… | structure | 2 | 100% | 80 · minor_drift | 83.4% | 60 · minor_drift |
| R5 The six check settings work for this Python `unittest` proj… | outcome | 3 | 100% | 75 · minor_drift | 66.7% | - |
| R6 With `defaults`, the run asks the user nothing, and the fin… | behavior | 2 | 83.3% | 60 · minor_drift | 33.3% | - |
| R7 Without `defaults`, the run asks one question at a time, ea… | behavior | 2 | 100% | 60 · minor_drift | 50% | - |
| R8 Each answer of the user that differs from the proposal of t… | outcome | 2 | - | - | - | - |
| R9 One commit on `main` records the new `pdlc/` folder, and th… | structure | 3 | 100% | 95 · equivalent | 100% | 90 · equivalent |
| R10 The final reply tells the user how to start with pdlc. | structure | 2 | 100% | 42.5 · major_drift | 41.7% | 60 · minor_drift |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 defaults | typical: `defaults`, no questions | 98.2 | 68.9 | 3/3 |
| P02 set up pdlc for this project | interactive: no `defaults`, the user takes each recommended answer | 100 | 77.9 | 2/3 |

---

## Where it falls short

Every item met in at least 80% of runs.
## Where it varies

### R10 · P02 — major_drift · 1 / 1 of 2

- 1 runs (P02#1): Gives /pdlc:ship <what you want> and /pdlc:intake for one stage at a time. Lists two unsure items in no spec (accented letters counted wrong, and a traceback instead of the README error on a non-UTF-8 file).
- 1 runs (P02#3): Gives /pdlc:ship and /pdlc:intake in the same way, but says 'Unsure items: none'. Adds a note about a 25-word sentence in DES-pdlc-commit-trailers (commit trailers) and an offer to change a decision.

Both runs give the two ways to start in near-identical words. Run 1 reports two README-versus-code mismatches as unsure items. Run 3 reports no unsure items and adds a different note, so the content of the final reply differs materially.

## What to fix

1. Outputs, the decision list: name the topics that the list covers (the map, the branch names, the check names, the writing style, the check settings and the adapters) → moves R6.

## Excluded runs and lost judges

- P02#2 — run agent died

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
