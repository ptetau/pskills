# Argue: Logical Contradiction Detector

Triggered by `/argue <text>` — the text to analyze is in the ARGUMENTS block.

## What this skill does

Breaks a text (spec, essay, plan, argument) into discrete logical claims, encodes them
in propositional logic, runs Z3 as the deterministic oracle for hard contradictions,
then uses reasoning to flag tensions and ambiguities. Produces annotated output showing
exactly which statements conflict and why.

## Execution steps

### 1. Extract claims

Read the text and identify every discrete logical claim — statements that assert
something to be true, required, forbidden, implied, or conditional. Ignore pure
background context that makes no assertions.

Number claims C1, C2, … Cn. Keep each claim to one clause. Split multi-claim sentences.
Write them in plain English, not the original wording if that was ambiguous.

If the text has no claims (pure narrative, no assertions), say so and stop.

### 2. Assign propositional variables and encode relationships

For each claim assign a short, meaningful snake_case Boolean name. Examples:
- "requests complete in under 100ms"  → `fast_requests`
- "validation pipeline takes 150ms+"  → `validation_slow`

Then identify logical relationships between claims and encode as formulas:

| Relationship                  | Formula                       |
|-------------------------------|-------------------------------|
| Claim X must hold             | assert X                      |
| Claim X must NOT hold         | assert Not(X)                 |
| "If X then Y"                 | Implies(X, Y)                 |
| "X and Y cannot both be true" | Not(And(X, Y))                |
| "At least one of X or Y"      | Or(X, Y)                      |
| "X if and only if Y"          | X == Y                        |

Only encode relationships that are clearly stated or directly implied by the text.
When in doubt, leave a claim as a standalone Bool (it contributes to tensions/
ambiguity detection, not Z3 contradictions).

### 3. Write and run the Z3 Python script

Write the script to `_argue_check.py` in the current working directory.

Template — fill in the variables and constraints sections:

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

Run it:
```
python _argue_check.py
```

If the output is `{"error": "z3_not_installed"}`, run `pip install z3-solver` then retry.

Parse the JSON. If `sat` is false, `contradictions` lists the UNSAT core citations.

Clean up `_argue_check.py` after parsing the result.

### 4. Identify tensions and ambiguities (reasoning, not Z3)

**Tensions** — claim pairs that are each individually satisfiable but work against each
other in practice. Signs to look for:
- Goals that pull in opposite directions ("minimize cost" vs "maximize reliability")
- Constraints that together leave near-zero slack (e.g., two deadlines for the same resource)
- Sequential dependencies that create bottlenecks even without a logical contradiction

**Ambiguities** — individual claims underspecified enough that an interpretation exists
that would contradict another claim. Signs to look for:
- Undefined thresholds: "fast", "reasonable", "minimal", "most"
- Unclear scope: "all users" vs "authenticated users"
- Conditionals with unstated conditions

### 5. Format the output

Render this layout in a fenced code block so it stays monospace:

```
ARGUE: <short title — 3-6 words describing the text>
══════════════════════════════════════════════════════════

CLAIMS
  [C1]  <claim text>
  [C2]  <claim text>
  ...

ANNOTATED TEXT
  <original text reproduced verbatim, with [Cn] tags inserted
   immediately after each identified claim in the source text>

──────────────────────────────────────────────────────────
CONTRADICTIONS  (proven UNSAT by Z3)

  !! C1 × C3  <one-line plain-English explanation>
              logic: <the encoding that caused UNSAT>

  none        (if Z3 returned sat)

TENSIONS  (logically consistent but conflicting in practice)

  ~~ C2 × C5  <one-line explanation>

  none        (if no tensions found)

AMBIGUITIES  (underspecified — could mask contradictions)

  ?? [C4]  <what is ambiguous and why it matters here>

  none        (if no ambiguities found)

──────────────────────────────────────────────────────────
VERDICT   <N> contradiction(s)  ·  <N> tension(s)  ·  <N> ambiguity(ies)
```

After the code block, add one plain-prose sentence summarising the most critical finding
(or "No issues found" if all three sections are none).

## Rules

- Always run Z3 — never skip the solver and rely on reasoning alone for the
  CONTRADICTIONS section. Z3 is the deterministic authority; your reasoning is not.
- Do not force propositional relationships that aren't clearly stated. An honest
  "none" in CONTRADICTIONS is better than a fabricated UNSAT.
- For very long texts (50+ claims), warn the user that encoding may be partial
  and only covers the most salient claims.
- Keep the annotated text faithful — reproduce the original verbatim, only adding [Cn] tags.
