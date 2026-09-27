---
name: vet
description: >
  Writes and runs an eval for another skill, then scores it on two axes: how well its
  output meets a rubric drawn from the skill itself (quality), and how little its
  output changes between runs (stability). Reads the target SKILL.md to extract the
  expected output structure and a rubric, writes varied test prompts (with scripted
  user replies for interactive skills), runs a sample of them many times each in
  isolated git worktrees via a Workflow, grades every run with a rubric judge, and has
  similarity judges classify and tally each rubric item by how much it changed across
  repeats and, for structure items, across prompts. Runs go in waves and the grade is
  recorded after each one, so you can watch it settle. Asks which models to use before
  every eval. Each agent role (run, grade,
  compare, cross) can take its own model, effort and batching, via presets or
  overrides, to trade cost against focus. Saves the suite to evals/<skill>/ so later
  runs are comparable. Use when the user says "/vet", asks to "eval a skill",
  "test this skill", "score my skill", "how consistent is this skill", or wants to
  check a skill before trusting it.
---

# Vet: Skill Evaluator

## Purpose

A good skill does two things. Its output meets the promises in its own SKILL.md, and
the same input gives much the same output every time. `/vet` measures both:

- **Quality (0-100):** the weighted share of the rubric met, across every run.
- **Stability (0-100):** how similar the outputs are, rubric item by rubric item,
  across repeated runs of the same prompt, plus structure across different prompts.
- **Overall (0-100):** √(quality × stability). A skill that is reliably wrong scores
  low, and so does one that is right but erratic. Neither axis can hide the other.

The pipeline: extract structure and rubric → write test prompts → run each
sampled prompt many times in isolation → grade every run → judge similarity per
rubric item → score.

## Usage

```
/vet <skill> [--prompts N] [--sample M] [--runs R] [--use P02,P07] [--regen]
             [--wave W] [--stop-when-settled]
             [--preset thorough|lean|minimal] [--agent role.key=value …]
```

| Argument | Default | Meaning |
|---|---|---|
| `<skill>` | required | Skill name, or a path to its folder or SKILL.md |
| `--prompts N` | 10 | Test prompts to write when creating a suite |
| `--sample M` | 3 | Prompts to run this time (the first M in the suite) |
| `--runs R` | 10 | Repeats of each sampled prompt; at least 2 |
| `--use` | none | Run these prompt ids instead of the first M |
| `--regen` | off | Rebuild the suite even if one exists |
| `--wave W` | 2 | Repeats per prompt per wave; the grade is updated after each wave. `--wave R` judges once at the end |
| `--stop-when-settled` | off | Start no new wave once the grade has settled; see Settling |
| `--preset` | `lean` | How much work each judge takes on; see Agent roles |
| `--agent role.key=value` | none | Override one role setting for this run, e.g. `--agent grade.model=<model>`; repeatable |

With the defaults (3 prompts × 10 runs in waves of 2, `lean`) and a 10-item rubric, a
run spawns up to 61 agents: 30 runs, 15 rubric judges and 15 similarity judges (one
of each per prompt per wave) and 1 cross-prompt judge. See Agent roles and Settling
to trade cost against focus.

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

`evals/` sits at the root of the git repo you run `/vet` from, beside the skill
folders rather than inside them, so a skill folder stays clean to copy into
`~/.claude/skills/`. Commit `suite.json`: re-runs reuse it, which is what makes scores
comparable over time.

## Phase 0: Resolve

1. **Find the skill.** Use the path if one was given. Otherwise try, in order,
   `./<name>/SKILL.md`, `.claude/skills/<name>/SKILL.md`, `~/.claude/skills/<name>/SKILL.md`.
   Stop and ask if it's missing or more than one matches.
2. **Find the repo root** with `git rev-parse --show-toplevel`. Worktree isolation
   needs git. If this isn't a git repo, stop and say so.
3. **Fingerprint the skill:** `sha256sum` of its SKILL.md.
4. **Check for a saved suite** at `evals/<skill>/suite.json`. If it exists and there's no
   `--regen`, load it and go straight to Phase 3b (models). If its `skillSha256` differs from
   today's, say so in one line and carry on. The suite still works, and keeping it
   keeps scores comparable. `--regen` rebuilds it but starts a new baseline.

