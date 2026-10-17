---
name: quiz-visual
description: >
  Asks the user the questions on one HTML page, not in the chat. Each option shows its
  result with a graphic, a sample, a wireframe, a palette, a flow, or a small clickable
  demo. The user picks what they see. Works as a plain file with copy-and-paste answers,
  and as a live Artifact in the Claude app that sends the answers back. Plans a fixed list
  of questions first. Recommends an option only on evidence from the words of the user.
  The visual twin of /quiz. Use when the user says "/quiz-visual", "show me the options",
  "quiz me visually", or "visual quiz". Also use when the questions are about how
  something looks, sounds, or works.
---

# Quiz Visual: Show, Do Not Tell

## Purpose

`/quiz-visual` gets the decisions that matter before the work starts. It puts all the
questions on one HTML page. Each option on the page shows its result. The user picks what
they see, and does not read a description.

The rule of this skill is **show, do not tell**. When two options differ in how they look,
sound, or work, show the difference. The words of an option name the option and give its
cost. The preview gives everything else.

Use `/quiz-visual` in these conditions:

- The options differ in how they look, sound, work, or are shaped. Examples are a tone, a
  layout, a colour scheme, a flow, or the shape of data.
- There are 3 to 10 questions, and the user gains from seeing them together.

Use `/quiz` in these conditions:

- Words answer the question, for example a name, a date, a yes or no, or a short list.
- The user is on a screen that cannot open a page.

## Writing

Write all text by the rules in `references/writing-guidelines.md`. This includes the
replies to the user, the text of each question and option, and each file that this skill
writes. A preview shows the real words, colours, and names of the work. Those are not
prose of this skill, so the writing rules do not change them.

## Step 1: Plan the questions

The same request must get the same questions. Before you write the page, make the full
list with this procedure. Then keep to the list.

1. Examine these dimensions, in this order: purpose and audience, style, scope, focus, and
   next step.
2. Ask about a dimension only if the request leaves it open **and** the answer changes the
   work. Do not ask about anything that the request already decides.
3. Put the most important questions first. Ask a maximum of 10 questions.
4. Commit to the list. The page shows each question one time, and the user answers them
   all together. Do not add a question after the page is out.

**Recommend only on evidence.** Mark an option as recommended only when the user said
something that points to the option. Write that evidence in the `evidence` field, in the
words of the user. If nothing that the user said favours an option, recommend nothing. Do
not recommend two options.

## Step 2: Choose a preview for each option

Read `references/preview-kinds.md` first. It tells you how to build each kind.

For each option, choose the lightest preview that shows what the options of the question
differ in:

| The options differ in | Use this preview |
|---|---|
| Words, voice, names, or copy | `sample`, with the real words in a frame |
| Where things go on a screen | `wireframe` |
| Colour | `swatch`, with a small sample in those colours |
| Order of steps, or who does what | `flow` |
| The shape of data, a command, or an interface | `code` |
| A picture that none of the above can draw | `svg` |
| A look that needs real HTML and CSS | `html`, in a locked frame |
| How something behaves when the user acts | `demo`, a small clickable prototype |
| Meaning only, with no difference to see | `none` |

Follow these rules:

1. Use the same kind of preview for each option of one question, so the user compares like
   with like.
2. Use real content. Write the real words, the real colours, and the real names of this
   work. Do not write "Option A text" or filler.
3. One preview shows one idea. If a preview needs a caption to say what it means, make
   the preview clearer.
4. Use a `demo` only when behaviour is the difference. A demo must work with one click.
5. Use `none` for a question only when the options do not differ in how they look, sound,
   or work. The checker warns when a question has no preview.

## Step 3: Write the spec

Write the questions as one JSON file, `<name>.quiz.json`, in the working directory. The
format is in `references/spec.md`, and a finished example is in
`examples/summit-welcome.quiz.json`.

For each option, write one sentence of 25 words or fewer. Say what the option gives, then
say its cost after "but". Do this for every option, the first question included.

## Step 4: Render and check

1. Render the page:
   `python3 <skill-folder>/scripts/render_quiz.py <name>.quiz.json -o <name>.quiz.html`
