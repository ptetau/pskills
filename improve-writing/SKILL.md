---
name: improve-writing
description: >
  Rewrites a text so that it obeys the writing guidelines: ASD-STE100 Simplified Technical
  English, the local-references rule, and the described-IDs rule. Works on skills, agent
  prompts, specs, plans, reports, and web pages, and keeps the meaning, the code, and
  quoted text. For a skill, records each behaviour and makes sure that the rewrite keeps it.
  Then runs /vet on the two versions to find a loss of effectiveness. Use
  when the user says "/improve-writing" or asks to "improve the writing", "rewrite this in
  STE", or "apply the writing guidelines". Also use to "make this plain English", or to
  rewrite a skill with no regression.
---

# Improve writing

## Purpose

This skill writes a text again so that the text obeys the writing guidelines in
`references/writing-guidelines.md`. The guidelines have three parts:

- The rules of ASD-STE100 Simplified Technical English (STE).
- The local-references rule: a pronoun refers only to a noun in the same paragraph.
- The described-IDs rule: each ID has a short description in the same sentence.

A rewrite must not change what the text does. For a document, the facts must stay the
same. For a skill or a prompt, the behaviour must stay the same. Thus, this skill records
the behaviours before the rewrite and examines them after the rewrite. For a skill, the
skill also runs `/vet` on the two versions and compares the scores.

## Usage

```
/improve-writing <path> [<path> …] [--no-eval] [--declarative] [--dictionary PATH]
```

| Argument | Default | Meaning |
|---|---|---|
| `<path>` | necessary | A file, or a skill folder. A skill folder includes `SKILL.md` and its Markdown references. |
| `--no-eval` | off | For a skill, do not run `/vet`. The report then says that the effectiveness is not measured. |
| `--declarative` | off | For a skill, rewrite it in the declarative form of `AGENTS.md`, inside its word budget. The section "Declarative mode" gives the changes. |
| `--dictionary PATH` | `STE100_DICTIONARY` | Your copy of the ASD-STE100 standard, as a PDF or a text file. |

## What changes and what stays

These items stay the same. Do not change them:

- The meaning of each sentence, and each fact, number, default, and limit.
- The strength of each statement. Advice stays advice: "should" does not become "must".
  A permission stays a permission: "may" does not become "can". A "never" stays a ban.
- Code, commands, file paths, identifiers, error codes, field names, and values.
- Quoted text, for example the words of a user or an example of bad text.
- The name of a skill, and the trigger phrases in its `description`.
- Text that a script reads, for example a heading that a checker looks for. Phase 1 finds
  this text.
- Labels that other text refers to, for example "Phase 3b" or "step 2".

These items change:

- Long sentences become short sentences, or a vertical list.
- Instructions become imperative sentences, with one instruction in each sentence.
- A condition moves to the start of its instruction.
- A pronoun that refers to an earlier paragraph becomes the full noun.
- Each ID gets a short description.
- Words from the linter list become plainer words.
- Passive verbs become active verbs, and complex verb forms become simple tenses.

## Phase 0: Resolve

1. Find each file. For a skill folder, use `SKILL.md` and each Markdown file in the
   folder. Do not change scripts. Code comments are outside the scope of this skill.
2. Put each file in one of two groups:
   - Behaviour text: a skill, an agent definition, a system prompt, or a template that
     gives instructions to an agent.
   - Documents: all other text.
3. Find the STE dictionary. Use `--dictionary`, or the `STE100_DICTIONARY` environment
   variable. If there is no dictionary, tell the user one time. The standard is free from
   <https://www.asd-ste100.org>. Without the dictionary, the linter does not examine
   words against the STE dictionary.
4. Make sure that the files are committed. The committed version is the baseline.

## Phase 1: Record the baseline (behaviour text only)

1. **Copy the baseline.** Copy the skill folder at the last commit to a temporary folder.
   Keep the name of the folder:

   ```
   mkdir -p "$TMP/baseline" && git archive HEAD <skill> | tar -x -C "$TMP/baseline"
   ```

