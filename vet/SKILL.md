---
name: vet
description: >
  Writes and runs an eval for a different skill. Then scores the skill on two axes:
  quality (how well its output meets a rubric from the skill itself) and stability (how
  little its output changes between runs). Reads the target SKILL.md to get the expected
  output structure and a rubric. Writes varied test prompts, with scripted user replies
  for interactive skills. Runs a sample of the prompts many times each, in isolated git
  worktrees, through a Workflow. A rubric judge grades each run. Similarity judges
  classify and tally each rubric item by how much it changed across repeats, and across
  prompts for structure items. Runs go in waves, and the script records the grade after
  each wave, so you can see the grade settle. Asks which models to use before each eval.
  Each agent role (run, grade, compare, cross) can have its own model, effort, and
  batching, through presets or overrides, to balance cost against focus. Saves the suite
  to evals/SKILL-NAME/ so that later runs are comparable. Use when the user says "/vet",
  or asks to "eval a skill", "test this skill", "score my skill", or "how consistent is
  this skill". Also use when the user wants to check a skill before they trust it.
---

# Vet: Skill Evaluator

## Purpose

A good skill does two things. Its output keeps the promises in its own SKILL.md. Also,
the same input gives much the same output each time. `/vet` measures the two things:

- **Quality (0-100):** the weighted share of the rubric that the output meets, across
  all runs.
- **Stability (0-100):** how similar the outputs are, rubric item by rubric item, across
  repeated runs of the same prompt. Stability also includes the structure across
  different prompts.
- **Overall (0-100):** √(quality × stability). A skill that is reliably wrong gets a low
  score. A skill that is right but erratic also gets a low score. Thus, one axis cannot
  hide the other axis.

The pipeline has these steps, in this order:

1. Extract the structure and the rubric.
2. Write the test prompts.
3. Run each sampled prompt many times, in isolation.
4. Grade each run.
5. Judge the similarity of each rubric item.
6. Calculate the scores.

## Writing

Write all text to `references/writing-guidelines.md`. This includes the replies to the
user, each question, and each file that this skill writes.

## Usage

```
/vet <skill> [--prompts N] [--sample M] [--runs R] [--use P02,P07] [--regen]
             [--wave W] [--stop-when-settled]
             [--preset thorough|lean|minimal] [--agent role.key=value …]
```

| Argument | Default | Meaning |
|---|---|---|
| `<skill>` | necessary | The skill name, or a path to its folder or to its SKILL.md |
| `--prompts N` | 10 | The number of test prompts to write for a new suite |
| `--sample M` | 3 | The number of prompts to run this time (the first M in the suite) |
| `--runs R` | 10 | The number of repeats of each sampled prompt. The minimum is 2. |
| `--use` | none | Run these prompt IDs instead of the first M |
| `--regen` | off | Build the suite again, also if a suite exists |
| `--wave W` | 2 | The number of repeats of each prompt in each wave. The grade updates after each wave. `--wave R` judges one time, at the end. |
| `--stop-when-settled` | off | Start no new wave after the grade settles. See "Settling". |
| `--preset` | `lean` | How much work each judge does. See "Agent roles". |
| `--agent role.key=value` | none | Override one role setting for this run, for example `--agent grade.model=<model>`. You can use this flag more than one time. |

A run with the defaults (3 prompts × 10 runs in waves of 2, `lean`) and a 10-item rubric
starts a maximum of 61 agents:

- 30 runs.
- 15 rubric judges and 15 similarity judges: one of each for each prompt in each wave.
- 1 cross-prompt judge.

To balance the cost against the focus, see "Agent roles" and "Settling".

## Files

```
evals/agents.json             optional repo-wide agent roles    (references/agents.schema.json)
evals/<skill>/
  suite.json                  structure, rubric, prompts   (references/suite.schema.json)
  runs/<runId>/
    outputs/P01-r01.md …      one capture per run: transcript + files the run wrote
                              (copied here from each run's worktree after the run)
    results.json              scores and every judgment    (references/results.schema.json)
    report.md                 the human report             (references/report-template.md)
```