2. Check the spec and the page:
   `python3 <skill-folder>/scripts/check_quiz.py <name>.quiz.json <name>.quiz.html`
3. Fix each `ERROR` and each `WARN` in the spec. Render and check again until the checker
   shows `PASS` and `0 writing warnings`.
4. Do not edit the HTML by hand. Edit the spec, and render again.
5. If the session has a browser, look at the page one time. Check that each preview shows
   what you meant, and that no text is cut off.

## Step 5: Give the page to the user

Always write the file. Also publish a live page when the session can.

1. **The file.** Tell the user the path of `<name>.quiz.html`. The page opens in any
   browser. The user answers, presses **Copy answers**, and pastes the result into the chat.
2. **The live page.** If the session has the Artifact tool, render the Artifact form:
   `python3 <skill-folder>/scripts/render_quiz.py <name>.quiz.json -o <name>.quiz.artifact.html --artifact`
   Then publish that file with the Artifact tool. Pass `capabilities: {"db": {}}`, the icon
   `quiz`, and a one-sentence description. Follow the rules that the Artifact tool gives.
   The page then shows **Send answers to the agent**, and the answers go to the `db`.
3. Tell the user in two sentences how to answer and what to do at the end. Then stop and
   wait. Do not ask the questions again in the chat.

## Step 6: Read the answers

1. If the user pasted JSON, read it.
2. If the user says that they sent the answers, read the document `answers` in the
   collection `quiz`. Use the `ArtifactData` tool, the action `get`, and the URL of the
   page. If the document is missing, ask the user to press **Send answers** again, or to
   paste the answers.
3. Make sure that `summary.answered` equals `summary.total`. If not, ask the user to
   finish the page.
4. Show each answer in one line, in order, with these forms:

| The user | Line |
|---|---|
| picked one option | `✓ 2/4 Tone → Warm` |
| picked one option and wrote a note | `✓ 2/4 Tone → Warm (note: keep it short)` |
| picked several options | `✓ 5/5 Extras → Opening hours, Gear prices` |
| pressed **You decide**, and an option was recommended | `✓ 2/4 Tone → Stoked (you decided: recommended)` |
| pressed **You decide**, and no option was recommended | `✓ 2/4 Tone → Stoked (you decided: first option)` |

5. Write one short paragraph on what the answers mean, for example "So I will write X,
   with Y, and without Z". Then start the work. Pressing **Send** or pasting the answers
   is the OK, so do not ask for a second confirmation.

The answers have this shape. For a question with several choices, `choice` is `null` and
`choices` lists them. For **You decide**, `deferred` is `true` and `decidedBy` is
`recommended` or `first option`.

```json
{
  "quiz": "Summit Welcome Email",
  "task": "A welcome email for new members",
  "generatedAt": "2026-10-17T09:30:00.000Z",
  "answers": [
    {
      "id": "tone", "label": "Tone", "question": "What tone suits the welcome email?",
      "choice": { "id": "warm", "label": "Warm" }, "choices": null,
      "note": "Keep it short.", "deferred": false, "decidedBy": null
    }
  ],
  "summary": { "total": 5, "answered": 5, "deferred": 0, "withNotes": 1 }
}
```

## What not to do

- Do not use words for what a preview can show.
- Do not use filler text or placeholder names in a preview.
- Do not recommend an option without evidence from the words of the user.
- Do not ask more than 10 questions.
- Do not put a web address in a preview. The page cannot load anything from the network,
  and the fonts are the only exception.
- Do not edit the rendered HTML by hand.
- Do not ask the same questions again in the chat after the page is out.

## Files in this skill

- `references/spec.md`: the format of the spec file.
- `references/preview-kinds.md`: how to build each kind of preview.
- `references/page-template.html`: the page. The renderer fills it.
- `scripts/render_quiz.py`: renders a spec as a page.
- `scripts/check_quiz.py`: checks the spec, the words, and the page.
- `scripts/test_quiz_visual.py` and `scripts/test_page_browser.js`: tests of the scripts and
  of the page.
- `examples/summit-welcome.quiz.json` and `.quiz.html`: a finished example.
