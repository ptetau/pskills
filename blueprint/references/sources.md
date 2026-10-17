# Sources

This file gives the source of each convention in `conventions.md`. Each quote was checked
against these pages. Where `conventions.md` uses a default of the skill itself (for
example, ISO 8601 UTC time), the text says so.

| Source | Contributes |
|--------|-------------|
| Cucumber, Gherkin reference — <https://cucumber.io/docs/gherkin/reference/> | The keywords, and the meaning of Given, When, and Then. 3–5 steps in each example. The use of Background and Scenario Outline. "your examples are an executable specification" |
| Cucumber, "Writing better Gherkin" — <https://cucumber.io/docs/bdd/better-gherkin/> | Declarative steps, not imperative steps: "what, not how" |
| Cucumber blog, "Cucumber anti-patterns (part one)" (2016) — <https://cucumber.io/blog/bdd/cucumber-antipatterns-part-one/> | One behaviour in each scenario |
| Gojko Adzic, "Focus on key examples" (2014) — <https://gojko.net/2014/05/05/focus-on-key-examples/>; *Specification by Example* — <https://www.manning.com/books/specification-by-example> | Key examples with boundary values. Specifications as executable documentation |
| Eiffel, "Design by Contract, Assertions and Exceptions" — <https://www.eiffel.org/doc/eiffel/ET-_Design_by_Contract_(tm),_Assertions_and_Exceptions> | Preconditions, postconditions, invariants, and who is at fault when each fails |
| Yaron Minsky, "Effective ML Revisited" (2011) — <https://blog.janestreet.com/effective-ml-revisited/> | "Make illegal states unrepresentable" |
| Alexis King, "Parse, don't validate" (2019) — <https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/> | Parse once at the boundary into refined types |
| Stripe, currencies — <https://docs.stripe.com/currencies> | Amounts in minor units, zero-decimal currencies, and vendor exceptions (ISK, UGX) |
| ISO 4217 list one (SIX) — <https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xml> | The minor-unit exponent of each currency |
| Martin Fowler, Money — <https://martinfowler.com/eaaCatalog/money.html> | Why money is a type: rounding losses and mixed currencies |
| Stripe, idempotent requests — <https://docs.stripe.com/api/idempotent_requests>; errors — <https://docs.stripe.com/api/errors> | Stripe replays the saved first result (including 500s), prunes keys after 24 hours, and refuses a parameter mismatch |
| IETF draft, "The Idempotency-Key HTTP Header Field" (draft-ietf-httpapi-idempotency-key-header-07; expired, not an RFC) — <https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/> | Key uniqueness. 400 for a missing key, 422 for a key reused with a different payload, and 409 for a request still in flight |
| Brandur Leach, "Implementing Stripe-like Idempotency Keys in Postgres" (2017) — <https://brandur.org/idempotency-keys> | Atomic phases and recovery points, and 409 on a mismatch |
| RFC 9457, Problem Details for HTTP APIs — <https://www.rfc-editor.org/rfc/rfc9457.html> | The members `type`, `title`, `status`, `detail`, and `instance`. Extension members. Do not parse `detail` |
| Marc Brooker, "Exponential Backoff and Jitter" (AWS, 2015) — <https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/> | The full jitter formula, and a comparison |
| Marc Brooker, "Timeouts, retries, and backoff with jitter" (Amazon Builders' Library, 2019) — <https://d1.awsstatic.com/builderslibrary/pdfs/timeouts-retries-and-backoff-with-jitter.pdf> | Timeouts from percentile latency. Retry only idempotent calls. Retry at one layer (243x). Token-bucket budgets. Jitter on all timers |
| RFC 9110, HTTP Semantics — <https://www.rfc-editor.org/rfc/rfc9110.html>; RFC 6585 (429) — <https://www.rfc-editor.org/rfc/rfc6585.html> | Idempotent methods. Do not automatically retry non-idempotent requests. 4xx and 5xx. 408, 429, 503, and `Retry-After` |
| Mermaid, state diagrams — <https://mermaid.js.org/syntax/stateDiagram.html> | `stateDiagram-v2` syntax, composite states, and limits |
| David Harel, "Statecharts: a visual formalism for complex systems" (1987) — <https://weizmann.elsevierpure.com/en/publications/statecharts-a-visual-formalism-for-complex-systems/> | Hierarchy, concurrency, and communication added to state diagrams |
| GitHub spec-kit, spec template and specify command — <https://github.com/github/spec-kit/blob/main/templates/spec-template.md> | `[NEEDS CLARIFICATION]`, a maximum of three, ranked by impact. Informed guesses recorded as assumptions |
| Claude Code best practices — <https://code.claude.com/docs/en/best-practices> | Give the agent a check that it can run. Self-contained specs that name files and interfaces, state what is out of scope, and end with a verification step |
| SWE-bench (ICLR 2024) — <https://arxiv.org/html/2310.06770> | Success judged by FAIL_TO_PASS and PASS_TO_PASS tests |

Three items come from the prompt that this skill was built from. These items are the
six-section format, its style rules (zero fluff, no cryptic IDs, agent-ready), and the
idea of pure, in-memory Engines. `/decompose` has the same Engine-purity default.
`/decompose` adds that an Engine can call ResourceAccess when the design records the call
(Löwy).

## Diagrams and plain language

| Source | Contributes |
|--------|-------------|
| Simon Brown, the C4 model — <https://c4model.com> (abstractions, diagrams, notation, checklist) | The four levels. The definitions of container and component ("it's the container that's the deployable unit"). Draw component diagrams only when they add value. Titles, keys, typed elements, and labelled one-way arrows. "notation independent" |
| Simon Brown, "Modular monolith" — <https://simonbrown.je/modular-monolith/> | Well-defined components in a monolith are a stepping stone to microservices. The choice of containers is a separate decision |
| Mermaid, C4 diagrams — <https://mermaid.js.org/syntax/c4.html> | C4Context and C4Container syntax (experimental, with no automatic layout and no legend). Thus, component diagrams are C4-style flowcharts |
| GitHub, creating diagrams — <https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams> | Mermaid renders in GitHub Markdown |
| Kincaid, Fishburne, Rogers and Chissom, "Derivation of New Readability Formulas" (1975) — <https://stars.library.ucf.edu/istlibrary/56/> | The Flesch–Kincaid grade level that `check_writing.py` reports |
| ASD-STE100 Simplified Technical English, Issue 9 (ASD, 2025) — <https://www.asd-ste100.org> | The writing rules in `writing-guidelines.md`: sentence length, verb forms, one instruction in each sentence, vertical lists, and the pronoun rules |