The `evals/` folder is at the root of the git repo where you run `/vet`. The folder is
next to the skill folders, not in a skill folder. Thus, a skill folder stays clean, and
you can copy the skill folder into `~/.claude/skills/`.

Commit `suite.json`. Each re-run uses the same `suite.json` again, and thus the scores
stay comparable over time.

## Phase 0: Resolve

1. **Find the skill.** If the user gave a path, use the path. If not, try these paths
   in this order: `./<name>/SKILL.md`, `.claude/skills/<name>/SKILL.md`,
   `~/.claude/skills/<name>/SKILL.md`. If the skill is missing, or if more than one path
   matches, stop and ask.
2. **Find the repo root** with `git rev-parse --show-toplevel`. The isolated worktrees
   need git. If this is not a git repo, stop and say so.
3. **Fingerprint the skill:** get the `sha256sum` of the SKILL.md of the skill.
4. **Check for a saved suite** at `evals/<skill>/suite.json`. If the suite exists and
   there is no `--regen`, load the suite. Then go directly to Phase 3b (models). If the
   `skillSha256` of the suite is different from the hash of today, say so in one line.
   Then continue. The suite still works, and the same suite keeps the scores comparable.
   `--regen` builds the suite again, but it also starts a new baseline.

## Phase 1: Structure and rubric (new suite only)

Read the full target SKILL.md. Also read each file that the SKILL.md refers to
(references, templates, schemas). Then write two things.

**Structure.** The structure tells what the output looks like, as SKILL.md specifies it:

- A `summary` of one or two sentences. The summary gives the turn pattern (a single
  reply, or multi-turn and how the turns alternate) and the overall shape.
- The `elements` S1, S2, …: each necessary section, block, format, file, or turn rule,
  in order. Write only what SKILL.md states or clearly implies. Do not invent structure.

**Rubric.** Write 6-12 items, R1, R2, …. Each item is one checkable claim about the
output:

- `kind` is one of these values:
  - `structure`: the shape of the output. Each structure item covers one S element, or
    a few closely related S elements (`structureRef`). Make sure that a structure item
    covers each S element.
  - `behavior`: a process rule that you can see in the output. Examples are "one
    question per turn" and "marks exactly one option recommended". The "don't" list of
    the skill is a good source.
  - `outcome`: whether the output does its job for the user who typed this prompt.
    Write a minimum of two outcome items, each with weight 3. Write these items from the
    side of the user, not from the side of the skill. For example, "The questions asked
    are the ones whose answers change the work" is an outcome. "asks questions" is not
    an outcome.
- `pass` and `partial` tell the judge concretely what to look for.
- `weight`: 3 = core purpose, 2 = important, 1 = nice to have.
- `appliesWhen`: use this field for rules that apply only sometimes, for example "the
  user adds a note to a reply". When the condition is false, the judges mark the item
  n/a.
- `source`: the heading, the rule number, or a short quote from SKILL.md that the item
  comes from.

Rules for the rubric:

