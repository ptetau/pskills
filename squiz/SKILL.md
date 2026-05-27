---
name: squiz
description: >
  Visual document-style clarifier rendered by the Apple //e × IBM Plex "Squiz"
  Go binary. The agent writes a compact JSON spec (squizzes, options, optional
  spec narrative); the `squiz` CLI renders a self-contained, retro-styled
  interactive HTML doc with mini-wireframe option art and a sticky `copy json`
  status bar. The user fills it in at their own pace and pastes a single JSON
  payload back. The payload carries the rendered file path + per-decision
  anchors so the agent can navigate back to the exact section the user was
  responding to. Theme is auto-assigned per repo (sequential, persisted) so
  each project gets a distinct identity. Use whenever the user says "/squiz",
  "squiz this", or asks for a richer, more designed-feeling visual version of
  /clarify-with-docs. The visual twin of /quiz (inline chat). Prefer it when
  the task is high-stakes or visual decisions matter.
---

# Squiz: JSON-in, HTML-out, Apple //e × IBM Plex

## Purpose

Same intent as [[clarify-with-docs]] — gather every clarifying question up front and render them as one rich interactive document the user fills in at their own pace. Squiz is the **opinionated visual implementation**: numbered "squiz cards", optional inline spec text with `{{markers}}` linking to questions, mini-wireframe option art, and a sticky bottom status bar that exports as JSON. Eight retro-terminal × editorial themes (paper / phosphor / amber / beige / rose / ocean / forest / slate), auto-assigned per repo so every project feels distinct.

Use it for high-stakes clarification where the visual identity *is* part of the message: a UX/UI brief, a product spec, a design system call, anything where the user benefits from seeing wireframe previews of their options.

## When to use this vs. siblings

- **`/quiz`** (inline chat twin) — quick rounds, one question per turn in chat. Use when the user wants speed or is on mobile.
- **`/clarify-with-docs`** — same document-style pattern, but unstyled. Use when you don't want the retro flavor.
- **`/squiz`** (this skill) — when the visual identity matters, when options benefit from mini-wireframe previews, or when the user explicitly asks for "squiz".

## The flow (3 phases, 1 binary)

### Phase 1 — Gather

Review the conversation, memory, uploaded files. Identify every ambiguity that could materially change the output. Aim for **3-12 questions**. Fewer → use `/quiz`. More → the user will bail.

Decide whether to include a **spec narrative** at the top (paragraphs with `{{markers}}` linking down to cards) — only if you have real prose you can quote. Skip it for tighter squizzes.

### Phase 2 — Write JSON, run the binary

Write a `<name>.json` file (see Schema below), then invoke the renderer:

```bash
squiz <name>.json
```

That's it. The `squiz` binary (installed via `go install` of `<this-skill>/go-renderer`) reads the JSON, picks a theme for the repo (auto, sequential, persisted), and emits `<name>.html` next to the JSON. With no extra flag it does **not** auto-open.

**Always hand the user a clickable `file://` URL** when you tell them the path. Bare Windows paths like `C:\Users\…\foo.html` aren't clickable in most terminals; `file:///C:/Users/.../foo.html` is. POSIX form: `file:///home/u/foo.html`. Use `--open` only when the user has asked for automatic browser launch — and even then, still print the URL alongside.

**Default file location:** write `squiz.json` (or a named variant like `squiz-onboarding.json`) **next to the work the squiz is about** — typically the project root or the relevant subdirectory. Output `.html` lands next to the `.json` with the same basename. Both paths are deterministic.

### Phase 3 — User pastes back

The doc has a sticky **`copy json`** button at the bottom. Tell the user:

> "Click `copy json` at the bottom, paste it back here, and I'll continue."

When they paste, parse it (see "Export JSON shape" below) — the payload includes `source.file` (absolute path to the rendered HTML) and per-decision `anchor` (`#squiz-<id>`). Use these to navigate back to context if needed. Restate your updated understanding in plain prose, ask any *new* gaps as plain chat follow-ups (do NOT render a second squiz), then start the work.

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

