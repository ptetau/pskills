---
name: quiz
description: >
  Quick inline chat clarifier with the Apple //e × IBM Plex "Squiz" terminal
  aesthetic. Renders ONE question at a time as a compact ASCII question card
  in the chat — the user replies with a single option letter (e.g. "B" or
  "B, with notes: …"), the agent echoes the resolved line, then immediately
  renders the next question. Never stack multiple questions in one message.
  The inline-chat twin of /squiz (which renders a full visual document for
  offline-style fill-in). Use when the user says "/quiz", "quiz me", "ask me
  a few questions", or signals they want a fast back-and-forth rather than a
  rendered document. Prefer /quiz over /squiz when there are only ~1-7
  questions, when the user is on mobile, when speed matters, or when the
  questions are mostly textual.
---

# Quiz: Inline Terminal-Styled Clarifier

## Purpose

`/quiz` is the inline-chat twin of [[squiz]]. Same job — gather clarifications before doing work — but rendered as compact text-mode "cards" inside the chat instead of a full interactive document. The aesthetic is the same retro Apple //e × IBM Plex terminal: monospace code blocks, `[?]` / `[✓]` markers, `// notes` callouts, numbered/lettered options.

Use `/quiz` when:
- There are roughly **1-7 small questions**, asked **one per turn**.
- The user is **on mobile** or wants quick back-and-forth.
- The questions are **mostly textual** (tone, scope, name) — no visual options to compare.
- The user signals speed ("ask me real quick", "couple of questions").

Use `/squiz` instead when:
- There are 8+ questions and the user benefits from seeing them all at once.
- Options need **visual previews** (wireframes, sample layouts, chart types).
- The user explicitly asks for "the doc", "the form", or "/squiz".

When in doubt, default to `/quiz`. It costs less, ships sooner, and the user can always escalate by saying "give me the full squiz".

## The look (this matters)

Every question is rendered as its own fenced code block styled like a terminal worksheet. **One question per message, always** — never stack two cards in the same turn. Keep it tight and consistent — the aesthetic is half the appeal.

### The question card

````
```
┌─ quiz · 01/03 ───────────────────────────────────────┐
│ [?] How should the welcome screen greet a user?      │
│     why it matters: sets tone for the whole app      │
└──────────────────────────────────────────────────────┘

  A · plain (recommended)   Says the goal straight ("Pick a habit to
                             start") — fits a utility app where users
                             want speed over small talk, and it's the
                             safest default for a first-run screen.
  B · warm                  Greets before asking ("Hey — glad you're
                             here...") — worth it if retention depends
                             on emotional buy-in, at the cost of an
                             extra beat before the user can act.
  C · playful                Light tone with emoji ("First habit
                             incoming...") — suits a casual audience,
                             but risks feeling flippant for anyone
                             using this for serious habit-tracking.

  // reply: A | B | C    (optional: add a note after the letter)
```
````

Each option is one fluid sentence: **what** it does, **why** it fits the situation just described, **how** it plays out in practice (the cost or benefit the user actually feels). One option carries `(recommended)` — see Rule 5.

Then on the next chat line, in plain prose, a single sentence: *"Pick A, B, or C — or reply `B, with notes: …` if you want to add detail."*

The `01/03` counter shows the user where they are in the sequence — increment it as you go (`02/03`, `03/03`).

### The rhythm (between questions)

After each reply, echo a one-line `[✓]` confirmation for the just-answered question, then *immediately* render the next card in the same message. The flow looks like:

```
turn 1 — agent: render Q1 card + reply hint
turn 2 — user: "B"
turn 3 — agent: "[✓] 01 audience → B · investors"  then Q2 card + reply hint
turn 4 — user: "A, with notes: skip metrics slide"
turn 5 — agent: "[✓] 02 length → A · ≤10 slides (note: skip metrics)"  then Q3
…
final  — agent: full resolved summary + "say `wait` if anything's wrong"
```

### Final resolved view (after the last question)

After the user answers the LAST question, restate the whole set with `[✓]` markers so they can spot a mistake before you proceed:

```
[✓] 01 audience  → B · investors
[✓] 02 length    → A · ≤10 slides   (note: skip metrics slide)
[✓] 03 tone      → C · punchy        (note: no jokes)
```

Then in one plain sentence: *"Going with these — say `wait` if anything's wrong, otherwise I'll start."*

## Rules of the look

