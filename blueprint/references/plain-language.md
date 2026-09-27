# Plain language

Everything this skill writes for people should read like it was written for a bright
10-year-old. Short sentences. Common words. Every technical word explained. The same
guide ships with `/decompose` and `/blueprint`, so their documents read alike.

Plain words are not less exact. "Send each message at most once" is as exact as "delivery
is idempotent", and more people understand it.

## What stays exact

Some things are names, not prose. Never simplify them:

- Code, types, and method names: `DeliveryStatus`, `claim(key, envelope)`.
- Error codes: `IDEMPOTENCY_CONFLICT`.
- Component names: `RoutingEngine`.
- Numbers, units, and formats: `30 s`, `NZD 5.00`, `2026-03-02T22:30:00Z`.

Everything around them is plain English.

## Rules

1. **One idea per sentence.** Aim for 15 words or fewer. Never go over 25.
2. **Use the everyday word.** "Use", not "utilize". "Send", not "dispatch". "Can't
   change", not "immutable". "Rule", not "invariant", unless you explain it.
3. **Say who does what.** "The Manager decides the order", not "the order is determined".
4. **Explain each technical word once**, the first time it matters, in plain words. Then
   add it to the **Words used here** list in section 1. A word that is hard to explain is
   a sign to use a simpler one.
5. **Show, don't abstract.** Give an example or a number. "Try up to 5 times, waiting
   longer each time" beats "bounded retries with exponential backoff".
6. **Start with the point.** The first sentence of each section says what matters most.
7. **Lists for steps and options.** Tables for comparisons. Prose for reasons.
8. **No filler.** No "In this document we will…", no "It is important to note that…".

## Words used here

Each document has a short glossary in section 1, under the heading `### Words used here`.
One line per word: the word, then a plain explanation. Only list words the document
actually uses. For example:

- **Idempotent**: doing it twice has the same effect as doing it once.
- **Invariant**: a rule that must always be true, no matter what happens.
- **Volatility**: how likely something is to change.
- **Encapsulate**: keep something inside one part, so changing it doesn't affect the rest.
- **Backoff**: waiting a little longer after each failed try.
- **Jitter**: adding a random wait, so many retries don't all happen at once.
- **Atomic**: happens all at once or not at all; nothing half-done is left behind.
- **Precondition**: something that must be true before a step can run.

Method terms (Manager, Engine, ResourceAccess, Client, Utility, brick) are defined in the
same list the first time a document uses them.

## Plain words for common terms

| Instead of | Write |
|------------|-------|
| volatility | how likely it is to change |
| encapsulate | keep inside one part |
| orthogonal | independent: changing one doesn't change the other |
| idempotent | safe to do twice |
| invariant | a rule that must always hold |
| orchestrate | run the steps in order |
| deterministic | always gives the same answer for the same input |
| atomic | all or nothing |
| payload | the data sent |
| latency | how long it takes |
| synchronous | waits for the answer before going on |
| asynchronous | goes on without waiting for the answer |

## Diagrams

Label boxes and arrows in plain words too: "Sends messages", not "Egress dispatch". Give
each diagram a title that says what it shows. Keep technology labels (`HTTPS`,
`Postgres`) as they are.

## Check it

Run the bundled checker on the document (`/blueprint`'s `check_blueprint.py` also runs it):

```
python <skill-dir>/scripts/readability.py name.md
```

It measures the prose only (code, names, tables, and diagrams are skipped). It reports the
average sentence length and a reading grade. It lists every sentence over 25 words with
its line number, and every technical word the document uses but doesn't explain in its
**Words used here** list. Rewrite until
it prints `READS PLAINLY`, or until the only warnings left are ones you can defend.