Five shapes, detected from the string content:

### 1. `"art": "wf:<name>"` or `"art": "arch:<name>"` — named library

Two namespaces of curated, theme-aware SVG parts baked into the binary:

- **`wf:*`** — UI/UX wireframe parts (calendars, charts, avatars, phone screens, controls, status, typography, graphs, metaphors, misc) — ~50 items
- **`arch:*`** — system-design / architecture parts (servers, databases, caches, queues, network primitives, identities) — ~30 items

Run `squiz catalog wf|arch|dsl` for the authoritative list with descriptions and natural-box dimensions — these are PARTS to remix, not pictures to pick from. The catalog's `--json` flag reports each entry's `naturalBox` so you can size `<use>` references in composed SVG without guessing.

### 2. `"art": "<dsl-string>"` — parametric DSL

Compact strings the binary parses into themed SVG. Primitives:

| Form | Example | Renders |
|---|---|---|
| `grid:NxM[@RATE]` | `"grid:7x7@0.55"` | N×M heatmap, RATE in [0,1] |
| `spark:[V,V,V,…]` | `"spark:[3,5,4,7,6,9,11]"` | sparkline from data |
| `bars:[V,V,V,…]` | `"bars:[3,5,4,7,6,9,11]"` | bar chart |
| `swatches:#A,#B,…` | `"swatches:#f1ebde,#1a1814,#b34a1a"` | palette swatches |
| `pills:A*\|B\|C*` | `"pills:morning*\|midday\|evening*"` | chip row, `*` = active |
| `sample:"text"[@FONT]` | `"sample:\"Quiet welcome back.\"@serif"` | styled sample text, FONT = `serif`/`sans`/`mono` |
| `circle-pack:N` | `"circle-pack:12"` | N organically-arranged circles |
| `text:"line 1\nline 2"[@FONT][?size=N&align=A&weight=W&color=C]` | `"text:\"Quiet\\nwelcome back.\"@mono?size=18&align=center&weight=700&color=accent"` | multi-line styled text (richer sibling of `sample:`). FONT = `mono`/`serif`/`sans` (default `sans`). `size` 6-36 (default 14). `align` = `left`/`center`/`right` (default `left`). `weight` 300-700 (default 400). `color` = `ink`/`ink-2`/`ink-3`/`accent`/`rule`/`rule-2` (default `ink`). Multi-line via `\n`. |
| `flow:[a,b,c]` or `flow:[a?icon=user,b?icon=api,c?icon=database]` | `"flow:[client?icon=user,api?icon=api,db?icon=database]"` | left-to-right pipeline of named boxes connected by arrows; optional `?icon=<arch>` embeds an arch icon in each box |
| `box:label[?icon=ARCH]` | `"box:web-tier?icon=server"` | single labeled box with optional arch icon |
| `arrow:"label"[?dir=DIR]` | `"arrow:\"async\"?dir=down"` | standalone labeled arrow glyph; `dir` = `right` (default) / `down` / `up` / `left` |

### 3. `"art": "<raw svg>"` — escape hatch

When library + DSL don't fit, inline raw SVG starting with `<svg`. Use CSS vars (`var(--accent)`, `var(--ink)`, `var(--ink-3)`, `var(--rule-2)`) so it inherits the active theme. Use `viewBox='0 0 100 60'` and `style='width:80%;height:auto'` to match the other forms visually.

### 4. `"art": "none"` — explicit hide

Drops the art slot entirely. Card collapses. Use when **no visual is appropriate** (e.g. a name/string question where art would be padding).

### 5. `art` omitted / empty — auto per-letter abstract

Subtle patterns based on option position: A = hatched, B = dotted, C = striped, D = grid, E = cross-hatch, F = waves. Looks intentional without authoring. Use as the default when you're moving fast and the visuals don't matter.

