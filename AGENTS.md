# Agent instructions for pskills

## Writing

Write all text to `WRITING-GUIDELINES.md`. This includes these types of text:

- Your replies to the user.
- Each file that you write, for example a spec, a plan, a report, or a web page.
- The text of a skill, an agent definition, or a prompt for a different agent.
- Commit messages and pull request text.

The three most important rules for a conversation are these:

- Write short sentences in the active voice. Give the answer first.
- Make each reply clear alone. A pronoun refers only to a noun in the same paragraph.
- Give each ID a short description in the same sentence, for example "B2 (cache the
  results)".

## Change the writing guidelines

1. Edit only `WRITING-GUIDELINES.md` at the root of the repository. Do not edit a copy.
2. Run `python3 scripts/sync_shared.py` to update each copy.
3. Before you commit, run `python3 scripts/sync_shared.py --check`.

The same script keeps the shared copies of `check_writing.py` and `c4.md` the same as
their master files.

## Write a skill, an agent, a plugin, or a prompt

State the goal and the limits. Trust the model to plan the steps. Use these sections, in
this order:

- `## Goal`: the end state, in 2 to 4 sentences.
- `## Inputs`: what the text reads, and how it selects an item.
- `## Outputs`: each file, status, and commit that the text makes.
- `## Constraints`: at most 8 rules. Each rule is one that the model cannot infer.
- `## Stages`: only for internal stages. Each `###` stage has the labels Goal, Inputs,
  Outputs, Done when, and (if needed) Constraints, in this order, in at most 6 lines.
- `## Done when`: the end conditions that a reader can check.

Do not put these in the text:

- A step-by-step procedure.
- A rule that a shared reference already states. Name the reference section instead.
- An example that the reference already has.

Keep each hard contract exact. A hard contract is a file name, a commit subject, a header
field, or a format that a script reads. Write each commit subject in double quotes.

A skill with a word budget must stay inside the budget. `scripts/skill_budgets.json`
holds each budget: 50% of the body of the skill, rounded up to 10 words, with a minimum of
170 words. A fix must not grow the body. If a fix needs words, remove the same number of
words. Only the user can raise a budget.

`scripts/check_skill_form.py` checks the form and the budget. It runs on each rewritten
skill. It does not run on the other skills yet.

## Rewrite a skill

1. Run `/improve-writing <skill>`. To rewrite a skill in the declarative form, run
   `/improve-writing <skill> --declarative`.
2. Do not merge a rewrite if `compare_vet.py` shows "REGRESSION".
3. If `/vet` did not run, write "not measured" in the pull request. Do not write "no
   regression".

## Tests

Run these tests before you commit:

```
python3 improve-writing/scripts/test_check_writing.py
python3 improve-writing/scripts/test_compare_vet.py
python3 scripts/test_check_skill_form.py
python3 vet/scripts/test_fingerprint.py
python3 scripts/sync_shared.py --check
python3 quiz-visual/scripts/test_quiz_visual.py
python3 bench/test_bench.py
python3 scripts/pdlc_known_files.py --check
(cd plugins/pdlc && python3 -m unittest discover -s tests)
python3 blueprint/scripts/check_blueprint.py blueprint/references/notifications.blueprint.md \
  --design decompose/references/notifications.design.md
```
