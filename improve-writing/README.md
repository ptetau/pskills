# `/improve-writing` — Rewrite Text to the Writing Guidelines

`/improve-writing` writes a file or a skill again, so that the text obeys
`WRITING-GUIDELINES.md`. The meaning, the facts, the code, and the quoted text stay the
same.

```
/improve-writing <path> [<path> …] [--no-eval] [--dictionary PATH]
```

For a document, `/improve-writing` writes the text again and runs the linter. The skill
stops when the linter shows no findings, or only findings with a recorded reason.

A rewrite can change what a skill does. Thus, for a skill or a prompt, `/improve-writing`
does these steps:

1. `/improve-writing` records each behaviour of the old version in a list, the behaviour
   inventory.
2. `/improve-writing` writes the text again.
3. `/improve-writing` makes sure that the rewrite keeps each behaviour in the inventory.
4. `/improve-writing` runs `/vet` on the old version and on the new version, with the
   same suite and the same models.
5. `/improve-writing` compares the two results with `compare_vet.py`. The script shows
   "REGRESSION" in these conditions:
   - The overall score falls more than 5 points.
   - A weight-3 rubric item falls more than 20 points.
   - Fewer runs are usable.

**Output (excerpt)**

```
| File          | Findings before | Findings after | Inventory     | Baseline | Rewrite | Result        |
|---------------|-----------------|----------------|---------------|----------|---------|---------------|
| quiz/SKILL.md | 46              | 0              | 34 of 34 kept | 82.1     | 83.0    | NO REGRESSION |
```

`/improve-writing` does not commit. You examine the change first.
