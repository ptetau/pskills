# Evals

This folder holds the saved evals of the `/vet` skill. `/vet` scores another skill on
quality and stability. For how `/vet` works, read `../vet/README.md`.

## What is here

- A **suite** is one folder for one skill, for example `evals/quiz/`. Its `suite.json`
  holds the rubric and the test prompts. `/vet` writes a suite once and uses it again, so
  that later runs compare.
- A **run** is one execution of a suite. Its folder is `evals/<skill>/runs/<label>-<time>/`.
  The name `pdlc-ready` means the suite of the skill `/pdlc:ready`.

A run folder holds these files:

- `results.json`: the scores, and the settings that the comparison script checks.
- `report.md`: the report for a person. Some runs have no report.
- `outputs/`: the captured output of each run, one file for each prompt and repeat.
- `compare*.txt` and `pooled-*.json`: the comparison of two runs, if the run has any.

## Which runs remain

This folder keeps only the runs that a comparison today needs. Git history holds the
other runs. To read one, check out an older commit.

| Suites | Runs kept | Why |
|---|---|---|
| `argue`, `quiz`, `quiz-plan`, `quiz-plan-execute`, `pdlc-board`, `pdlc-conventions`, `pdlc-init`, `pdlc-trace` | The newest run | The newest run is the latest score. |
| `pdlc-acceptance`, `pdlc-build`, `pdlc-change`, `pdlc-intake`, `pdlc-ready`, `pdlc-ship`, `pdlc-show`, `pdlc-tests`, `pdlc-verify` | Each `plugin-M*` and `plugin-N*` run, with its pooled files | `M` is the run of the earlier skill text, and `N` is the run of the new text. They use the same suite and runner, so they compare. |
| `pdlc-acceptance`, `pdlc-change`, `pdlc-intake`, `pdlc-ready`, `pdlc-ship` | The `decl*` and `master-base*` runs that `scripts/skill_budgets.json` names | The `evidence` fields of that file name these runs. |
| `blueprint`, `decompose`, `quiz-visual` | None | These suites have no run yet. |

Older runs used older suites, runners, or workflow scripts. `compare_vet.py` cannot compare
them with a new run.

## Compare two runs

```
python3 improve-writing/scripts/compare_vet.py BASELINE/results.json CANDIDATE/results.json
```

For example, replace `BASELINE` with `evals/pdlc-tests/runs/plugin-M-20261102T134321Z`, and
`CANDIDATE` with `evals/pdlc-tests/runs/plugin-N-20261102T134204Z`. The exit code is 0 for a
pass, 1 for a fail, and 2 when the two runs are not comparable.