2. **Write the behaviour inventory.** Read the full skill, and each file that the skill
   refers to. Then write a list of each item that controls the behaviour:
   - When to use the skill, and the trigger phrases.
   - Each argument and its default.
   - Each step, in its order.
   - Each rule, with its strength: each "must", "should", "may", "do not", "always", and
     "never".
   - Each number, limit, threshold, and default.
   - Each part of the output: sections, files, formats, and the order of turns.
   - Each question that the skill asks, and when it asks the question.
   - What the skill does when a step fails.
   - Text that a script reads. Search the scripts of the skill for the strings that the
     scripts match.

   Give each item an ID and a short description, for example "B7 (ask which models to use
   before each run)". Save the list as `inventory.md` in the temporary folder.
3. **Lint the baseline.** Run the linter on each file, and keep the counts for the report:

   ```
   python <this skill>/scripts/check_writing.py FILE [--dictionary PATH]
   ```

## Phase 2: Rewrite

1. Work on one file at a time, and on one section at a time.
2. For each section, decide if the section gives instructions or information. Use the
   rules for instructions (STE section 5) or for descriptive text (STE section 6).
3. Write the section again with the guidelines. The section "What changes and what
   stays" gives the primary changes.
4. Do not add a behaviour, and do not remove a behaviour. Do not add new rules or new
   examples.
5. If a sentence has two possible meanings, do not select one. Ask the user which meaning
   is correct, and record the question in the report.
6. Do not add words that do not give meaning. A rewrite is usually 0.9 to 1.3 times as
   long as the original. If the rewrite is longer, look for text that occurs two times.

## Phase 3: Check

1. **Lint.** Run the linter on each file. Correct each finding. If a finding is incorrect,
   record the reason, for example "a technical noun of the subject". Run the linter again.
   Stop when the linter shows only findings with a recorded reason.
2. **Behaviour inventory.** For each item in `inventory.md`, find the text in the rewrite
   that keeps the item. Mark each item "kept", "changed", or "lost". Correct each changed
   or lost item. For a skill, give this check to a different agent if you can. An agent
   that did not write the rewrite finds more losses.
3. **Scripts.** If the skill has a checker or tests, run them. For example, run the
   checker of a skill on the example output of that skill.
4. **Read the text again.** Examine the rules that a script cannot measure:
   - Each sentence has one topic.
   - Each pronoun refers to one noun in the same paragraph.
   - Each statement is accurate and not abstract.

## Phase 4: Measure the effectiveness (skills only)

A skill can obey every rule and still work less well. `/vet` measures the quality and the
stability of the output of a skill. Run `/vet` on the baseline and on the rewrite, and
compare the two results.

1. **Get a suite.** Use `evals/<skill>/suite.json` if it exists. If it does not exist,
   run `/vet` on the baseline copy to make the suite. Thus, the rubric comes from the old
   version, and the rewrite must keep the promises of the old version.
2. **Use the same settings for the two runs.** Use the same suite, prompts, number of
   runs, wave size, preset, and models. A light setting for each skill is
   `--sample 2 --runs 4 --wave 4 --preset minimal`. That setting starts about 11 agents
   for each run of `/vet`. Ask the model question of `/vet` one time for all skills in the
   request.
3. **Run the baseline.** Give `/vet` the path of the baseline copy. If an earlier result
   has the same suite, settings, and models, use that result. Its `skillSha256`,
   `skillTreeSha256`, and `workflowSha256` must all match the baseline skill and the
   current workflow script.
4. **Run the rewrite.** Give `/vet` the path of the rewritten skill.
5. **Compare.** Run the compare script:

   ```
   python <this skill>/scripts/compare_vet.py BASELINE/results.json REWRITE/results.json
   ```

   The script shows "REGRESSION" in these conditions:
   - The overall score is more than 5 points lower.
   - The pass rate of a weight-3 rubric item is more than 20 points lower.
   - Fewer runs are usable.

   If the two results have a different `workflowSha256`, the script shows "NOT COMPARABLE"
   and exits with code 2. Run `/vet` again with the same workflow script.

   The thresholds are defaults, not measured noise. To measure the noise of the judges,
   run `/vet` on the baseline two times and compare the two results. For this check, the
   script prints the warning "measure the same skill text". This warning is expected.
6. **If there is a regression,** read the captures of the failed items in the two runs.
   Find the change in the text that caused the regression. Correct that text. Then run
   `/vet` on the rewrite again.

