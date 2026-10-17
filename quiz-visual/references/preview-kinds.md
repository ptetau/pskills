# How to build a preview

A preview shows an option. The user looks at the preview, and the user does not read about
it. Choose the lightest kind that shows how the options of one question differ.

## sample: real words in a frame

Use `sample` when the options differ in words: a tone, a name, a message, or a title.
Write the real copy that the work will have. Do not write a description of the copy.

- Use the same `frame` for each option, so the user compares the words and not the frames.
- Write 1 to 4 short paragraphs. Keep the real length, because length is part of the tone.
- Give the button the real label, for example "Book your first climb".

```json
{"kind": "sample", "frame": "email", "from": "Summit Climbing", "title": "Welcome to Summit",
 "body": ["We are glad that you joined us.", "Take your time."], "action": "Plan your first visit"}
```

## wireframe: where things go

Use `wireframe` when the options differ in layout. The page draws grey blocks in a phone,
a browser, or an email. Use the same blocks and the same frame for each option. Change only
the arrangement.

- Name a block by what it holds in `label`, for example "Photo". Do not label every block.
- Use `cols` for side by side, and `grid` for a repeated block.
- Use 4 to 8 rows. A wireframe with more rows is hard to read at card size.

## swatch: colour

Use `swatch` when the options differ in colour. Give 3 to 5 colours. Set the `role` of the
page colour (`bg`), the text colour (`ink`), and the button colour (`accent`). The page
draws a small sample in those colours, so the user sees the colours working together.

- Choose colours that work together. Do not show a rainbow.
- Write the real colour names of the work, for example "Chalk", not "Colour 1".

## flow: order and ownership

Use `flow` when the options differ in the order of steps or in who does a step. Use 3 to 5
steps. Set `who` on each step, and set `emphasis` on the steps where the options differ.
A flow of more than 3 steps shows as a column.

## code: the shape of data, a command, or an interface

Use `code` for the shape of a record, a command, or an API. Use 15 lines or fewer. Show
the real names. Use the same style for each option.

## svg: a picture

Use `svg` for a picture that no other kind can draw: a map, a chart, an icon, or a diagram.

- Start with `<svg` and give a `viewBox`. The page shows the picture as an image, so a
  script in it cannot run.
- Draw on a light ground. The mat of the preview is light in both themes.
- Write an `alt` of one sentence that says what the picture shows.

## html: a mockup in a locked frame

Use `html` when you need real HTML and CSS: a small screen, a form, a table, or a card.
The frame is locked. It has no script, and it cannot reach the page or the network.

- Write the `css` in the `css` field. Use system fonts.
- Set a `height` from 120 to 420 that fits the content with no scroll.
- Write an `alt` of one sentence.

## demo: a prototype that the user clicks

Use `demo` only when the options differ in behaviour. Examples are a control, a transition,
or a flow of two screens. The user clicks the demo in the card.

- One idea, one click. The demo shows its result after one action.
- Show a clear start state, and make each clickable item look clickable.
- Write the real labels and the real messages of the work.
- Keep the `js` short, under 1,500 characters when you can. Use plain script, with no
  library.
- The demo runs in a locked frame with script. It has no network and no storage. It cannot
  reach the page.
- Write an `alt` of one sentence that says what the demo does.

```json
{"kind": "demo", "alt": "A button. Clicking it shows the booking page that opens next.", "height": 200,
 "html": "<button id=\"go\">Book my intro class</button><p id=\"m\"></p>",
 "css": "#go{padding:10px 16px;border:0;border-radius:999px;background:#1b2030;color:#fff}",
 "js": "document.getElementById('go').onclick=function(){document.getElementById('m').textContent='The booking page opens.'}"}
```

## none: words only

Use `none` when the options differ in meaning and not in how they look, sound, or work.
Examples are a yes or no, a budget, and a date. The checker warns when a question has no
preview at all. Make sure that no preview can show the difference before you ignore it.

## Check each preview

- The user can tell the options apart at a glance, with no text from you.
- The preview uses the real content of the work.
- The preview has the same size and style as the other previews of its question.
- The `text` of the option tells the cost, and does not repeat what the preview shows.
