# `/argue` — Logical Contradiction Detector

Paste any text (spec, plan, essay, argument). Then `/argue` does these steps:

1. `/argue` divides the pasted text into discrete logical claims (C1, C2, …).
2. `/argue` encodes each claim in propositional logic.
3. `/argue` runs **Z3** as a deterministic SAT solver to prove hard contradictions.
4. `/argue` uses reasoning to flag tensions and ambiguities.
5. `/argue` gives an annotated version of the original text, and a tiered summary.

The `z3-solver` package is necessary for `/argue`. To install the package, run
`pip install z3-solver`.

**Example**

```
/argue The API must respond within 50ms. All requests go through the fraud
detection pipeline before returning. The fraud pipeline takes 200ms minimum.
No request may bypass fraud detection.
```

**Output (excerpt)**

```
CONTRADICTIONS  (proven UNSAT by Z3)

  !! C1 × C2 × C3  A synchronous fraud check of 200ms+ makes a 50ms
                   API response impossible for any request
                   logic: api_under_50ms ∧ all_requests_fraud
                          ∧ fraud_takes_200ms_plus → UNSAT

VERDICT   1 contradiction  ·  1 tension  ·  1 ambiguity
```