1. **Always use a fenced code block** for the question cards. Monospace is the aesthetic — it must render as a code block, not prose with hyphens.
2. **Top border with `quiz · NN/NN`** as the marker. Lowercase. Use box-drawing characters (`┌─┐│└┘`) for the question header; plain ASCII for the rest.
3. **`[?]` for open, `[✓]` for resolved.** Match the squiz convention exactly.
4. **Options as `A · short-label`, then one fluid sentence** covering what the option does, why it fits the problem just described, and how it plays out in practice — the concrete cost or benefit, not a vague gesture at "trade-offs." Two-space indent, wrap continuation lines with a hanging indent. **Draw the card at ≈80% of the terminal width** — the top border and the wrapped option text should fill about four-fifths of the available columns, not a narrow column. When the terminal width is unknown, assume a wide desktop terminal and draw at ~96 cols; keep a ~48-col floor so narrow/mobile terminals still render. (The sample cards in this doc are drawn narrow to fit the page — widen them on render.)
5. **Mark exactly one option `(recommended)`** whenever you have enough context to judge — never a coin-flip default. The reasoning must live inside that option's sentence and name the specific problem, constraint, or goal that makes it the practical choice here. If it's a genuine toss-up, skip the tag rather than force one.
6. **Optional `why it matters:` line** under the question — one short clause, only when the user benefits from knowing the consequence.
7. **`// reply:` hint at the bottom** of every card, with the comment slash to match the squiz `//` accent.
8. **One question per turn — never stack.** Each card lives in its own message. Wait for the user's reply before rendering the next.
9. **Cap at ~7 questions total.** If you need more, switch to `/squiz` instead.
10. **No emojis** in the cards themselves (except as actual sample content, like option text). The aesthetic is text-mode.

## Flow

1. User triggers `/quiz` or says something like "ask me quickly".
2. Agent identifies all the questions that matter (max ~7; if more, switch to `/squiz` and tell the user). Internally decides an order — most-load-bearing first.
3. Agent renders the **first question only** as a code block — each option a what/why/how sentence, one marked `(recommended)` per Rule 5 — followed by a one-sentence plain-prose reply hint. Counter shows `01/N`.
4. User replies with a single letter, optionally with notes.
5. Agent echoes a one-line `[✓]` confirmation for that question, then *immediately* renders the next question card in the same message.
6. Repeat 4–5 until the last question is answered.
7. After the last reply, agent echoes the full resolved view (all `[✓]` lines stacked) and asks for confirmation in one sentence.
8. If confirmed, agent restates the *implication* in one short paragraph ("So I'll build X, skipping Y, with tone Z") and begins.
9. If a reply reveals a new ambiguity, ask **one** follow-up — plain prose, no card. Don't render another card for a single straggler.

## Reply parsing

Be permissive. Accept any of:

- `A` / `a` / `Option A` — straight pick
- `B, with notes: skip the metrics slide` — pick with a note
- `B (skip the metrics)` — pick with a parenthetical note
- `skip` / `you decide` / `n/a` / "go with your pick" — defer to the option already marked `(recommended)` on that card

If the user types free prose instead of a letter ("yeah do the warm one"), match it to the closest option and confirm in your echo. If they answer multiple questions at once anyway (e.g. `1c2a3b4b`), accept it gracefully — parse the run, echo all the `[✓]` lines in order, and move straight to the implication or the next unanswered question.

## Internal JSON (for parity with /squiz)

Track answers internally in the same shape `/squiz` exports, so the user can mix the two flows. You don't need to show this to the user — but if they ask for "the squiz JSON" after a quiz round, produce:

```json
{
  "spec": "<short task summary>",
  "generatedAt": "<ISO timestamp>",
  "decisions": [
    {
      "id": "audience",
      "question": "Audience for the deck?",
      "choice": { "id": "investors", "name": "investors", "summary": null },
      "notes": null
    }
  ],
  "summary": { "total": 3, "resolved": 3, "withNotes": 1 }
}
```

A `null` `choice` means the user skipped that decision.

## What NOT to do

- Don't stack two question cards in one message. Always one per turn.
- Don't render questions as a markdown table — the box-drawing characters and code-block monospace are the look.
- Don't use bold/italic markdown inside the cards — the code block won't render formatting; rely on layout instead.
- Don't apologize for the format or explain the aesthetic. Just render.
- Don't render a quiz card every time you need clarification — that's overkill. Use it when you have a real cluster of decisions to lock in, the same trigger that warrants a `/squiz`.
- Don't ask the same question twice. If a reply was ambiguous, ask once in plain prose to clarify, then move on.

## Escalation to /squiz

If, mid-quiz, you realize the question is more visual than expected ("actually you should *see* these options"), tell the user in one sentence and offer to switch:

> "This one's easier to pick if you can see the layouts — want me to render a full Squiz for just the visual decisions? Otherwise I'll keep going text-only."

Don't auto-escalate. Let the user choose.
