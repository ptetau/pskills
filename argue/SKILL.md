# Argue: Logical Contradiction Detector

The user starts this skill with `/argue <text>`. The text to analyse is in the ARGUMENTS
block.

## What this skill does

`/argue` breaks a text (a spec, an essay, a plan, or an argument) into discrete logical
claims. Then the skill encodes the claims in propositional logic. The skill runs Z3 (a
logic solver) as the oracle for hard contradictions. Z3 always gives the same result for
the same formulas. Then the skill uses reasoning to find tensions and ambiguities. The
annotated output shows exactly which statements conflict, and why they conflict.

## Writing

Write all text to `references/writing-guidelines.md`. This includes the replies to the
user, each question, and each file that this skill writes.

## Execution steps

### 1. Extract claims

Read the text. Identify each discrete logical claim in the text. A claim is a statement
that asserts that something is true, necessary, forbidden, implied, or conditional.
Ignore pure background context that makes no assertions.

Give the claims the numbers C1, C2, … Cn. Write each claim as one clause. If a sentence
has more than one claim, divide the sentence into its claims. Write each claim in plain
English. If the original wording is ambiguous, do not use the original wording.

If the text has no claims (pure narrative, no assertions), tell the user that the text
has no claims. Then stop.

### 2. Give each claim a propositional variable, and encode the relationships

Give each claim a short snake_case Boolean name. The name must show the meaning of the
claim. For example:
- "requests complete in under 100ms"  → `fast_requests`
- "validation pipeline takes 150ms+"  → `validation_slow`

Then identify the logical relationships between the claims. Use this table to encode
each relationship as a formula:

| Relationship                  | Formula                       |
|-------------------------------|-------------------------------|
| Claim X must hold             | assert X                      |
| Claim X must NOT hold         | assert Not(X)                 |
| "If X then Y"                 | Implies(X, Y)                 |
| "X and Y cannot both be true" | Not(And(X, Y))                |
| "At least one of X or Y"      | Or(X, Y)                      |
| "X if and only if Y"          | X == Y                        |

Encode only the relationships that the text clearly states or directly implies. If you
are not sure about a relationship, keep the claim as a standalone Bool. A standalone Bool
helps you find tensions and ambiguities, but not Z3 contradictions.

### 3. Write and run the Z3 Python script

Write the script to `_argue_check.py` in the current working directory.

Use this template. Complete the variables section and the constraints section:

```python
import json, sys
try:
    from z3 import Bool, Not, And, Or, Implies, Solver
except ImportError:
    print(json.dumps({"error": "z3_not_installed"}))
    sys.exit(0)

# ── claim variables ──────────────────────────────────────────
# (add one Bool per claim)
# fast_requests  = Bool('fast_requests')
# validation_slow = Bool('validation_slow')


# ── constraints (formula, tracker_label, human_citation) ─────
# Each tuple: (z3_formula, unique_string_label, "Cx" or "Cx × Cy")
constraints = [
    # (fast_requests,                          'c1',     'C1'),
    # (validation_slow,                        'c2',     'C2'),
    # (Implies(fast_requests, Not(validation_slow)), 'c1_c2', 'C1 × C2'),
]

s = Solver()
citation_map = {}
for formula, label, citation in constraints:
    s.assert_and_track(formula, label)
    citation_map[label] = citation

result = s.check()
sat = str(result) == "sat"
output = {"sat": sat, "contradictions": []}

if not sat:
    core = [str(c) for c in s.unsat_core()]
    output["contradictions"] = [citation_map.get(l, l) for l in core]

print(json.dumps(output))
```

Run the script:
```
python _argue_check.py
```

If the output is `{"error": "z3_not_installed"}`, run `pip install z3-solver`. Then run
the script again.

Parse the JSON. If `sat` is false, `contradictions` lists the UNSAT core citations.

After you parse the result, delete `_argue_check.py`.

### 4. Identify tensions and ambiguities (reasoning, not Z3)

**Tensions** — claim pairs that are each individually satisfiable but work against each
other in practice. Look for these signs:
- Goals that pull in opposite directions ("minimize cost" and "maximize reliability").
- Constraints that together leave near-zero slack (for example, two deadlines for the
  same resource).
- Sequential dependencies that cause bottlenecks, also when there is no logical
  contradiction.

**Ambiguities** — a single claim that is so underspecified that one possible
interpretation of the claim contradicts a different claim. Look for these signs:
- Undefined thresholds: "fast", "reasonable", "minimal", "most".
- Unclear scope: "all users" or "authenticated users".
- Conditional claims that do not give their conditions.

### 5. Format the output

Render this layout in a fenced code block, so that the layout stays monospace:

```
ARGUE: <short title for the text — 3-6 words>
══════════════════════════════════════════════════════════

CLAIMS
  [C1]  <claim text>
  [C2]  <claim text>
  ...

ANNOTATED TEXT
  <the original text, word for word, with a [Cn] tag immediately
   after each claim that you identified in the source text>

──────────────────────────────────────────────────────────
CONTRADICTIONS  (proven UNSAT by Z3)

  !! C1 × C3  <one-line plain-English explanation>
              logic: <the encoding that caused UNSAT>

  none        (if Z3 returned sat)

TENSIONS  (logically consistent but conflicting in practice)

  ~~ C2 × C5  <one-line explanation>

  none        (if you found no tensions)

AMBIGUITIES  (underspecified — could mask contradictions)

  ?? [C4]  <what is ambiguous and why it matters here>

  none        (if you found no ambiguities)

──────────────────────────────────────────────────────────
VERDICT   <N> contradiction(s)  ·  <N> tension(s)  ·  <N> ambiguity(ies)
```

After the code block, write one sentence of plain prose that summarises the most critical
finding. If all three sections are `none`, write "No issues found".

## Rules

- Always run Z3. Do not skip the solver. Do not use only your reasoning for the
  CONTRADICTIONS section. Z3 is the authority and always gives the same result. Your
  reasoning is not the authority.
- Do not force propositional relationships that the text does not clearly state. An
  honest "none" in CONTRADICTIONS is better than a fabricated UNSAT.
- For a very long text (50+ claims), warn the user that the encoding can be partial and
  covers only the most important claims.
- Keep the annotated text faithful to the original. Copy the original text word for
  word. Add only the [Cn] tags.
