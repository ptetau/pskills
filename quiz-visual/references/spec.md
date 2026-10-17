# The spec file

The spec is one JSON file, `<name>.quiz.json`. `scripts/render_quiz.py` turns it into the
page. The renderer checks the spec first, and it stops with a list of errors when a rule
fails. `examples/summit-welcome.quiz.json` is a finished example.

## The page

| Field | Rule |
|---|---|
| `title` | The name of the page. Use 2 to 5 words, for example "Summit Welcome Email". |
| `intro` | One sentence of 25 words or fewer. Say what the user does on the page. |
| `task` | Optional. A short line that names the work. The page shows it above the title. |
| `questions` | A list of 1 to 10 questions, most important first. |

## A question

| Field | Rule |
|---|---|
| `id` | Lower-case words joined by hyphens. Each question has its own `id`. |
| `label` | 12 characters or fewer, for example "Tone". The page shows it in the list at the side. |
| `question` | One sentence of 25 words or fewer that ends with "?", in the words of the user. |
| `options` | A list of 2 to 5 options. |
| `multi` | Optional. Set it to `true` when the user can pick several options. |
| `evidence` | Required when an option is recommended. Give the words of the user that point to it. Do not set it otherwise. |

## An option

| Field | Rule |
|---|---|
| `id` | Lower-case words joined by hyphens. Each option of a question has its own `id`. |
| `label` | 1 to 5 words. |
| `text` | One sentence of 25 words or fewer. Say what the option gives, then say its cost after "but". Start with a noun, not with "It". |
| `recommended` | Optional. Set it to `true` for at most one option, and only with `evidence`. |
| `preview` | Required. An object with a `kind`. See `preview-kinds.md`. |

## The fields of each preview kind

Each preview also takes an optional `caption`: a short label under the preview.

| `kind` | Fields |
|---|---|
| `sample` | `frame` (`email`, `message`, `card`, `page`, or `plain`), `from`, `title`, `body` (1 to 4 paragraphs), `action` (the text of a button) |
| `wireframe` | `frame` (`phone`, `browser`, `email`, or `none`), `rows` (1 to 10 rows) |
| `swatch` | `colors` (2 to 6 colours, each with `name`, `value` such as `#1a2b3c`, and `role`: `bg`, `ink`, `accent`, or `extra`), `sample` (a heading), `action` (a button) |
| `flow` | `steps` (2 to 7 steps, each with `label`, and optional `note`, `who`, and `emphasis`), `orientation` (`row` or `column`) |
| `code` | `language`, `code` (15 lines or fewer) |
| `svg` | `svg` (a picture that starts with `<svg`), `alt` |
| `html` | `html`, `css`, `height` (120 to 420), `alt`. It shows in a locked frame, with no script. |
| `demo` | `html`, `css`, `js`, `height` (120 to 420), `alt`. It shows in a locked frame, with script. |
| `none` | No other fields. The card shows words only. |

A wireframe row is a block name, an object with a `type` and an optional `label`, a
`cols` object, or a `grid` object. The block names are `header`, `nav`, `hero`, `image`,
`text`, `button`, `list`, `input`, `footer`, `chart`, `card`, `tabs`, `avatar`, and `map`.

```json
["header", {"type": "hero", "label": "Photo"}, {"cols": ["image", "text"], "ratio": [1, 2]},
 {"grid": 3, "item": "card"}, "button", "footer"]
```

A `flow` step has `who` set to `user`, `system`, or `staff`. The page draws each kind in
its own style. Set `emphasis` to `true` on the steps that make the options differ.

## The limits

- A `svg`, `html`, `css`, or `js` field has 20,000 characters or fewer.
- A preview cannot hold a web address. It cannot load anything from the network. The only
  exception is the `xmlns` namespace of an SVG.
- `html` and `demo` show in a locked frame. They cannot reach the page or the network.