- Make each item checkable from the capture alone. The capture is the transcript and the
  files that the run wrote. Do not grade steps that the output cannot show ("reads the
  code first").
- Write one claim in each item, with no overlaps. If two items always pass or fail
  together, make the two items one item.
- The items are also the units that the similarity judges compare. Thus, each item must
  name one aspect of the output that you can align across runs.
- Guard against circularity. A rubric that only restates the claims of the skill passes
  the skill by construction. The outcome items are the counterweight: the outcome items
  ask if the user got what the user needed.

## Phase 2: Test prompts (new suite only)

Write N prompts (default 10), P01, P02, …. Each prompt is what a user types after
`/<skill>`:

- **Suitable.** Each prompt is in the scope of the skill. This is not a trigger test.
- **Varied.** Spread the prompts across axes, and record the `axis` of each prompt. The
  axes are typical, minimal or terse, rich or long input, ambiguous, unusual domain, and
  edge-but-valid. An edge-but-valid prompt is at the limits of the skill, for example a
  request that needs exactly one question, or a request near a stated cap.
- **Self-contained.** Put any text that the skill needs in the prompt. Run worktrees can
  start from the default branch of the repo, not from your current checkout. Thus,
  refer only to files that are committed on that branch. Do not use a network,
  connectors, or secrets, unless the skill exists to use them.
- **`exercises`:** one line that tells which parts of the skill the prompt tests.
- **`replies`** (interactive skills): the answers that a plausible user gives to this
  prompt, in the reply format of the skill. Give enough replies to reach the end: the
  usual number of turns, plus a final "yes, go". Each repeat uses the same list in the
  same order. Thus, make each reply meaningful for any question that it lands on: option
  letters, "yes", "go ahead".

  When the list has no more replies, the run agents pick the recommended option. If no
  option is recommended, the run agents reply "you decide". For skills that do not ask
  questions, leave the list empty.
- **Order.** Put the most varied prompts first. Runs use the first M prompts. Thus,
  P01-P03 must already cover three different axes, with typical first.

## Phase 3: Review gate (new suite only)

Write `evals/<skill>/suite.json`, and check it against `references/suite.schema.json`.
Then show the user these items, in a compact form:

- The structure summary and the S elements.
- The rubric as a table: id, kind, weight, criterion, source.
- The prompts: id, axis, prompt (shortened), and number of replies. Mark the first M
  prompts as the sample of this run.
- The agent roles in effect (the preset and any overrides), and the agent estimate for
  these roles (see "Agent roles").

Ask: "Reply `go`, or tell me what to change (for example `drop R4`, `make P03 harder`,
`R2 weight 3`)." Apply the edits to `suite.json`, and show only the changed rows. Do not
start runs until the user says go.

On later runs, a saved suite skips this gate, because the user already reviewed its
rubric. Do not skip the model question in Phase 3b.

## Phase 3b: Models (every run)

The model is the biggest variable in an eval. Thus, ask which models to use before each
run, for a new suite and for a saved suite. Skip the question only when the
`--agent role.model=…` flags of this invocation name a model for all four roles.

Ask two questions in one message. Mark the current setting as the default. The current
setting comes from `evals/agents.json`, or is `session`.

- **The skill's model** (`run.model`): the model whose behaviour you test. Recommend the
  session model, because the skill usually runs on the session model. The exception is
  when the user wants to know how the skill does on a different model.
- **The judges' model** (`grade`, `compare`, `cross`): recommend the same model as the
  runs, or a stronger model. A weaker judge adds its own noise. This noise lowers the
  stability and makes the grade less clear.

Put the answers into the agent roles for this run. Offer one time to save the answers to
`evals/agents.json` as the default of the repo. Record the meaning of `session` in the
results: when you know the model name of the session, set `config.sessionModel` to that
name. Scores from runs with different models are not comparable.

## Phase 4: Run and judge

1. **Pick the prompts.** Use the `--use` IDs. If an ID is not in the suite, stop. If
   there is no `--use`, use the first M prompts.
2. **Resolve the agent roles.** Apply the settings in this order:
   1. Start from `evals/agents.json`, if it exists.
   2. Apply `--preset`.
   3. Apply each `--agent role.key=value`. For example, `--agent grade.model=<model>`
      sets `grade.model`.
   4. Apply the answers from Phase 3b.

   Check the result against `references/agents.schema.json`. On a re-run that skips the
   review gate, say these items in one line before the runs start: the preset, the
   models, the overrides in effect, and the agent estimate.
3. **Make the run folder.** `runId` is `date -u +%Y%m%dT%H%M%SZ`. Create
   `evals/<skill>/runs/<runId>/outputs/`. Record the output of `git worktree list`, so
   that Phase 5 can find the worktrees that this run creates.
4. **Call the Workflow tool.** Set `scriptPath` to `references/vet.workflow.js` in the
   directory of this skill. Set `args` to a real JSON object, not a string:

   ```json
   {
     "skill": { "name": "<skill>", "dir": "<abs skill dir>", "file": "<abs SKILL.md>" },
     "suite": { "structure": {…}, "rubric": [ … ], "prompts": [ <selected prompts only> ] },
     "runs": 10,
     "wave": 2,
     "settle": { "delta": 2, "patience": 2, "stop": false },
     "maxTurns": 12,
     "crossPerPrompt": 2,
     "agents": { "preset": "lean", "grade": { "model": "<model>" } }
   }
   ```

   All paths must be absolute, because the run agents work in their own worktrees. The
   Workflow tool accepts only a `scriptPath` in the working directory. Thus, the tool
   refuses the copy that is installed under `~/.claude/skills/`. If the tool refuses the
   path, read the file and give its contents, unchanged, as `script`.

   **Do not edit the script for a run.** The evaluator must vary as little as the skills
   that it scores. Thus, each eval runs the same file.