## Phase 1: Structure and rubric (new suite only)

Read the target SKILL.md in full, plus every file it points to (references, templates,
schemas). Then write two things.

**Structure.** What the output looks like, as SKILL.md specifies it:
- a one- or two-sentence `summary` with the turn pattern (single reply, or multi-turn
  and how turns alternate) and the overall shape;
- `elements` S1, S2, …: each required section, block, format, file, or turn rule, in
  order. Only what SKILL.md states or plainly implies. Don't invent structure.

**Rubric.** 6-12 items, R1, R2, …, each one checkable claim about the output:

- `kind` is one of:
  - `structure`: the shape of the output. Each covers one or a few closely related
    S elements (`structureRef`). Every S element is covered by some structure item.
  - `behavior`: a process rule you can see in the output, e.g. "one question per turn"
    or "marks exactly one option recommended". The skill's "don't" list is a good source.
  - `outcome`: whether the output does its job for the user who typed this prompt. At
    least two, weight 3. Write these from the user's side, not the skill's. "The
    questions asked are the ones whose answers change the work" is an outcome; "asks
    questions" is not.
- `pass` and `partial` say concretely what the judge should look for.
- `weight`: 3 = core purpose, 2 = important, 1 = nice to have.
- `appliesWhen` for rules that only apply sometimes (e.g. "the user adds a note to a
  reply"). Judges mark the item n/a when the condition is false.
- `source`: the heading, rule number, or a short quote from SKILL.md it comes from.

Rules for the rubric:
- Checkable from the capture alone, meaning the transcript and the files written. Don't
  grade steps the output can't show ("reads the code first").
- One claim per item, no overlaps. Two items that always pass or fail together are
  one item.
- The items are also the units the similarity judges compare, so each should name one
  aspect of the output that can be lined up across runs.
- Guard against circularity. A rubric that just restates the skill's own claims will
  pass the skill by construction. The outcome items are the counterweight: they ask
  whether the user got what they needed.

## Phase 2: Test prompts (new suite only)

Write N prompts (default 10), P01, P02, …, each what a user would type after
`/<skill>`:

- **Suitable.** Every prompt is in scope for the skill. This is not a trigger test.
- **Varied.** Spread them across axes and record each one's `axis`: typical, minimal or
  terse, rich or long input, ambiguous, unusual domain, and edge-but-valid (right at
  the skill's own limits, e.g. a request needing exactly one question, or one near a
  stated cap).
- **Self-contained.** Put any text the skill needs inline. Run worktrees can start from
  the repo's default branch rather than your current checkout, so refer only to files
  committed there. Avoid anything needing network, connectors or secrets unless the
  skill exists to use them.
- **`exercises`:** one line on which parts of the skill the prompt tests.
- **`replies`** (interactive skills): the answers a plausible user would give to this
  prompt, in the skill's reply format, enough to reach the end (the usual number of
  turns plus a final "yes, go"). Every repeat uses the same list in order, so keep
  replies meaningful whatever question they land on: option letters, "yes", "go
  ahead". When the list runs out, run agents pick the recommended option, or reply
  "you decide" if nothing is recommended. Leave it empty for skills that never ask.
- **Order.** Put the most varied first. Runs use the first M prompts, so P01-P03 should
  already cover three different axes, typical first.

## Phase 3: Review gate (new suite only)

Write `evals/<skill>/suite.json` and check it against `references/suite.schema.json`.
Then show the user, compactly:

- the structure summary and S elements;
- the rubric as a table: id, kind, weight, criterion, source;
- the prompts: id, axis, prompt (shortened), number of replies, with the first M
  marked as this run's sample;
- the agent roles in effect (preset plus any overrides) and the agent estimate for
  them (see Agent roles).

Ask: "Reply `go`, or tell me what to change (e.g. `drop R4`, `make P03 harder`,
`R2 weight 3`)." Apply edits to `suite.json` and show the changed rows only. Don't
start runs until the user says go. A saved suite skips this gate on later runs, since
its rubric was already reviewed. The model question below is never skipped.

## Phase 3b: Models (every run)

The model is the biggest variable in an eval, so ask which models to use before every
run, whether the suite is new or saved. Skip the question only when this invocation's
own `--agent role.model=…` flags name a model for all four roles.

