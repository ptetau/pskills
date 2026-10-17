---
name: squiz
description: >
  Visual clarifier in the form of a document. The Apple //e × IBM Plex "Squiz" Go binary
  renders the document. The agent writes a compact JSON spec (squizzes, options, and an
  optional spec narrative). Then the `squiz` CLI renders a self-contained, retro-styled,
  interactive HTML doc. The doc has mini-wireframe art for each option and a sticky
  `copy json` status bar. The user fills in the doc at their own pace and pastes one JSON
  payload back. The payload gives the path of the rendered file and an anchor for each
  decision. Thus, the agent can go back to the exact section that each answer is about.
  The binary assigns a theme to each repo automatically, in sequence, and saves the
  theme. Thus, each project gets a different identity. Use when the user says "/squiz" or
  "squiz this". Also use when the user asks for a richer, more designed visual version of
  /clarify-with-docs. The visual twin of /quiz (inline chat). Prefer /squiz when the task
  is high-stakes or when visual decisions are important.
---

# Squiz: JSON-in, HTML-out, Apple //e × IBM Plex

## Purpose

Squiz has the same intent as [[clarify-with-docs]]. Squiz collects all the clarifying
questions at the start. Then Squiz shows the questions in one rich, interactive document,
which the user fills in at their own pace.

Squiz is the **opinionated visual implementation** of this intent. The document has these
parts:

- Numbered "squiz cards".
- Optional inline spec text, with `{{markers}}` that link to the questions.
- Mini-wireframe art for each option.
- A sticky status bar at the bottom, which exports the answers as JSON.

Squiz has eight retro-terminal × editorial themes (paper / phosphor / amber / beige /
rose / ocean / forest / slate). The binary assigns a theme to each repo automatically, so
each project looks different.

Use Squiz for high-stakes clarification when the visual identity *is* part of the message.
Examples are a UX/UI brief, a product spec, and a decision about a design system. Also use
Squiz for any task where the user gets help from wireframe previews of the options.

## Writing

Write all text to `references/writing-guidelines.md`. This includes the replies to the
user, each question, and each file that this skill writes.

## When to use this vs. siblings

- **`/quiz`** (the inline chat twin): quick rounds, with one question in each chat turn.
  Use `/quiz` when the user wants speed, or when the user is on mobile.
- **`/clarify-with-docs`**: the same document pattern, but without a style. Use
  `/clarify-with-docs` when you do not want the retro style.
- **`/squiz`** (this skill): use `/squiz` when the visual identity is important, or when
  mini-wireframe previews help to show the options. Also use `/squiz` when the
  user explicitly asks for "squiz".

## The flow (3 phases, 1 binary)

### Phase 1 — Gather

1. Read the conversation, the memory, and the uploaded files.
2. Find each ambiguity that can materially change the output.
3. Aim for **3-12 questions**. If there are fewer questions, use `/quiz`. If there are
   more questions, the user will stop before the end.
4. Decide if the doc gets a **spec narrative** at the top. A spec narrative is a set of
   paragraphs, with `{{markers}}` that link down to the cards. Include a spec narrative
   only if you have real prose that you can quote. Do not include a spec narrative for a
   tighter squiz.

### Phase 2 — Write JSON, run the binary

1. Write a `<name>.json` file (see "JSON Schema (input)" below).
2. Run the renderer:

   ```bash
   squiz <name>.json
   ```

No other step is necessary. The `squiz` binary (installed with `go install` of
`<this-skill>/go-renderer`) reads the JSON and selects a theme for the repo (automatic,
in sequence, and saved). Then the binary writes `<name>.html` next to the JSON. If you
do not add a flag, the binary does **not** open the HTML automatically.

**When you tell the user the path, always give a clickable `file://` URL.** In most
terminals, a bare Windows path such as `C:\Users\…\foo.html` is not clickable. The URL
`file:///C:/Users/.../foo.html` is clickable. The POSIX form is `file:///home/u/foo.html`.
Use `--open` only if the user asked for an automatic browser launch. Even then, also print
the URL.

**Default file location:** Write `squiz.json`, or a named variant such as
`squiz-onboarding.json`, **next to the work that the squiz is about**. This location is
usually the project root or the applicable subdirectory. The binary writes the `.html`
next to the `.json`, with the same basename. Thus, you can always know the two paths
before the run.