What the script does:

The repeats of each prompt run in waves of W (default 2). In each wave, these steps
occur:

- **Run (step 2).** One agent runs each (prompt, repeat), with `isolation: 'worktree'`.
  The agent reads the target SKILL.md from the main checkout, so the eval tests the
  uncommitted edits. The agent follows the skill as if the user started the skill with
  the prompt. When the skill waits for the user, the agent gives the scripted replies.
  The agent keeps each file in its worktree, because an isolated agent cannot write
  outside its worktree.

  The agent writes a verbatim capture to `.vet-capture/P01-r03.md` in its worktree, and
  reports the absolute path. The capture holds the transcript and each file that the
  agent created or changed. The skill-facing part of the prompt is the same for each
  repeat. Thus, the differences come from the skill.
- **Grade (step 3).** A rubric judge gives each new run a verdict on each item: met,
  partial, missed, or n/a. The judge gives a verbatim quote as evidence. When the judge
  is not sure between two verdicts, the judge picks the lower verdict. With
  `grade.batch: run`, each run gets its own judge when the run finishes. With `prompt`
  (the default), one judge grades the runs of the wave, and grades each run separately.
- **Compare (step 4).** For each rubric item, a similarity judge puts each new run into
  one of the groups so far, or opens a new group. The judge compares the new run with
  one example run from each group. Then the judge classifies the item across all runs
  so far: identical, equivalent, minor drift, major drift, or contradictory. The judge
  judges sameness, not quality. When the judge is not sure, the judge picks the less
  similar class.

  The script keeps the groups. If a judge does not place a run, the script offers the
  run again in the next wave.
- **Settle.** After all the prompts finish the wave, the script records the running
  quality, stability, and overall grade. The script also logs one line, for example
  `wave 3/5 (6 of 10 runs per prompt): quality 86.1 · stability 71.0 · overall 78.2 (C) ·
  moved +0.8 · settled`. See "Settling".

After the last wave, these steps occur:

- **Cross.** For structure items, a cross-prompt judge compares the first two usable
  runs of each prompt. The judge ignores the content and compares only the shape.
- **Tally.** The script itself counts the groups of each item, for example `7 / 3 of
  10`. The script flags each judgement whose groups do not place each run exactly one
  time.
- **Score (step 5).** The script calculates the scores with plain arithmetic. No judge
  takes part. See "Scoring".

All these steps run in parallel. Each prompt moves through its waves independently. The
judges of a wave go into the queue ahead of the runs of the next wave, so that the grade
stays current. The Workflow runtime runs a maximum of min(16, CPU cores − 2) agents at
the same time, and puts the other agents in a queue. For example, the runtime runs 14
agents on a 16-core machine, but only 2 agents on a 4-core machine. Thus, check `nproc`
before you promise a finish time.

The script omits some runs from the scores, and lists these runs under `excluded`. An
excluded run has one of these conditions:

- The agent died, or the agent did not execute the skill (`not_run`).
- The grader died, or the grader skipped the run.
- The capture is missing, or the capture is not verbatim.

The script lists each missing similarity judgement under `lostJudges`. A judgement is
missing when the judge died or skipped an item. The script does not count an excluded
run or a lost judgement as a pass or as a fail.

## Phase 5: Report

1. Record `generatedAt` (`date -u +%Y-%m-%dT%H:%M:%SZ`) and `suiteSha256`
   (`sha256sum evals/<skill>/suite.json`).
2. **Collect the captures.** The capture of each run is in the worktree of that run, at
   the path in `runs[].capture`. Copy each capture to `outputs/<P01-r03>.md` with a
   shell loop. Do not read the captures into your context. Then point `runs[].capture`
   at the copy.