> **Authoring preference (see Rule 5):** composition with library parts is the default; single library tokens only when one shape IS the picture.

## Theme (auto by default — don't set unless overriding)

**Default behavior:** the binary auto-assigns one of 8 themes per repo, sequentially, persisted in `~/.squiz/themes.json`. Each new repo gets the next theme in rotation. Re-renders of the same repo always get the same theme. Repo key = `git remote get-url origin` if available, else the absolute working directory.

**Precedence:**
1. `--theme <name>` CLI flag (highest)
2. `"theme"` field in JSON
3. Auto-derived from repo cache

**Generally**: omit `theme` from the JSON. Let it auto. Only set it if you want a specific identity for one squiz (e.g. `phosphor` for a code/infra-flavored decision).

The 8 themes:

| Theme | Vibe | Mode |
|---|---|---|
| `paper` | Cream + ink + rust accent. Editorial, calm. | light |
| `phosphor` | Green-on-black CRT. | dark |
| `amber` | IBM 3279 amber on near-black. | dark |
| `beige` | PS/2 cream with IBM blue. | light |
| `rose` | Warm pink, plum ink, rose accent. | light |
| `ocean` | Pale blue-grey, deep teal, coral accent. | light |
| `forest` | Oat cream, moss, warm gold. | light |
| `slate` | Cool dark grey, electric blue accent. | dark |

Optional toggles: `data-scanlines="on"` for CRT character (best with `phosphor`/`amber`/`slate`), `data-density="comfortable"` for roomier layout.

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

`source.file` is the absolute path of the rendered HTML; `anchor` is the `#squiz-<id>` you can append to it to navigate to a specific decision. `choice: null` means the user skipped that decision — treat as "you decide" unless `notes` say otherwise.

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

Puts `squiz` on `$GOPATH/bin` (usually on `$PATH`). Verify with `squiz version`.

## Accessibility (built into the renderer)

The rendered HTML ships with: a skip-to-decisions link, `radiogroup` ARIA roles per squiz, arrow-key navigation within each group, Enter/Space to select, visible focus rings on all interactives, modal focus trap + return-focus on close, `aria-live` progress announcements, proper `<label>` associations for notes textareas, `prefers-reduced-motion` support. No additional work for the agent.

## Rules