`/vet` cannot run a skill that starts its own Workflow, for example `/probe` and `/vet`.
For such a skill, the behaviour inventory is the only check. Write this limit in the
report.

## Phase 5: Report

Give a table with one row for each file or skill:

| File | Linter findings before | Linter findings after | Inventory | Baseline overall | Rewrite overall | Result |
|---|---|---|---|---|---|---|

Under the table, give:

- Each recorded linter exception, with its reason.
- Each inventory item that changed, and how you corrected it.
- Each question about a meaning, from Phase 2.
- The `/vet` result files, and the settings and models of the runs.

Do not commit. The user examines the change first.

## Declarative mode

With `--declarative`, the target is one `SKILL.md`. The default mode stays as it is. The
phases below change as follows. Each other phase runs as before.

**Phase 1: the inventory has four classes.** Give each item a class, a place, and a
reason:

| Class | Meaning | Place |
|---|---|---|
| C (contract) | A literal string that a script, a hook, a test, or another skill reads. | keep: the rewrite states the string exactly. |
| R (rubric-tested) | A behaviour that a rubric item of the `/vet` suite of the skill tests. | keep, or move to a README section that states it. |
| B (other behaviour) | Any other limit, default, stop, ban, or question. | keep, or move to a README section that states it. |
| P (procedure) | An order or a method that a capable model finds alone. | drop as procedure, with a one-line reason. |

A place of "move to README section X" names the section. The Phase 3 inventory check
reads that section to make sure that it states the item. Only class P can be "drop as procedure".

Contracts to keep exactly:

- Each commit subject, in double quotes. The pdlc test
  `test_every_subject_a_skill_names_is_in_the_list` needs more than 10 quoted subjects
  across all skills. A README pointer alone breaks the test.
- Each trailer name, handoff title, header field, file name, status, and script command.
- The front matter, unchanged.

**Phase 2: the form and the budget replace the length rule.** Do not use the 0.9 to 1.3
length rule.

- Write the skill in the form of `AGENTS.md`: Goal, Inputs, Outputs, Constraints,
  optional Stages, and Done when.
- Take the word budget of the skill from `scripts/skill_budgets.json` in the repository.
- Do not add anything that the form in `AGENTS.md` bans.
- Stay inside the budget. If a fix needs more words, remove the same number of words
  elsewhere.
- Do not raise a budget. Ask the user.

**Phase 3: add the form check.** Run the checker from the root of the repository:

```
python3 scripts/check_skill_form.py <path>/SKILL.md
```

Correct each problem that the checker prints. Then run the pdlc tests. Then mark each
inventory item "kept", "moved", "dropped as procedure", "changed", or "lost". Correct each
changed or lost item. Refuse a drop that is not class P.

**Phase 4: vet settings.** In declarative mode, use the vet settings that the plan or the
user gives.

**Phase 5: report.** Add these items to the table:

- The body words before and after, and the budget.
- The inventory counts for each class and each place.
- The result of the form check.

## Rules

- Obey `references/writing-guidelines.md` in your replies and in the report.
- Do not change code, commands, paths, identifiers, error codes, or quoted text.
- Do not change the name of a skill or its trigger phrases.
- Do not change the meaning. If you are not sure of a meaning, ask the user.
- Do not show "no regression" if `/vet` did not run. Write "not measured".

## Files

- `references/writing-guidelines.md`: the guidelines. The repository root has the master
  copy, `WRITING-GUIDELINES.md`.
- `scripts/check_writing.py`: the linter.
- `scripts/test_check_writing.py`: the tests of the linter.
- `scripts/compare_vet.py`: compares two `/vet` results.
- `scripts/check_skill_form.py` and `scripts/skill_budgets.json`: at the root of the
  repository. The checker and the budgets of the declarative mode.

## Example

```
/improve-writing quiz
```

The skill copies `quiz` at the last commit, and records 34 behaviours in `inventory.md`.
Then the skill writes `quiz/SKILL.md` again. The linter shows 46 findings before the
rewrite and 0 after the rewrite. The inventory check shows that each of the 34 behaviours
is kept. `/vet` runs on the two versions with the saved suite: the baseline overall score
is 82.1, and the rewrite overall score is 83.0. The compare script shows "NO REGRESSION".
