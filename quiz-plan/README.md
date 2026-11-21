# `/quiz-plan` — Quiz-driven Change Plan

`/quiz-plan` runs an adaptive interview, not a fixed list. The interview finds each
assumption, ambiguity, and dependency in a proposed change. Then `/quiz-plan` writes a
structured `<name>.plan.md` in the `plans/` folder at the project root. The plan has these
parts: Intent, Ground truth, Boundaries, gated Steps, Verification/rollback, and a live
progress tracker. Step 1 always tests the riskiest assumption.

**Example**

```
/quiz-plan add rate limiting to the public API routes
```

`/quiz-plan` asks more and more specific questions, for example "configurable or hardcoded
limit?", "which middleware dir?", and "what must not change?". `/quiz-plan` continues
until it can see the exact files and changes. Then `/quiz-plan` asks the user to confirm.
After that, `/quiz-plan` writes `plans/add-api-rate-limiting.plan.md`. The plan has a gate
for each step (AUTO / GATED), and a 12-character progress bar in the header.
