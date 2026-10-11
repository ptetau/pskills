# DES-writing-style · How we write

Status: agreed · Default: yes · Ask at init: no

## Scope

Everything written for engineers and agents:

- specs, intents and change specs;
- handoffs, review packets and review results;
- commit messages and pull request text;
- code comments and agent instructions;
- messages to the user.

Code, commands, file names, quoted user text and other systems' names keep their own
spelling and form.

## Rule

`pdlc/bin/check_writing.py` checks rules 1, 2, 5 and 6 where it can. Reviewers judge the
rest.

### 1. Simplified Technical English (ASD-STE100), core rules

We use the core writing rules of ASD-STE100. We don't use its controlled dictionary.

Words:
- Use short, common words. "Use", not "utilise". "Start", not "initiate".
- Use one word for one thing, and keep using that word. If a "check" proves a
  requirement, don't call it a "test" in the next sentence.
- Use the project's technical names exactly as the project writes them.
- Use a verb for an action. "Check the file", not "do a check of the file".
- Use simple tenses: present, past and future. "The script stops", not "the script will
  be stopping".
- Don't stack more than three nouns. "The reset link expiry time" becomes "the time the
  reset link expires".

Sentences:
- An instruction has 20 words or fewer. A description has 25 words or fewer.
- One instruction per sentence, unless the two actions happen at the same time.
- Use the active voice. "The builder writes the code", not "the code is written".
- Give instructions as commands. "Run the checks."
- Put a condition first. "If a check fails, stop the build."
- Start a warning with the command, then give the reason. "Don't commit on main. Main
  holds only merged work."

Paragraphs:
- One topic per paragraph, six sentences at most.
- Use a list for three or more items or steps.

### 2. New Zealand spelling

- "-ise", not "-ize": organise, summarise, prioritise.
- "-our", not "-or": colour, behaviour, favour.
- "-re", not "-er": centre, metre.
- Also: analyse, catalogue, defence, grey, travelled, modelling.
- Noun and verb differ: a "licence" and a "practice" (nouns); to "license" and to
  "practise" (verbs).
- "Program" for software. "Programme" for a plan or schedule.

### 3. Concrete examples

Explain a concept or a rule with a concrete example, from this project where you can.

- Not: "Test limits carefully."
- But: "Test a one-hour limit at 59:59 (accepted) and at 60:00 (refused)."

### 4. Clear references to nouns

Use "it", "this", "that" or "they" only when one noun can be meant. If two nouns could be
meant, repeat the noun.

- Not: "The builder sends the result to the reviewer after it runs."
- But: "After the builder runs, the builder sends the result to the reviewer."

### 5. Name what an ID points to

When you refer to another requirement, spec, change or section, give its ID and a short
name. Never the ID alone.

- Not: "This conflicts with R3."
- But: "This conflicts with CAP-email.R3 (the reset link expires after one hour)."

Machine fields are exempt: trace trailers (`Req: CAP-email.R3`), check names, branch names
and tables that already show the name in another column.

### 6. No conversation in artifacts

An artifact states the facts as they are now. It doesn't tell the story of how they came
about, or who asked for what.

- Not: "As you asked, I changed the limit to 10 because the reviewer flagged it."
- But: "Maximum: 10 items. (assumed)"

Record a decision as a fact, in the place for decisions. Example, in an intent's Notes:
`CAP-email.R3 (reset link expiry): how long? → one hour (assumed)`. Git keeps the history.

### 7. Be concise

- Say each thing once.
- Cut words that don't change the meaning.
- No preamble and no closing summary of what you just wrote.
- If a sentence needs rereading, rewrite it.
