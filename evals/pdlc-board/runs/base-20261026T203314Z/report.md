# Vet Report: pdlc:board

**Skill:** `pdlc:board` · version `4ff8bd954efc`
**Suite:** `evals/pdlc-board/suite.json` · `d94bfb9c7d39`
**Run:** `base-20261026T203314Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `claude-sonnet-5-5` · judges on `claude-opus-5-5`
**Agents:** preset `lean` · waves of 3 · no overrides

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 89.6 | Weighted share of the rubric met across all runs |
| Stability | 60.4 | How little the output changed between runs |
| **Overall** | **73.6 (C)** | √(quality × stability) |

Per-run quality: min 83.3 · median 86.8 · max 100

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 3 | 89.6 | 60.4 | 73.6 (C) | - |

Not settled: this eval judged one wave of 3 runs per prompt, so no later wave could confirm the grade.

## Verdict

The old board skill lists the right cards and changes nothing: R1 (true card list), R4 (no pdlc change) and R9 (no board write) pass in each run. The biggest issue is what it says about the board that it could not read. Four of six runs say "the board needs 3 new cards" as a fact (R3). Half the runs name the block but give no step to remove it (R8). One wave of 3 runs per prompt is a small sample, so the stability score is rough.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 The user gets the true list of cards. The list has one card… | outcome | 3 | 100% | 57.5 · major_drift | 83.4% | - |
| R2 The dry-run table gives the card key, the current column, a… | structure | 2 | 100% | 60 · minor_drift | 66.7% | - |
| R3 The user can trust each statement about the board, because … | outcome | 3 | 66.7% | 60 · minor_drift | 66.7% | - |
| R4 pdlc stays the truth: the run changes no pdlc file and make… | behavior | 3 | 100% | 90 · equivalent | 100% | - |
| R5 The user who set a tracker does not hear that the project h… | outcome | 2 | 100% | 42.5 · major_drift | 66.7% | - |
| R6 When the setup check finds a gap, the reply names the exact… | structure | 2 | 91.7% | 42.5 · major_drift | 66.7% | 60 · minor_drift |
| R7 After a sync, the run records each new card key and reports… | structure | 1 | - | - | - | - |
| R8 The user knows what to do next: the reply names each block … | outcome | 2 | 75% | 42.5 · major_drift | 83.4% | - |
| R9 When the user asks for a dry-run, the run makes no board wr… | behavior | 2 | 100% | 90 · equivalent | 100% | - |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 dry-run | typical | 86.8 | 65.3 | 3/3 |
| P02 defaults | sync without dry-run, with defaults | 93.6 | 54.3 | 3/3 |

---

## Where it falls short

### R3 The user can trust each statement about the board, because the reply states only what the… — met in 66.7% of runs

met 2 · partial 4 · missed 0

> This is a dry run. The board needs 3 new cards — P01#1
> Dry run: the board needs 3 new cards and no moves. — P01#2

### R8 The user knows what to do next: the reply names each block on the board work, and a step … — met in 75% of runs

met 3 · partial 3 · missed 0

> This session has no tool for GitHub projects, so I could not read the board. — P01#1
> The skill commits on main, but the README lets only `record_merges.py` commit on main while a pdlc branch is unmerged. — P01#2

## Where it varies

### R5 · P01 — major_drift · 2 / 1 of 3

- 2 runs (P01#1, P01#2): Takes the tracker as set without naming it: talks only about the missing GitHub projects tool, not about the tracker settings.
- 1 runs (P01#3): Names the tracker tracker-github-projects and confirms that owner example-org, project 7 and status field Status are all present.

No run says there is no tracker. But only run 3 states the tracker and its settings, and runs 1 and 2 leave the tracker implicit.

### R8 · P01 — major_drift · 2 / 1 of 3

- 2 runs (P01#1, P01#3): Names the block (no GitHub projects tool) but gives no next step to remove it.
- 1 runs (P01#2): Gives a 'Two things to settle before a real run' section: add a GitHub projects tool (gh project commands or GitHub project tools), and handle where the card keys get committed while the branch is unmerged.

Only run 2 gives steps that remove the blocks. Runs 1 and 3 name the missing tool and give no step.

### R1 · P02 — major_drift · 2 / 1 of 3

- 2 runs (P02#1, P02#2): Gives no list of cards; the reply stops at the board-access gap.
- 1 runs (P02#3): Lists all three cards with correct status and column: IN-0001 and CH-0001 in review/In review, IN-0002 new/Backlog.

Only P02#3 lists the cards, and its list is correct. P02#1 and P02#2 list no cards at all, so the item shows up in one run and not in the other two.

### R6 · P02 — major_drift · 2 / 1 of 3

- 2 runs (P02#1, P02#2): Names the gap (no gh project tool; gh api got HTTP 403 on the project) and stops with no card table.
- 1 runs (P02#3): Names the gap with its reason and confirms the settings are present, says it stopped at step 1, but still shows the pdlc card list with target columns after the gap.

All runs name the same access gap and its cause. P02#3 still shows the card table after the gap without a dry-run, while P02#1 and P02#2 stop cleanly.

## What to fix

1. "## 3" (dry-run table): when the run cannot read the board, say "if the board has no cards yet" and not "the board needs N new cards" → moves R3 (no claim about the unread board).
2. "## 1. Examine the setup": for each block, tell the user the one step that removes it, for example "give this session the `gh project` commands" → moves R8 (a step that removes each block).
3. "## 1. Examine the setup": when the run finds the tracker and its settings, tell the run to name them. Then the user sees that the setup is right → moves R5 (the set tracker is not called missing) and R6 (name the exact gap and stop).

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `outputs/` in this folder (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
