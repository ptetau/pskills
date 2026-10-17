---
name: quiz
description: >
  Quick inline clarifier. Asks ONE question at a time before the work starts. Uses the
  native picker (the AskUserQuestion tool) when the session has it, and a short
  plain-markdown question when the session does not have it. Does not use ASCII cards or
  code blocks. Plans a fixed, ordered list of questions first, so that the same request
  gets the same questions. Gives each recommendation a reason from the words of the user,
  and echoes each answer in one line. Shows the resolved answers for a final OK before
  the work starts. Use when the user says "/quiz", "quiz me", "ask me a few questions",
  or wants a fast back-and-forth. Best for about 1-7 questions that are mostly text, on
  mobile, or when speed is important.
---

# Quiz: Inline Clarifier

## Purpose

`/quiz` gets the decisions that are important before the work starts, one question at a
time. In `/quiz`, each question is a native picker that the user clicks, or a short
markdown question that the user answers with a letter.

Use `/quiz` in these conditions:

- There are about **1-7 questions**, and you ask **one question in each turn**.
- The user wants a quick back-and-forth, or the user is **on mobile**.
- The questions are mostly **text** (tone, scope, name), or a visual choice needs only a
  short preview for each option.

## Writing

Write all text by the rules in `references/writing-guidelines.md`. This includes the
replies to the user, each question, and each file that this skill writes. The exact
formats in this skill have priority over the guidelines. For example, each option still
has one sentence that ends with its cost or trade-off.

## Step 1: Plan the questions before you ask any

The same request must get the same questions. Before the first question, make the full
list with this procedure. Then keep to the list.

1. Examine these dimensions, in this order:
   1. **Purpose and audience**: what the work is for, and who the work is for.
   2. **Style**: the tone for writing, the look for design, and the conventions for code.
   3. **Scope**: the length, the size, and what is in or out.
   4. **Focus**: what comes first, and what is most important.
   5. **Next step**: the call to action, the output format, or where the work goes.
2. Ask about a dimension only if the prompt leaves the dimension open
   **and** the answer would change the work. Do not ask about anything that the prompt
   already decides. A dimension can hold two independent decisions that both
   change the work. Only then, ask a second question for that dimension.
3. The list, in that order, is the quiz. Thus, the most important questions come first.
   Ask a maximum of 7 numbered questions. Drop the questions that come last in the list.
4. **Commit to the list.** The total number of questions, T, is fixed when you ask the
   first question. After that, do not add, remove, or reorder the numbered questions.
   If an answer causes a new ambiguity, echo the answer first. Then ask one follow-up in
   plain prose. Do not make the follow-up a new numbered question.

## Step 2: Write each question

Each question has these parts:

- A **label** of one or two words, with a maximum of 12 characters, for example `Tone`
  or `Audience`.
- The **question**: one sentence that ends with `?`, in the words of the user.
- **2-4 options**. Each option has a short label of 1-5 words and one sentence. The
  sentence tells what the option does and why the option fits this request. The sentence
  **ends with the cost or the trade-off of the option**. Give this sentence to each
  option, also to the options of the first question.
- A maximum of **one recommended option**, which you list first. List the other options
  from the most likely fit to the least likely fit.

**Recommend only on evidence.** Recommend an option only when the user said something
that points to the option. Name that thing in the sentence of the option, for example
"since this is a climbing gym". If nothing that the user said favours an option, do not
recommend an option. That condition is typical for the first question on a short request.
Do not recommend two options.

## Step 3: Ask the question

**Picker.** If the session has the `AskUserQuestion` tool, ask each question with the
tool. Ask one question in each call:

- `header`: the label.
- `question`: the question, then ` (N of T)`.
- `options`: the 2-4 options. Put the recommended option first, with ` (Recommended)` at
  the end of its label. The `description` of each option is the sentence of the option.
- `multiSelect`: false, unless the question really is "pick any that apply".
- `preview`: only for visual choices, for example a layout, sample text, or the shape of
  some code. Give a short mockup for each option.

The user can always select "Other" and type a different answer.

**Fallback.** If there is no picker, or if the user asks for text, write the question as
plain markdown in the message. Do not use code blocks, box drawing, or emojis. Use
exactly this layout:

````markdown
**Question 1 of 3 · Tone**
What tone should the welcome email have?

- **A · Stoked (recommended)**: matches how climbers talk to each other, since this is
  a climbing gym, but it can read as try-hard to a quieter crowd.
- **B · Warm**: friendly and personal, a safe fit for a mixed membership, but it has
  less energy.
- **C · Plain**: gives the facts first and is the quickest to read, but it can feel
  like a receipt.

Reply A, B, or C. You can add a note, for example `B, keep it short`.
````

The fence above only shows the layout. Show the question as markdown, not in a code
block. If there is no recommendation, remove `(recommended)` from each option.

**Ask one question in each message, always.** Do not put two questions in one message or
in one picker call.

## Step 4: Echo each answer, then ask the next question

After each answer, write one echo line. Then ask the next question in the same message.
In the echo, write the label of the option without its ` (Recommended)` suffix. Each echo
has one of these exact forms:

| The user… | Echo |
|---|---|
| picked an option | `✓ 2/3 Tone → Warm` |
| picked and added a note | `✓ 2/3 Tone → Warm (note: keep it short)` |
| deferred ("you decide", "skip", "n/a", "go with your pick") | `✓ 2/3 Tone → Stoked (you decided: recommended)` |
| deferred where nothing was recommended | `✓ 2/3 Tone → Stoked (you decided: first option)` |
| wrote words that match an option | `✓ 2/3 Tone → Warm (from: "the friendly one")` |
| wrote their own answer ("Other") | `✓ 2/3 Tone → dry and funny` |

When you read a reply in the fallback, accept many forms, for example `A`, `a`,
`Option A`, `B, with notes: …`, `B, …`, or `B (…)`. If the user answers several questions in one
reply (`1a 2b 3c`), accept all the answers. Echo each answer on its own line, in order.
Then ask the first question that has no answer. If each question has an answer, go to
Step 5.

## Step 5: Confirm, then start

After the last answer, show each answer as an echo line in a bulleted list. Give one line
for each question, in order. Do not put the list in a code block:

- ✓ 1/3 Tone → Stoked
- ✓ 2/3 Focus → Getting started (note: mention the free intro belay class)
- ✓ 3/3 Length → Short and scannable

Then ask the user to confirm:

- **Picker:** ask one question with the header `Confirm` and the question
  `Go with these answers?`. Give two options: `Go` ("start with these answers") and `Change one` ("tell
  me which answer to change"). Do not recommend an option, because nothing that the user
  said selects one.
- **Fallback:** write one sentence: *"I will start with these answers unless you say
  `wait` to change one."*

When the user confirms, tell the user what the answers mean in one short paragraph, for
example "So I will write X, with Y, and without Z". Then start the work. If the user
changes an answer, update that echo line and show the list again. Do not ask the other
questions again.

## What not to do

- Do not use ASCII cards, box-drawing characters, or code blocks around questions or
  echoes.
- Do not put two questions together. Ask one question in each message and in each picker
  call.
- After the first question, do not change the numbered list or its total.
- Do not recommend an option without a reason from what the user said.
- Do not ask the same question two times. If a reply is not clear, ask one time in plain
  prose.
- Do not run a quiz for one small clarification. Ask the question in a sentence.
