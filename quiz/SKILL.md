---
name: quiz
description: >
  Quick inline clarifier. Asks ONE question at a time before starting work, through
  the native picker (the AskUserQuestion tool) when the session has it and as a short
  plain-markdown question otherwise; never ASCII cards or code blocks. Plans a fixed,
  ordered question list up front so the same request gets the same questions, grounds
  every recommendation in what the user said, echoes each answer in one line, then
  shows the resolved answers for a final OK before work begins. The inline twin of
  /squiz (which renders a full visual document). Use when the user says "/quiz",
  "quiz me", "ask me a few questions", or wants a fast back-and-forth rather than a
  rendered document. Prefer /quiz over /squiz for about 1-7 mostly textual questions,
  on mobile, or when speed matters.
---

# Quiz: Inline Clarifier

## Purpose

`/quiz` gathers the decisions that matter before doing the work, one question at a
time. It's the inline twin of [[squiz]]: same job, but each question is either a native
picker the user clicks or a short markdown question they answer with a letter.

Use `/quiz` when:
- there are about **1-7 questions**, asked **one per turn**;
- the user wants a quick back-and-forth, or is **on mobile**;
- the questions are mostly **textual** (tone, scope, name), or a short preview per
  option is enough to show a visual choice.

Use `/squiz` instead when:
- there are 8+ questions and seeing them all at once helps;
- options need side-by-side visual comparison bigger than a short preview;
- the user asks for "the doc", "the form", or `/squiz`.

When in doubt, use `/quiz`. The user can always say "give me the full squiz".

## Step 1: Plan the questions before asking any

The same request should get the same questions. Before the first question, build the
whole list with this procedure, then commit to it:

1. Walk these dimensions, in this order:
   1. **Purpose and audience**: what it's for and who it's for.
   2. **Style**: tone for writing, look for design, conventions for code.
   3. **Scope**: length, size, what's in or out.
   4. **Focus**: what leads, what matters most.
   5. **Next step**: the call to action, output format, or where it goes.
2. For each dimension, ask one question only if the prompt leaves it open **and** the
   answer would change the work. Skip anything the prompt already settles. A dimension
   takes a second question only when it holds two independent decisions that both
   change the work.
3. The list, in that order, is the quiz. The most load-bearing questions come first by
   construction. Cap it at 7; if more remain, offer `/squiz` (see Escalation).
4. **Commit.** The total, T, is fixed once the first question is asked. Don't add,
   drop or reorder numbered questions after that. If an answer opens a new ambiguity,
   ask one plain-prose follow-up (not a new numbered question) right after echoing it.

## Step 2: Write each question

Each question has:
- a **label** of one or two words, at most 12 characters (e.g. `Tone`, `Audience`);
- the **question**, one sentence ending in `?`, in the user's own terms;
- **2-4 options**. Each option is a short label (1-5 words) and one sentence that says
  what it does, why it fits this request, and **ends on its cost or trade-off**. Every
  option gets that sentence, including options on the first question;
- at most **one recommended option**, listed first. List the rest from most to least
  likely to fit.

**Recommend only on evidence.** Recommend an option only when something the user said
points to it, and name that thing in its sentence ("since this is a climbing gym").
When nothing they said favours any option, which is typical for the first question on a
terse request, recommend nothing. Never recommend two.

## Step 3: Ask it

**Picker.** When the session has the `AskUserQuestion` tool, ask each question through
it: one question per call.
- `header`: the label.
- `question`: the question, followed by ` (N of T)`.
- `options`: the 2-4 options, the recommended one first with ` (Recommended)` at the end
  of its label; each `description` is the option's sentence.
- `multiSelect`: false, unless the question really is "pick any that apply".
- `preview`: only for visual choices (a layout, sample text, a code shape), as a short
  mockup per option.

The user can always choose "Other" and type their own answer.

**Fallback.** When there's no picker, or the user asks for text, write the question as
plain markdown in the message itself. No code blocks, no box drawing, no emojis.
Exactly this layout:

````markdown
**Question 1 of 3 · Tone**
What tone should the welcome email have?