### Phase 3 — User pastes back

The doc has a sticky **`copy json`** button at the bottom. Tell the user:

> "Click `copy json` at the bottom, paste it back here, and I'll continue."

When the user pastes the JSON, do these steps:

1. Parse the JSON (see "Export JSON shape" below). The JSON includes `source.file`, the
   absolute path of the rendered HTML. The JSON also has an `anchor` (`#squiz-<id>`) for
   each decision.
2. If necessary, use `source.file` and `anchor` to go back to the context of a decision.
3. Give your updated understanding again in plain prose.
4. Ask about each *new* gap in a plain chat follow-up. Do NOT render a second squiz.
5. Start the work.

## JSON Schema (input)

```jsonc
{
  // OPTIONAL — leave omitted for auto-rotation per repo. Set explicitly to override.
  "theme":     "paper",        // paper|phosphor|amber|beige|rose|ocean|forest|slate
  "density":   "compact",      // compact|comfortable  (default compact)
  "scanlines": false,          // CRT scanline overlay
  "cursor":    true,           // blinking cursor in the squiz wordmark

  "spec": {
    "path":  "/usr/specs/tide.md",          // shown in the topbar
    "title": "Tide — a habit tracker",      // page H1
    "lede":  "Eight decisions to lock in…", // one-line summary
    "paragraphs": [                          // OPTIONAL spec narrative
      { "text": "Users land on a {{onboarding}} the very first time…" }
    ]
  },

  "squizzes": [
    {
      "id":    "onboarding",                            // stable slug; appears in anchors
      "title": "First-launch experience",
      "desc":  "The first 60 seconds set expectations.",
      "quote": "the bar to 'doing the thing' should be embarrassingly low",
      "options": [
        {
          "id":    "jumpin",                              // stable slug
          "label": "Option A",                            // OPTIONAL — auto from index
          "name":  "Name one habit, go",                  // short display
          "desc":  "Single text field. No setup.",        // 1-2 sentence trade-off
          "art":   "wf:phone-input"                       // see Art forms below
        }
      ]
    }
  ]
}
```

## Art forms (the `art` field on each Option)

The `art` field has five forms. The binary finds the form from the content of the string.

### 1. `"art": "wf:<name>"` or `"art": "arch:<name>"` — named library

The binary contains two namespaces of curated, theme-aware SVG parts:

- **`wf:*`**: UI/UX wireframe parts (calendars, charts, avatars, phone screens, controls,
  status, typography, graphs, metaphors, misc). There are about 50 parts.
- **`arch:*`**: system-design and architecture parts (servers, databases, caches, queues,
  basic network parts, identities). There are about 30 parts.

To get the authoritative list, run `squiz catalog wf|arch|dsl`. The list gives a
description and the natural-box dimensions of each entry. The entries are PARTS to remix,
not pictures to select. With the `--json` flag, `squiz catalog` gives the `naturalBox` of
each entry. Thus, you can size the `<use>` references in a composed SVG without a guess.

### 2. `"art": "<dsl-string>"` — parametric DSL

The binary parses compact strings into themed SVG. These are the DSL forms:

| Form | Example | Renders |
|---|---|---|
| `grid:NxM[@RATE]` | `"grid:7x7@0.55"` | An N×M heatmap. RATE is in [0,1]. |
| `spark:[V,V,V,…]` | `"spark:[3,5,4,7,6,9,11]"` | A sparkline from the data. |
| `bars:[V,V,V,…]` | `"bars:[3,5,4,7,6,9,11]"` | A bar chart. |
| `swatches:#A,#B,…` | `"swatches:#f1ebde,#1a1814,#b34a1a"` | Palette swatches. |
| `pills:A*\|B\|C*` | `"pills:morning*\|midday\|evening*"` | A row of chips. `*` = active. |
| `sample:"text"[@FONT]` | `"sample:\"Quiet welcome back.\"@serif"` | Styled sample text. FONT = `serif`/`sans`/`mono`. |
| `circle-pack:N` | `"circle-pack:12"` | N circles in an organic arrangement. |
| `text:"line 1\nline 2"[@FONT][?size=N&align=A&weight=W&color=C]` | `"text:\"Quiet\\nwelcome back.\"@mono?size=18&align=center&weight=700&color=accent"` | Multi-line styled text (a richer sibling of `sample:`). FONT = `mono`/`serif`/`sans` (default `sans`). `size` 6-36 (default 14). `align` = `left`/`center`/`right` (default `left`). `weight` 300-700 (default 400). `color` = `ink`/`ink-2`/`ink-3`/`accent`/`rule`/`rule-2` (default `ink`). Use `\n` for more lines. |
| `flow:[a,b,c]` or `flow:[a?icon=user,b?icon=api,c?icon=database]` | `"flow:[client?icon=user,api?icon=api,db?icon=database]"` | A left-to-right pipeline of named boxes, with arrows between the boxes. The optional `?icon=<arch>` puts an arch icon in each box. |
| `box:label[?icon=ARCH]` | `"box:web-tier?icon=server"` | One labelled box, with an optional arch icon. |
| `arrow:"label"[?dir=DIR]` | `"arrow:\"async\"?dir=down"` | One labelled arrow glyph. `dir` = `right` (default) / `down` / `up` / `left`. |

### 3. `"art": "<raw svg>"` — escape hatch

If the library and the DSL do not fit, write raw SVG inline. The SVG must start with
`<svg`. Use CSS vars (`var(--accent)`, `var(--ink)`, `var(--ink-3)`, `var(--rule-2)`), so
that the SVG gets the active theme. To look the same as the other forms, use
`viewBox='0 0 100 60'` and `style='width:80%;height:auto'`.

### 4. `"art": "none"` — explicit hide

The value `none` removes the art slot fully, and the card collapses. Use `none` when **no
visual is applicable**. An example is a question about a name or a string, where art only
fills space.

### 5. `art` omitted / empty — auto per-letter abstract

The binary draws a subtle pattern from the position of the option: A = hatched,
B = dotted, C = striped, D = grid, E = cross-hatch, F = waves. The pattern looks
intentional, and you write no art. Use this form as the default when you work
fast and the visuals are not important.

> **Authoring preference (see Rule 5):** The default is to compose art from library parts.
> Use one library token alone only when one shape IS the picture.

## Theme (automatic by default, set only to override)

**Default behaviour:** The binary assigns one of 8 themes to each repo automatically, in
sequence. The binary saves each assignment in `~/.squiz/themes.json`. Each new repo gets
the next theme in the rotation. When you render again in the same repo, the binary always
uses the same theme. The repo key is the output of `git remote get-url origin`, if that
command gives a value. If not, the repo key is the absolute working directory.

**Precedence:**

1. The `--theme <name>` CLI flag (highest).
2. The `"theme"` field in the JSON.
3. The automatic theme from the repo cache.

**Generally**, do not put `theme` in the JSON, and let the binary select the theme. Set
`theme` only if you want a specific identity for one squiz. For example, use `phosphor`
for a decision about code or infrastructure.

The 8 themes:

| Theme | Look | Mode |
|---|---|---|
| `paper` | Cream, ink, and a rust accent. Editorial and calm. | light |
| `phosphor` | Green on black, like a CRT. | dark |
| `amber` | IBM 3279 amber on near-black. | dark |
| `beige` | PS/2 cream with IBM blue. | light |
| `rose` | Warm pink, plum ink, and a rose accent. | light |
| `ocean` | Pale blue-grey, deep teal, and a coral accent. | light |
| `forest` | Oat cream, moss, and warm gold. | light |
| `slate` | Cool dark grey, with an electric blue accent. | dark |

There are two optional toggles:

- `data-scanlines="on"` gives a CRT character. This toggle is best with `phosphor`,
  `amber`, or `slate`.
- `data-density="comfortable"` gives a layout with more space.

## Export JSON shape (what the user pastes back)

