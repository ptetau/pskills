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

## Rewrite a skill

1. Run `/improve-writing <skill>`.
2. Do not merge a rewrite if `compare_vet.py` shows "REGRESSION".
3. If `/vet` did not run, write "not measured" in the pull request. Do not write "no
   regression".

## Tests

Run these tests before you commit:

```
python3 improve-writing/scripts/test_check_writing.py
python3 scripts/sync_shared.py --check
python3 quiz-visual/scripts/test_quiz_visual.py
(cd plugins/pdlc && python3 -m unittest discover -s tests)
```
