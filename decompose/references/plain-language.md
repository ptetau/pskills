# Plain language

Everything this skill writes for people should read as if a bright 10-year-old is the
reader. Short sentences. Common words. Every technical word explained. The same
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

1. **One idea per sentence.** Aim for 15 words or fewer. Never go over 20 words in an
   instruction, or 25 in any other sentence. An instruction starts with a command verb,
   such as "Use" or "Keep".
2. **Use the everyday word.** "Use", not "utilise". "Send", not "dispatch". "Can't
   change", not "immutable". "Rule", not "invariant". If you need "invariant", explain it.
3. **Say who does what.** "The Manager decides the order", not "the order is determined".
4. **Explain each technical word once**, the first time it matters, in plain words. Then
   add it to the **Words used here** list in section 1. A word that is hard to explain is
   a sign to use a simpler one.
5. **Show, don't abstract.** Give an example or a number. "Try up to 5 times, waiting
   longer each time" beats "bounded retries with exponential backoff".
6. **Start with the point.** The first sentence of each section says what matters most.
7. **Lists for steps and options.** Tables for comparisons. Prose for reasons.
8. **No filler.** No "In this document we will…", no "It is important to note that…".
9. **Put a condition first.** "If the vendor times out, try again", not "Try again if the
   vendor times out".
10. **Use New Zealand spelling**: "behaviour", "catalogue", "organise". Names and code keep
    their own spelling (`color: #000` in a diagram).
11. **Give an ID with its name**: "V3 (message content)", never "V3" alone. A trace
    column, such as a brick's **Serves** column, may list IDs alone. A blueprint uses no
    design IDs at all.
12. **State the facts as they are now.** Don't tell how the document came about, or who
    asked for what. Give the reason for the design as it is. Write "One `Adjust(kind)`
    brick would mix three different sums, so the design uses three bricks". Don't write
    "The first draft had one brick".

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

The same list defines the method terms (Manager, Engine, ResourceAccess, Client, Utility,
brick) the first time a document uses them.

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

Run the bundled checker on the document:

```
python <skill-dir>/scripts/readability.py name.md
```

The checker measures the prose only (it skips code, names, tables, and diagrams). It
reports the average sentence length and a reading grade. It lists every sentence over its
limit (20 words for an instruction, 25 for any other sentence), with its line number. It
also lists every technical word the document uses but doesn't explain in its **Words used
here** list. Rewrite until the checker prints `READS PLAINLY`, or until the only warnings
left are ones you can defend.