```json
{
  "spec": "Tide — a habit-tracking app",
  "source": {
    "file":     "C:\\Users\\User\\code\\tide\\squiz.html",
    "basename": "squiz.html"
  },
  "generatedAt": "2026-05-25T12:34:56Z",
  "decisions": [
    {
      "id":       "onboarding",
      "question": "First-launch experience",
      "anchor":   "#squiz-onboarding",
      "choice": {
        "id":      "jumpin",
        "name":    "Name one habit, go",
        "summary": "Single text field. No setup. Customize later."
      },
      "notes": "Use a placeholder hint that rotates each launch."
    }
  ],
  "summary": { "total": 8, "resolved": 8, "withNotes": 3 }
}
```

`source.file` is the absolute path of the rendered HTML. `anchor` is the `#squiz-<id>`
value. To go to a specific decision, add the `anchor` to the end of `source.file`.
`choice: null` means that the user skipped that decision. Treat a skipped decision as "you
decide", unless the `notes` of the decision say a different thing.

## CLI reference

```bash
squiz <input.json>                    # render <input>.html next to input
squiz render <input.json>             # same, explicit subcommand
squiz <input.json> --open             # also open in default browser
squiz <input.json> --theme phosphor   # force a specific theme
squiz <input.json> --out path.html    # explicit output path
squiz <input.json> --stdout > x.html  # write to stdout
squiz version
squiz help
```

## Installation (one-time)

```bash
cd ~/.claude/skills/squiz/go-renderer
go install .
```

The install puts `squiz` on `$GOPATH/bin`, which is usually on `$PATH`. To make sure that
the install worked, run `squiz version`.

## Accessibility (built into the renderer)

The rendered HTML has these accessibility features:

- A skip-to-decisions link.
- `radiogroup` ARIA roles for each squiz.
- Arrow-key navigation in each group.
- Enter or Space to select.
- Visible focus rings on all interactive controls.
- A modal focus trap, and return-focus on close.
- `aria-live` announcements of the progress.
- Correct `<label>` associations for the notes textareas.
- Support for `prefers-reduced-motion`.

The agent does no more work for accessibility.

## Rules

1. **One squiz per invocation.** If the answers show a new ambiguity, ask a follow-up in
   plain chat. Do not render a second squiz.
2. **3-12 questions** is the best range. If there are fewer questions, use `/quiz`. If
   there are more questions, the user stops before the end.
3. **Stable IDs.** Keep the squiz `id` and the option `id` stable, because the two IDs
   come back in the JSON. Select short kebab-case or camelCase slugs that will still have
   a clear meaning in a week.
4. **Omit `theme`**, unless you have a reason to override the theme. The automatic
   rotation gives the correct result.