Ask two things, in one message, with the current setting (from `evals/agents.json`, or
`session`) marked as the default:
- **The skill's model** (`run.model`): the model whose behaviour you are testing.
  Recommend the session model, since that is how the skill normally runs, unless the
  user wants to know how the skill does on another model.
- **The judges' model** (`grade`, `compare`, `cross`): recommend the same model as the
  runs or stronger. A weaker judge adds its own noise, which lowers stability and
  blurs the grade.

Put the answers into the agent roles for this run, and offer once to save them to
`evals/agents.json` as the repo default. Record what `session` means in results: set
`config.sessionModel` to the session's model name when you know it. Scores from runs
with different models are not comparable.

## Phase 4: Run and judge

1. **Pick the prompts:** the `--use` ids (stop if any isn't in the suite), else the
   first M.
2. **Resolve the agent roles.** Start from `evals/agents.json` if it exists, apply
   `--preset`, then each `--agent role.key=value` (`--agent grade.model=<model>` sets
   `grade.model`), then the answers from Phase 3b. Check the result against
   `references/agents.schema.json`. On a re-run that skips the review gate, say in one
   line which preset, models and overrides are in effect and the agent estimate before
   starting.
3. **Make the run folder.** `runId` is `date -u +%Y%m%dT%H%M%SZ`. Create
   `evals/<skill>/runs/<runId>/outputs/`. Note the output of `git worktree list` so
   Phase 5 can tell which worktrees this run created.
4. **Call the Workflow tool** with `scriptPath` set to `references/vet.workflow.js` in
   this skill's own directory, and `args` as a real JSON object (not a string):

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

   All paths must be absolute: run agents work from inside their own worktrees. The
   Workflow tool only accepts a `scriptPath` inside the working directory, so it
   refuses the copy installed under `~/.claude/skills/`. When that happens, read the
   file and pass its contents, unchanged, as `script`.
   **Never edit the script for a run.** The evaluator must vary as little as the
   skills it scores, so every eval runs the same file.

What the script does:

Each prompt's repeats run in waves of W (default 2). For each wave:

- **Run (step 2).** One agent per (prompt, repeat), each with `isolation: 'worktree'`.
  It reads the target SKILL.md from the main checkout, so uncommitted edits are what
  gets tested. It follows the skill as if invoked with the prompt and plays the
  scripted replies whenever the skill waits for the user. It keeps every file inside
  its worktree, because isolated agents can't write outside it. It writes a verbatim
  capture (transcript plus any files it created or changed) to
  `.vet-capture/P01-r03.md` there and reports the absolute path. The skill-facing part
  of the prompt is identical for every repeat, so differences come from the skill.
- **Grade (step 3).** A rubric judge gives every new run a verdict of met, partial,
  missed or n/a on each item, with a verbatim quote as evidence, and picks the lower
  verdict when torn. With `grade.batch: run` each run gets its own judge as soon as it
  finishes; with `prompt` (the default) one judge grades the wave's runs, each on its
  own.
- **Compare (step 4).** A similarity judge places each new run into the groups built
  so far for each rubric item, or opens a new group. It compares against one example
  run per group, then classifies the item across all runs so far: identical,
  equivalent, minor drift, major drift or contradictory. It judges sameness, not
  quality, and picks the less similar option when torn. The script keeps the groups,
  so a run a judge fails to place is offered again next wave.
- **Settle.** Once every prompt has finished the wave, the script records the running
  quality, stability and overall grade and logs one line, e.g. `wave 3/5 (6 of 10 runs
  per prompt): quality 86.1 · stability 71.0 · overall 78.2 (C) · moved +0.8 ·
  settled`. See Settling.

After the last wave:

- **Cross.** For structure items, a cross-prompt judge compares the first two usable
  runs of each prompt, ignoring content and comparing only shape.
- **Tally.** The script counts each item's groups itself, e.g. `7 / 3 of 10`, and
  flags any judgment whose groups don't place every run exactly once.
- **Score (step 5).** Plain arithmetic in the script, with no judge involved. See
  Scoring.

It all runs in parallel. Prompts move through their waves independently, and each
wave's judges are queued ahead of the next wave's runs so the grade keeps up. The
Workflow runtime runs up to min(16, CPU cores − 2) agents at once and queues the
rest: 14 on a 16-core machine, only 2 on a 4-core one, so check `nproc` before
promising a finish time.

Runs whose agent died or never executed the skill (`not_run`), whose grader died or
skipped them, or whose capture is missing or not verbatim are left out of the scores
and listed under `excluded`.
Similarity judgments that are missing (the judge died or skipped an item) are listed
under `lostJudges`. Neither is ever counted as a pass or a fail.

## Phase 5: Report

1. Stamp `generatedAt` (`date -u +%Y-%m-%dT%H:%M:%SZ`) and `suiteSha256`
   (`sha256sum evals/<skill>/suite.json`).
2. **Collect the captures.** Each run's capture is in its own worktree, at the path
   in `runs[].capture`. Copy each one to `outputs/<P01-r03>.md` with a shell loop
   (don't read them into your context), then point `runs[].capture` at the copy.
3. Write `results.json` as `{ skill, skillSha256, suiteSha256, runId, generatedAt, ...workflowResult }`.
   Keep the workflow's return value unchanged apart from the capture paths, and add
   `config.sessionModel` from Phase 3b. Check it against
   `references/results.schema.json` if a validator is to hand, e.g. Python's
   `jsonschema`.
4. Write `report.md` from `references/report-template.md`. The verdict and "What to fix"
   are the only parts you write yourself, and both must rest on the evidence in the
   results. Read the captures behind the worst items before suggesting fixes.
5. Run `git worktree list` again and compare it with the list from Phase 4. The runtime
   puts worktrees under `.claude/worktrees/`, and every run leaves its worktree behind
   because it holds the capture. Once the captures are copied, list the new worktrees
   and offer to remove them. Remove nothing without a yes. If `.claude/worktrees/`
   isn't in `.gitignore`, suggest adding it.
6. Reply in a few lines: the three scores and grade, whether and when the grade
   settled, the weakest item and the least stable one in plain words, and the path to
   `report.md`. If there is an earlier run with the same `suiteSha256`, agent roles and
   models, add the change in each score since then. A run graded under a different
   suite version is never a baseline.

## Agent roles

Four roles do the work. Each can take its own `model` (`session`, the default, inherits
the session's model; otherwise any model alias or id the harness accepts), `effort`
(`low` to `max`, or `session`) and `agentType` (a custom subagent type). The three
judge roles also take `batch`, which sets how much work one agent does.

| Role | Does | `batch` options |
|---|---|---|
| `run` | Executes the skill, one agent per (prompt, repeat) | none |
| `grade` | Rubric verdicts | `run`: one judge per run · `prompt`: one judge per prompt per wave |
| `compare` | Similarity across repeats of a prompt | `item`: one judge per (prompt, item) per wave · `prompt`: one judge per prompt per wave · `merged`: the per-prompt grade judge also compares |
| `cross` | Structure across prompts | `item`: one judge per structure item · `all`: one judge |

Presets set the batching. Agent counts are upper bounds for 3 prompts × 10 runs, 10
rubric items and 3 structure items, in waves of 2 (the default) and in one wave
(`--wave 10`, judged once at the end):

| Preset | grade | compare | cross | Agents, waves of 2 | Agents, one wave |
|---|---|---|---|---|---|
| `thorough` | run | item | item | 213 | 93 |
| `lean` (default) | prompt | prompt | all | 61 | 37 |
| `minimal` | prompt | merged | all | 46 | 34 |

Waves add judges, but each one reads only the new runs plus one example per group,
so the reading grows far less than the agent count.

Set roles for the whole repo in `evals/agents.json`, or for one run with flags:

```json
{ "preset": "lean", "run": { "model": "session" }, "grade": { "model": "<model>", "effort": "low" } }
```

```
/vet quiz --preset thorough --agent compare.model=<model> --agent cross.effort=low
```

Trade-offs to keep in mind:
- The 30 runs are the measurement and usually the biggest cost. Changing
  `run.model` changes what you are testing, not just what it costs. Leave it at
  `session` unless you mean to test the skill on another model.
- Bigger batches mean fewer agents and fewer reads, but each judge holds more at once.
  A per-item judge looks at one thing across ten outputs. A per-prompt judge looks at
  everything, and one dead judge loses that whole prompt's grades or comparisons.
- `merged` saves the most, but the same judge grades and then compares, so its grades
  can colour its sense of sameness.
- Cheaper judge models add judge noise, which shows up as lower stability. If
  stability drops after a switch, re-run once with `thorough` to check.

## Settling

The grade settles as runs come in. After each wave, once every prompt has finished it,
the script records the running quality, stability and overall grade in `trajectory`.
Stability here is within-prompt only; the final score also includes the cross-prompt
check.

- **Settled** means the overall score moved no more than 2 points in each of the last
  2 waves and kept the same letter. With waves of 2 over 10 runs, the earliest it can
  settle is wave 3, at 6 runs per prompt.
- **Not settled** at the end means more runs would likely still move the grade. Say so,
  and suggest a re-run with more `--runs`.
- **`--stop-when-settled`** starts no new wave once the grade has settled, which saves
  runs on a steady skill. It is off by default because a skill that drifts once in
  five runs has about a one-in-four chance of showing no drift in its first six, so
  stopping early can miss rare drift.

## Scoring

| Verdict | Value | | Similarity class | Value |
|---|---|---|---|---|
| met | 1 | | identical | 1.0 |
| partial | 0.5 | | equivalent | 0.9 |
| missed | 0 | | minor_drift | 0.6 |
| n/a | left out | | major_drift | 0.25 |
| | | | contradictory | 0 |

- **Quality** = 100 × Σ(weight × verdict value) ÷ Σ(weight), over every applicable
  (run, item) pair in the usable runs.
- **Stability** = 100 × Σ(weight × class value) ÷ Σ(weight), over every similarity
  judgment. Each prompt's repeats count as one scope per item, and cross-prompt counts
  as one more scope for structure items.
- **Overall** = √(quality × stability). Grades: A ≥ 90, B ≥ 80, C ≥ 70, D ≥ 60, F below.
- **Confidence** is `low` when fewer than 80% of runs were usable.
- **Tallies** don't enter the score. Each judgment also carries the group sizes the
  script counted (`7 / 3 of 10`) and `agreement`, the share of runs in the largest
  group. The report shows them next to the class so you can see how a drift splits.

Scores are comparable only between runs with the same `suiteSha256`, the same agent
roles and models (`config.agents` and `config.sessionModel` in results.json), and the
same wave size. Judges on a different model or batch setting score differently.

## Limits

- Run agents are Workflow subagents told to follow the SKILL.md, not fresh `claude`
  sessions. They are close to real use but not identical to how the harness loads a
  skill.
- Skills that launch their own Workflow (e.g. `/probe`, `/vet`) can't run inside a run
  agent, because workflows don't nest. Those runs come back `blocked`.
- Skills that need a running app, a connector, or a binary the environment lacks come
  back `blocked`. They are still graded, so the report shows what they managed.
- The harness can relay the user's latest message to every workflow agent. If that
  message is about the eval ("quit and restart it"), agents may take it as addressed
  to them. Every agent prompt says the message was for the launching session, which
  has already acted on it. If many runs still come back `not_run`, the eval is
  invalid: fix the cause and re-run rather than reporting scores.
- Judges are models, and their own noise lands in the scores. The "choose the lower
  one when torn" rules reduce it. Re-running the same suite shows how much remains.
- Scripted replies keep the user side fixed. A skill whose questions vary between runs
  will get the same reply to different questions, which shows up, rightly, as drift.
- Scripted replies are used in order, whatever the skill asks. A spare letter reply can
  land on a confirmation question, so keep reply lists to the questions you are sure
  of and let the recommended-option fallback cover the rest.

## Example

```
/vet quiz
```

There is no suite yet, so `vet` reads `quiz/SKILL.md` and writes the structure (one
card per turn, a `[✓]` echo, a final resolved view). It writes a 10-item rubric, e.g.
R3 "exactly one option marked (recommended)" and R8 "questions asked are the ones
whose answers change the work". It writes 10 prompts from a terse one-liner to a
seven-decision project, each with scripted letter replies. You review and reply `go`.
Thirty runs later, `evals/quiz/runs/20260927T101500Z/report.md` shows quality 88,
stability 74, overall 80.7 (B). The report flags R5, the question order, which drifts:
6 of 10 runs ask about audience first and 4 ask about scope first. It suggests making
the "most load-bearing first" rule in Flow step 2 concrete.
