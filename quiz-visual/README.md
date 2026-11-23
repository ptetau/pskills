# `/quiz-visual` — Visual Clarifier Page

`/quiz-visual` asks the questions on one HTML page. Each option shows its result, so the
user picks what they see. The rule is **show, do not tell**. Each kind of difference has its
own preview:

- A tone is a sample of the real words.
- A layout is a wireframe.
- A colour scheme is a palette in use.
- A flow is a diagram.
- A behaviour is a small prototype that the user clicks.

**Example**

```
/quiz-visual a welcome email for new members of my climbing gym
```

The skill plans a fixed list of questions, writes them as `<name>.quiz.json`, and renders
`<name>.quiz.html` with `scripts/render_quiz.py`. The checker `scripts/check_quiz.py` makes
sure that the page is complete and that the words follow the writing guidelines.

The user opens the page in any browser and answers. A sticky list shows the progress. Each
question has a note field and a **You decide** button. At the end, **Copy answers** puts the
answers on the clipboard, and the user pastes them into the chat. In the Claude app, the
skill also publishes the page as an Artifact. The page then has a **Send answers to the
agent** button, and the skill reads the answers itself.

The page follows the theme of the system, in light and in dark. The page works on a phone.
A finished example is in `quiz-visual/examples/summit-welcome.quiz.html`.

Usually, use `/quiz` when words answer the question, for example a name or a date. Use
`/quiz-visual` when the options differ in how they look, sound, or work.