- **A · Stoked (recommended)**: matches how climbers talk to each other, since this is
  a climbing gym; it can read as try-hard to a quieter crowd.
- **B · Warm**: friendly and personal, a safe fit for a mixed membership; it carries
  less energy.
- **C · Plain**: facts first and quickest to read; it can feel like a receipt.

Reply A, B or C, optionally with a note (e.g. `B, keep it short`).
````

(The fence above is only to show the layout. Render it as markdown, never inside a code
block.) When there's no recommendation, drop `(recommended)` from every option.

**One question per message, always.** Never stack two questions in one message or one
picker call.

## Step 4: Echo each answer, then ask the next

After each answer, write one echo line, then ask the next question in the same message.
Echo the option's label without its ` (Recommended)` suffix. Echoes always take one of
these exact forms:

| The user… | Echo |
|---|---|
| picked an option | `✓ 2/3 Tone → Warm` |
| picked and added a note | `✓ 2/3 Tone → Warm (note: keep it short)` |
| deferred ("you decide", "skip", "n/a", "go with your pick") | `✓ 2/3 Tone → Stoked (you decided: recommended)` |
| deferred where nothing was recommended | `✓ 2/3 Tone → Stoked (you decided: first option)` |
| wrote words that match an option | `✓ 2/3 Tone → Warm (from: "the friendly one")` |
| wrote their own answer ("Other") | `✓ 2/3 Tone → dry and funny` |

Reading replies in the fallback, be permissive: `A`, `a`, `Option A`,
`B, with notes: …`, `B, …`, `B (…)`. If the user answers several at once (`1a 2b 3c`),
accept them all, echo each line in order, and carry on with the first unanswered
question, or go straight to Step 5 if none is left.

## Step 5: Confirm, then start

After the last answer, list every answer as a bulleted list of echo lines, one per
question and in order, with no code block around it:

- ✓ 1/3 Tone → Stoked
- ✓ 2/3 Focus → Getting started (note: mention the free intro belay class)
- ✓ 3/3 Length → Short and scannable

Then ask for the go-ahead:
- **Picker:** one question with header `Confirm`, question `Go with these answers?`,
  and options `Go` ("start with these answers") and `Change one` ("tell me which answer
  to change"). Neither is recommended: nothing the user said picks between them.
- **Fallback:** one sentence: *"Going with these. Say `wait` if anything's wrong,
  otherwise I'll start."*

Once confirmed, say what that means in one short paragraph ("So I'll write X, with Y,
skipping Z") and begin. If the user changes an answer, update that echo line and show
the list again; don't re-ask the rest.

## Internal JSON (for parity with /squiz)

Track answers in the same shape `/squiz` exports, so the two flows mix. Don't show it
unless the user asks for "the squiz JSON":

```json
{
  "spec": "<short task summary>",
  "generatedAt": "<ISO timestamp>",
  "decisions": [
    {
      "id": "tone",
      "question": "What tone should the welcome email have?",
      "choice": { "id": "stoked", "name": "Stoked", "summary": null },
      "notes": null
    }
  ],
  "summary": { "total": 3, "resolved": 3, "withNotes": 1 }
}
```

A deferred answer ("you decide", "skip") records the option taken, with
`"notes": "you decided"`. `choice` is `null` only when no option was taken at all.

## What not to do

- No ASCII cards, box-drawing characters, or code blocks around questions or echoes.
- Don't stack questions: one per message, one per picker call.
- Don't change the numbered list, or its total, after the first question.
- Don't recommend without a reason taken from what the user said.
- Don't ask the same question twice. If a reply was unclear, ask once in plain prose.
- Don't run a quiz for a single small clarification. Just ask it in a sentence.

## Escalation to /squiz

Picker previews cover most visual choices, so stay in `/quiz` where you can. Offer
`/squiz` in one sentence, and don't switch on your own, when there are more than 7
questions, or when the options need a side-by-side comparison bigger than a short
preview:

> "This one's easier to pick if you can see the layouts side by side. Want a full Squiz
> for just the visual decisions? Otherwise I'll keep going here."
