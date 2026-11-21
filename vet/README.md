# `/vet` — Skill Evaluator

`/vet` writes and runs an eval for a different skill. A good skill meets its own rubric. A
good skill also gives almost the same output each time. `/vet` scores the two qualities
with these steps:

1. `/vet` reads the SKILL.md of the target skill. `/vet` extracts the expected **output
   structure** and a **rubric** (`structure`, `behavior`, and `outcome` items, weighted,
   each with a citation of its source).
2. `/vet` writes **10 varied test prompts**. For an interactive skill, `/vet` also writes
   scripted user replies.
3. `/vet` asks **which models** to use for the skill and for the judges. The models are
   the biggest variable in an eval.
4. `/vet` runs **3 prompts × 10 repeats** in waves, in parallel through a `Workflow`. Each
   run is in its own git worktree.
5. **Rubric judges** grade each run: met / partial / missed / n/a, with evidence.
6. **Similarity judges** (by default, one for each prompt in each wave) put each new run
   into the current groups for each rubric item. The judges classify the run on this
   scale: identical → equivalent → minor drift → major drift → contradictory. Structure
   items are also compared across prompts. The `Workflow` script counts each split, for
   example `7 / 3 of 10`.
7. `/vet` scores **quality**, **stability**, and **overall** = √(quality × stability).
   `/vet` records the grade after each wave, so you can watch the grade **settle**. To
   stop early when the grade settles, add `--stop-when-settled`.

You select what each agent does. Each of the four roles (`run`, `grade`, `compare`,
`cross`) has its own model, effort, and batching. The presets set the batching:

| Preset | Agents, 3 × 10 runs in waves of 2 | One wave (`--wave 10`) | Judges |
|---|---|---|---|
| `thorough` | up to 213 | 93 | one per run, one per rubric item |
| `lean` (default) | up to 61 | 37 | one grader and one comparer per prompt |
| `minimal` | up to 46 | 34 | one judge per prompt grades and compares |

You can override a role in `evals/agents.json`, or for one run, for example
`/vet quiz --agent grade.model=<model> --agent grade.effort=low`.

`/vet` saves the suite to `evals/<skill>/suite.json`, and uses the suite again. Thus, you
can compare later runs. You examine the rubric and the prompts one time, when `/vet` first
writes a suite.

**Example**

```
/vet quiz
```

**Output (excerpt)**

```
wave 1/5 (2 of 10 runs per prompt): quality 90.2 · stability 81.0 · overall 85.5 (B) · settling
wave 2/5 (4 of 10 runs per prompt): quality 88.4 · stability 75.3 · overall 81.6 (B) · moved -3.9 · settling
wave 3/5 (6 of 10 runs per prompt): quality 88.1 · stability 74.1 · overall 80.8 (B) · moved -0.8 · settling
wave 4/5 (8 of 10 runs per prompt): quality 88.0 · stability 74.4 · overall 80.9 (B) · moved +0.1 · settled

Quality 88 · Stability 74 · Overall 80.7 (B)    30/30 runs usable · settled at wave 4

Where it varies
  R5 question order · P02 — major_drift
    6 runs (P02#1,#2,#4,#6,#7,#9): asks about audience first
    4 runs (P02#3,#5,#8,#10):      asks about scope first
```

`/vet` writes `evals/quiz/runs/<runId>/report.md`, `results.json`, and one capture for
each run. `/vet` has these options: `--prompts N`, `--sample M`, `--runs R`,
`--use P02,P07`, `--regen`, `--wave W`, `--stop-when-settled`, `--preset`,
`--agent role.key=value`.