1. **One squiz per invocation.** If answers reveal new ambiguity, follow up in plain chat — don't render a second squiz.
2. **3-12 questions** is the sweet spot. Fewer → `/quiz`. More → the user bails.
3. **Stable IDs.** Both squiz `id` and option `id` are stable — they come back in the JSON. Pick short kebab-or-camel slugs that will still make sense in a week.
4. **Omit `theme`** unless you have a reason to override. Auto-rotation does the right thing.
5. **Art is a bespoke illustration composed from parts. The library is clipart, not finished pictures.**

   The `wf:` / `arch:` / DSL items are **parts** meant to be remixed inside a custom drawing — a labeled box of your own words, an arrow you draw between two icons, a small composition that shows the *specific* idea this option is about. **The default mode is composition: raw SVG that embeds one or more library references plus your own text and connecting marks.** Treat a single library token alone as a deliberate exception, not the norm.

   The composition mechanism (v0.8.0+): inside raw SVG, write `<use href="wf:phone-card" x="0" y="5" width="30" height="50"/>` to drop in a library shape; the renderer inlines it as a `<symbol>` and you get a bespoke composition with library parts. Use `squiz catalog wf --json` to discover sizing — every entry reports its `naturalBox` so you size `<use>` boxes without guessing.

   **Pick the kind of diagram first, THEN compose.** Six shapes consistently read at a glance:

   | Shape | When it fits | Typical recipe |
   |---|---|---|
   | **labeled-object** | one thing with one part that matters | wf/arch icon + callout pointing at the part |
   | **flow** | a process or path (request → ack, raw → cooked) | 2-4 boxes with arrows between; one highlighted |
   | **contrast / vs** | before/after, this/that, chosen/rejected | two mini-panels with `divider:vs` between them |
   | **part-whole** | scope, subset, "this slice of that" | container with one cell emphasized |
   | **metric-with-context** | a number that means something only vs a reference | sparkline + `baseline:N` reference line + label |
   | **typed-list** | a choice among siblings or named modes | `pills:a*\|b\|c*` or N rows with one accent |

   **Visual budget at 100×60.** Four "ink events" max — one silhouette, one accent, one ≤6-char label, one relationship-line. More than that and the eye gives up. One accent color in one place only; if two things are accented neither is. ~30-40% of the viewBox should be empty. Asymmetric composition (centered = decorative; off-center = informative).

   **Authoring checklist — run before committing each art form:**
   1. **Caption it.** In one sentence, what does the picture I'm about to write actually show?
   2. **Key-noun match.** Does the caption reproduce at least two load-bearing nouns or verbs from the desc? If desc says *"hot path: browser → cache → db, 50ms p99"*, the caption must say browser/cache/db/50ms.
   3. **Sibling diff check.** If this is one of N options in a chooser, would the same single token be defensible on each? If yes, mine isn't specific enough.
   4. **Compose-vs-single test.** Could a label, arrow, or second icon make this read more specifically? If yes, compose; if the primitive truly IS the picture, single is fine.
   5. **"None" check.** If after all the above the best I can do is a generic library icon, use `"art": "none"` instead. Generic decoration is worse than no art.

   **A single library token alone is correct only when the primitive IS the picture.** Three legitimate cases:
   - `text:"systemctl enable\nclipsi.service"@mono?size=10&color=accent` — the literal command IS the thing
   - `pills:M*|T|W*|T|F*|S|S` — three lit days IS the desc "3× / week"
   - `wf:calendar-grid` alone — only when the option is literally about a calendar grid

   If you reach for one library token, finish the sentence "the picture I want to draw IS this exact icon, alone, with no label." If you can't say that, compose.

   **Anti-patterns to avoid:**
   - Two options in a chooser share the same `art` (the icon means nothing if siblings collide — the validator warns `sibling-art-collision`)
   - Generic `arch:user` / `arch:server` / `arch:database` where the desc names something specific (give it a label or compose around it)
   - Default fallback art left in place when 30 seconds of composition would say something concrete (the validator warns `composition-thin` per section)
   - Decoration that "looks plausible" but reproduces zero key nouns from the desc
6. **Spec narrative is optional.** Include it only when you have real prose to quote with `{{markers}}` that map to squizzes.
7. **The `quote` field on a squiz is optional.** Use it when you can point to a specific spec line that motivates the question.
8. **Self-contained.** The doc should make sense to a user opening it cold. `SPEC_LEDE` is the one-liner that does this work.
9. **Clickable links.** When you hand the user the rendered file, format it as a `file://` URL (`file:///C:/Users/.../foo.html` on Windows). Bare paths aren't clickable; URLs are.
10. **Recommend when you have a real preference.** Any option can carry `"recommendation": "<one or two sentences explaining why>"`. The renderer shows a `★ RECOMMENDED` chip + the explanation as an editorial callout. Use it when the spec/constraints/audience genuinely point at one option — DON'T mark every option as recommended, and don't fluff the explanation. If you can't justify the pick in one sentence ("OVR-3's $5-VPS constraint rules out k8s; that leaves systemd vs Docker; systemd is one fewer moving part"), the recommendation isn't earned and should stay off. At most one recommendation per squiz/item.

## Files in this skill

- `SKILL.md` — this file.
- `go-renderer/` — Go module that becomes the `squiz` binary on install.
  - `main.go`, `schema.go`, `render.go`, `theme.go`, `art.go`, `dsl.go`, `wf.go`, `browser.go`, `strbuilder.go`
  - `templates/index.html.tmpl` + `templates/styles.css` — embedded via `//go:embed`
  - `testdata/smoke.json` — reference fixture exercising every art form
