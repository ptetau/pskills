# Sources

Where each convention in `conventions.md` comes from. Quotes were checked against these
pages. The skill's own defaults (for example ISO 8601 UTC time) are marked as such where
they are used.

| Source | Contributes |
|--------|-------------|
| Cucumber, Gherkin reference — <https://cucumber.io/docs/gherkin/reference/> | Keywords; the meaning of Given, When, and Then; 3–5 steps per example; Background and Scenario Outline usage; "your examples are an executable specification" |
| Cucumber, "Writing better Gherkin" — <https://cucumber.io/docs/bdd/better-gherkin/> | Declarative over imperative: "what, not how" |
| Cucumber blog, "Cucumber anti-patterns (part one)" (2016) — <https://cucumber.io/blog/bdd/cucumber-antipatterns-part-one/> | One behavior per scenario |
| Gojko Adzic, "Focus on key examples" (2014) — <https://gojko.net/2014/05/05/focus-on-key-examples/>; *Specification by Example* — <https://www.manning.com/books/specification-by-example> | Key examples with boundary values; specifications as executable documentation |
| Eiffel, "Design by Contract, Assertions and Exceptions" — <https://www.eiffel.org/doc/eiffel/ET-_Design_by_Contract_(tm),_Assertions_and_Exceptions> | Preconditions, postconditions, invariants, and who is at fault when each fails |
| Yaron Minsky, "Effective ML Revisited" (2011) — <https://blog.janestreet.com/effective-ml-revisited/> | "Make illegal states unrepresentable" |
| Alexis King, "Parse, don't validate" (2019) — <https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/> | Parse once at the boundary into refined types |
| Stripe, currencies — <https://docs.stripe.com/currencies> | Amounts in minor units; zero-decimal currencies; vendor exceptions (ISK, UGX) |
| ISO 4217 list one (SIX) — <https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xml> | Minor-unit exponents per currency |
| Martin Fowler, Money — <https://martinfowler.com/eaaCatalog/money.html> | Why money is a type: rounding losses, mixed currencies |
| Stripe, idempotent requests — <https://docs.stripe.com/api/idempotent_requests>; errors — <https://docs.stripe.com/api/errors> | Saved first result replayed (including 500s); keys pruned after 24 hours; parameter mismatch refused |
| IETF draft, "The Idempotency-Key HTTP Header Field" (draft-ietf-httpapi-idempotency-key-header-07; expired, not an RFC) — <https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/> | Key uniqueness; 400 missing, 422 reused with a different payload, 409 still in flight |
| Brandur Leach, "Implementing Stripe-like Idempotency Keys in Postgres" (2017) — <https://brandur.org/idempotency-keys> | Atomic phases and recovery points; 409 on mismatch |
| RFC 9457, Problem Details for HTTP APIs — <https://www.rfc-editor.org/rfc/rfc9457.html> | `type`, `title`, `status`, `detail`, `instance`; extension members; never parse `detail` |
| Marc Brooker, "Exponential Backoff and Jitter" (AWS, 2015) — <https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/> | Full jitter formula and comparison |
| Marc Brooker, "Timeouts, retries, and backoff with jitter" (Amazon Builders' Library, 2019) — <https://d1.awsstatic.com/builderslibrary/pdfs/timeouts-retries-and-backoff-with-jitter.pdf> | Timeouts from percentile latency; retry only idempotent calls; retry at one layer (243x); token-bucket budgets; jitter on all timers |
| RFC 9110, HTTP Semantics — <https://www.rfc-editor.org/rfc/rfc9110.html>; RFC 6585 (429) — <https://www.rfc-editor.org/rfc/rfc6585.html> | Idempotent methods; don't auto-retry non-idempotent requests; 4xx vs 5xx; 408, 429, 503, and `Retry-After` |
| Mermaid, state diagrams — <https://mermaid.js.org/syntax/stateDiagram.html> | `stateDiagram-v2` syntax, composite states, limits |
| David Harel, "Statecharts: a visual formalism for complex systems" (1987) — <https://weizmann.elsevierpure.com/en/publications/statecharts-a-visual-formalism-for-complex-systems/> | Hierarchy, concurrency, and communication added to state diagrams |
| GitHub spec-kit, spec template and specify command — <https://github.com/github/spec-kit/blob/main/templates/spec-template.md> | `[NEEDS CLARIFICATION]`, at most three, ranked by impact; informed guesses recorded as assumptions |
| Claude Code best practices — <https://code.claude.com/docs/en/best-practices> | Give the agent a check it can run; self-contained specs that name files and interfaces, state what is out of scope, and end with a verification step |
| SWE-bench (ICLR 2024) — <https://arxiv.org/html/2310.06770> | Success judged by FAIL_TO_PASS and PASS_TO_PASS tests |

The six-section format itself, its style rules (zero fluff, no cryptic IDs, agent-ready),
and the idea of pure, in-memory Engines come from the prompt this skill was built from.
The Engine-purity default is shared with `/decompose`, which adds that an Engine may call
ResourceAccess when the design records it (Löwy).