3. Write `results.json` as `{ skill, skillSha256, suiteSha256, runId, generatedAt, ...workflowResult }`.
   Do not change the return value of the workflow, except the capture paths. Add
   `config.sessionModel` from Phase 3b. If a validator is available (for example, the
   `jsonschema` package of Python), check `results.json` against
   `references/results.schema.json`.
4. Write `report.md` from `references/report-template.md`. Write only two parts yourself:
   the verdict and "What to fix". Base the two parts on the evidence in the results.
   Before you suggest fixes, read the captures of the worst items.
5. Run `git worktree list` again, and compare the output with the list from Phase 4.
   The runtime puts worktrees under `.claude/worktrees/`. Each run leaves its worktree,
   because the worktree holds the capture. After you copy the captures, list the new
   worktrees and offer to remove them. Do not remove anything without a yes from the
   user. If `.claude/worktrees/` is not in `.gitignore`, recommend that the user adds
   the folder to `.gitignore`.
6. Reply in a few lines. Give these items:
   - The three scores and the grade.
   - If the grade settled, and when.
   - The weakest item and the least stable item, in plain words.
   - The path to `report.md`.

   If an earlier run has the same `suiteSha256`, agent roles, and models, also give the
   change in each score since that run. Do not use a run with a different suite version
   as a baseline.

## Agent roles

Four roles do the work. Each role can have its own settings:

- `model`: `session` (the default) uses the model of the session. Any other value is a
  model alias or a model id that the harness accepts.
- `effort`: a value from `low` to `max`, or `session`.
- `agentType`: a custom subagent type.

The three judge roles also have `batch`. The `batch` setting tells how much work one
agent does.

| Role | Does | `batch` options |
|---|---|---|
| `run` | Executes the skill, with one agent for each (prompt, repeat) | none |
| `grade` | Gives the rubric verdicts | `run`: one judge for each run · `prompt`: one judge for each prompt in each wave |
| `compare` | Judges the similarity across the repeats of a prompt | `item`: one judge for each (prompt, item) in each wave · `prompt`: one judge for each prompt in each wave · `merged`: the grade judge of each prompt also compares |
| `cross` | Compares the structure across prompts | `item`: one judge for each structure item · `all`: one judge |

The presets set the batching. The agent counts in this table are maximums for
3 prompts × 10 runs, 10 rubric items, and 3 structure items. The table gives the counts
for waves of 2 (the default), and for one wave (`--wave 10`, judged one time at the end):

| Preset | grade | compare | cross | Agents, waves of 2 | Agents, one wave |
|---|---|---|---|---|---|
| `thorough` | run | item | item | 213 | 93 |
| `lean` (default) | prompt | prompt | all | 61 | 37 |
| `minimal` | prompt | merged | all | 46 | 34 |

Waves add judges. But each judge reads only the new runs and one example from each
group. Thus, the quantity of reading grows much less than the agent count.

Set the roles for all of the repo in `evals/agents.json`, or for one run with flags:

```json
{ "preset": "lean", "run": { "model": "session" }, "grade": { "model": "<model>", "effort": "low" } }
```

```
/vet quiz --preset thorough --agent compare.model=<model> --agent cross.effort=low
```

Remember these trade-offs:

- The 30 runs are the measurement, and usually the biggest cost. A change to
  `run.model` changes what you test, not only the cost. Keep `run.model` at `session`,
  unless you want to test the skill on a different model.
- Bigger batches give fewer agents and fewer reads, but each judge holds more at the
  same time. A per-item judge examines one thing across ten outputs. A per-prompt judge
  examines everything. If a per-prompt judge dies, the eval loses all the grades or
  comparisons of that prompt.
- `merged` saves the most. But the same judge grades and then compares, so the grades
  of the judge can colour its sense of sameness.
- Cheaper judge models add judge noise, and this noise appears as lower stability. If
  the stability decreases after a switch, re-run one time with `thorough` to check.

## Settling

The grade settles when more runs complete. After all the prompts finish a wave, the
script records the running quality, stability, and overall grade in `trajectory`. The
stability in `trajectory` is within-prompt only. The final score also includes the
cross-prompt check.

