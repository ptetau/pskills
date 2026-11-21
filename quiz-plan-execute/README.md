# `/quiz-plan-execute` — Plan Executor (TDD, per-step commits)

`/quiz-plan-execute` is the executor twin of `/quiz-plan`. `/quiz-plan-execute` reads a
`.plan.md`, and completes each step through a strict 6-stage gate. Each stage must finish
before the next stage starts:

1. **Understand** the acceptance criteria (the `Done when` of the step).
2. **Red** — write the failing test.
3. **Green** — write the minimum implementation that passes the test.
4. **Refactor** — remove duplication, obey the conventions, and decrease the complexity.
5. **Review** the work against the acceptance criteria.
6. **Commit** — make one commit for each step. Update the plan tracker in the same commit.

At the start, `/quiz-plan-execute` asks one question: whether to make a new branch. At
the end, `/quiz-plan-execute` offers to squash-merge locally or to open a PR.

**Example**

```
/quiz-plan-execute add-api-rate-limiting.plan.md
```

A GATED step pauses for human review. An AUTO step continues. If a conflict with the
Intent or the Boundaries occurs, `/quiz-plan-execute` stops and asks. `/quiz-plan-execute`
does not resolve the conflict itself.