5. **Art is a bespoke illustration that you compose from parts. The library is clipart,
   not finished pictures.**

   The `wf:`, `arch:`, and DSL items are **parts**. Remix the parts in a custom drawing,
   for example:
   - A labelled box with your own words.
   - An arrow that you draw between two icons.
   - A small drawing that shows the *specific* idea of this option.

   **The default mode is to compose. Write raw SVG that embeds one or more library
   references, and add your own text and connecting marks.**

   A single library token alone is a deliberate exception, not the norm.

   The mechanism to compose (v0.8.0+): to add a library shape, write
   `<use href="wf:phone-card" x="0" y="5" width="30" height="50"/>` in the raw SVG. The
   renderer inlines the shape as a `<symbol>`. Thus, you get a bespoke drawing with
   library parts. To find the size of a part, use `squiz catalog wf --json`. Each entry
   gives its `naturalBox`, so you can size each `<use>` box without a guess.

   **Select the type of diagram first, THEN compose.** The reader understands these six
   shapes at a glance:

   | Shape | When it fits | Typical recipe |
   |---|---|---|
   | **labeled-object** | one item with one important part | a wf or arch icon, and a callout that points at the part |
   | **flow** | a process or a path (request → ack, raw → cooked) | 2-4 boxes with arrows between them, and one box highlighted |
   | **contrast / vs** | before and after, this and that, chosen and rejected | two mini-panels with `divider:vs` between them |
   | **part-whole** | a scope, a subset, "this slice of that" | a container with one cell emphasised |
   | **metric-with-context** | a number that has a meaning only against a reference | a sparkline, a `baseline:N` reference line, and a label |
   | **typed-list** | a choice among siblings or named modes | `pills:a*\|b\|c*`, or N rows with one accent |

   **Visual budget at 100×60.** Use a maximum of four "ink events": one silhouette, one
   accent, one label of ≤6 characters, and one relationship line. If there are more, the
   eye cannot read the picture.

   Use one accent colour, in one position only. If two items have the accent, the two
   items do not show as accented. Keep about 30-40% of the viewBox empty. Put the parts
   off-centre, because a centred drawing looks decorative and an off-centre drawing looks
   informative.

   **Authoring checklist.** Do these checks before you decide on each art form:
   1. **Caption it.** In one sentence, say what the picture that you will write actually
      shows.
   2. **Key-noun match.** Make sure that the caption uses at least two load-bearing
      nouns or verbs from the desc. For example, if the desc says *"hot path: browser →
      cache → db, 50ms p99"*, the caption must say browser/cache/db/50ms.
   3. **Sibling diff check.** Is the option one of N options in a chooser? If so, can you
      justify the same single token on each option? If yes, your art is not sufficiently
      specific.
   4. **Compose-vs-single test.** Ask this question: can a label, an arrow, or a second
      icon make the picture more specific? If yes, compose. If the single part truly IS
      the picture, a single token is correct.
   5. **"None" check.** After these checks, if the best art is a generic library icon, use
      `"art": "none"`. Generic decoration is worse than no art.

   **A single library token alone is correct only when the part IS the picture.** These
   are the three correct uses:
   - `text:"systemctl enable\nclipsi.service"@mono?size=10&color=accent`: the literal
     command IS the item.
   - `pills:M*|T|W*|T|F*|S|S`: the three lit days ARE the desc "3× / week".
   - `wf:calendar-grid` alone: use it only when the option is literally about a calendar
     grid.

   If you want to use one library token, complete this sentence: "the picture I want to
   draw IS this exact icon, alone, with no label." If you cannot say that sentence,
   compose.

   **Anti-patterns (do not do these):**
   - Two options in a chooser have the same `art`. If sibling options have the same icon,
     the icon has no meaning. The validator gives the warning `sibling-art-collision`.
   - A generic `arch:user` / `arch:server` / `arch:database` when the desc names a
     specific item. Give the icon a label, or compose a drawing around the icon.
   - The default fallback art stays, but 30 seconds of work to compose can show a
     concrete idea. The validator gives the warning `composition-thin` for each section.
   - Decoration that "looks plausible", but uses no key nouns from the desc.
6. **Spec narrative is optional.** Include a spec narrative only when you have real prose
   to quote, with `{{markers}}` that map to squizzes.
7. **The `quote` field on a squiz is optional.** Use the `quote` field when you can point
   to a specific spec line that is the reason for the question.
8. **Self-contained.** Try to write the doc so that the doc makes sense to a user who
   opens the doc cold. `SPEC_LEDE` is the one-line summary that does this work.
9. **Clickable links.** When you give the user the rendered file, write the path as a
   `file://` URL (`file:///C:/Users/.../foo.html` on Windows). A bare path is not
   clickable, but a URL is clickable.
10. **Recommend when you have a real preference.** Each option can have
    `"recommendation": "<one or two sentences explaining why>"`. The renderer shows a
    `★ RECOMMENDED` chip, and shows the explanation as an editorial callout.

    Use a recommendation when the spec, the constraints, or the audience really point at
    one option. Do NOT mark all options as recommended. Do not add filler to the
    explanation.

    If you cannot justify the pick in one sentence, the recommendation is not earned, and
    you leave the recommendation off. An example of a good sentence is "The $5-VPS
    constraint (OVR-3) excludes k8s, so the choice is systemd or Docker, and systemd has
    one fewer moving part". Give a maximum of one recommendation for each squiz/item.

## Files in this skill

- `SKILL.md`: this file.
- `go-renderer/`: the Go module that becomes the `squiz` binary when you install it.
  - `main.go`, `schema.go`, `render.go`, `theme.go`, `art.go`, `dsl.go`, `wf.go`,
    `browser.go`, `strbuilder.go`
  - `templates/index.html.tmpl` and `templates/styles.css`: the binary embeds these files
    with `//go:embed`.
  - `testdata/smoke.json`: a reference fixture that uses all the art forms.