- **Settled** means that the overall score moved by 2 points or less in each of the last
  2 waves, and kept the same letter. With waves of 2 over 10 runs, the earliest wave
  that can settle is wave 3, at 6 runs per prompt.
- **Not settled** at the end means that more runs will probably still move the grade.
  Say so, and suggest a re-run with more `--runs`.
- **`--stop-when-settled`** starts no new wave after the grade settles. This flag saves
  runs on a steady skill. The flag is off by default, because an early stop can miss
  rare drift. For example, a skill that drifts one time in five runs has about a
  one-in-four chance to show no drift in its first six runs.

## Scoring

| Verdict | Value | | Similarity class | Value |
|---|---|---|---|---|
| met | 1 | | identical | 1.0 |
| partial | 0.5 | | equivalent | 0.9 |
| missed | 0 | | minor_drift | 0.6 |
| n/a | omitted | | major_drift | 0.25 |
| | | | contradictory | 0 |

- **Quality** = 100 × Σ(weight × verdict value) ÷ Σ(weight), over each applicable
  (run, item) pair in the usable runs.
- **Stability** = 100 × Σ(weight × class value) ÷ Σ(weight), over each similarity
  judgement. The repeats of each prompt count as one scope for each item. The
  cross-prompt check counts as one more scope for structure items.
- **Overall** = √(quality × stability). Grades: A ≥ 90, B ≥ 80, C ≥ 70, D ≥ 60, F below.
- **Confidence** is `low` when fewer than 80% of runs are usable.
- **Tallies** do not change the score. Each judgement also carries the group sizes that
  the script counted (`7 / 3 of 10`), and `agreement`, the share of runs in the largest
  group. The report shows these values next to the class, so that you can see how a
  drift splits.

Scores are comparable only between runs with these same items:

- The same `suiteSha256`.
- The same agent roles and models (`config.agents` and `config.sessionModel` in
  results.json).
- The same wave size.

Judges on a different model or with a different batch setting give different scores.

## Limits

- Run agents are Workflow subagents with an instruction to follow the SKILL.md. Run
  agents are not fresh `claude` sessions. Thus, a run is close to real use, but not
  identical to how the harness loads a skill.
- Skills that start their own Workflow (for example `/probe` and `/vet`) cannot run in a
  run agent, because workflows do not nest. The runs of these skills report the status
  `blocked`.
- Skills that need a running app, a connector, or a binary that the environment does
  not have also report `blocked`. The judges still grade these runs, so the report shows
  how much each run completed.
- The harness can relay the latest message of the user to each workflow agent. If that
  message is about the eval ("quit and restart it"), the agents can think that the
  message is for them. Each agent prompt says that the message was for the launching
  session, and that the launching session already acted on the message. If many runs
  still report `not_run`, the eval is not valid. Correct the cause and re-run the eval.
  Do not report the scores.
- Judges are models, and the noise of the judges lands in the scores. The "choose the
  lower one when torn" rules reduce this noise. A re-run of the same suite shows how
  much noise remains.
- Scripted replies keep the user side fixed. If the questions of a skill vary between
  runs, the skill gets the same reply to different questions. The eval correctly shows
  this result as drift.
- The run agents use the scripted replies in order, whatever the skill asks. A spare
  letter reply can land on a confirmation question. Thus, keep each reply list to the
  questions that you are sure of. Let the recommended-option fallback cover the other
  questions.

## Example

```
/vet quiz
```

There is no suite yet. Thus, `vet` reads `quiz/SKILL.md` and writes the structure (one
card per turn, a `[✓]` echo, a final resolved view). Then `vet` writes a 10-item rubric.
Two examples are R3 "exactly one option marked (recommended)" and R8 "questions asked
are the ones whose answers change the work". Then `vet` writes 10 prompts, from a terse
one-liner to a seven-decision project, each with scripted letter replies. You review the
suite and reply `go`.

After thirty runs, `evals/quiz/runs/20260927T101500Z/report.md` shows quality 88,
stability 74, and overall 80.7 (B). The report flags R5 (the question order), which
drifts. Of the 10 runs, 6 ask about the audience first, and 4 ask about the scope first.
The report suggests a more concrete form of the "most load-bearing first" rule in Flow
step 2.
