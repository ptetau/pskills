# Change Plan: soft-ui pages that build and load in 80 ms

**Owner:** `you` · **Status:** Draft
**Branch:** `claude/ui-soft-assembly-skill-867e0n` · **Plan location:** `plans/soft-ui-80ms.plan.md`
**Progress:** ░░░░░░░░░░░░ 0/14 steps completed (0%)

## How to use this document (read this first, every session)

You are an agent that executes this plan. Assume that you have no memory of earlier sessions.

1. Read Intent, Ground truth, and Boundaries in full (and Approach).
2. Read the Progress log to find the current state. Do not do a completed step again. Do not reopen a decision that the log records.
3. Resume at the first step that is not marked done. Obey the gate of that step. If the step has a `Parallel group` tag that other not-done steps share, those steps run together (see [[quiz-plan-execute]]).
4. After each step, add an entry to the Progress log. Then, before you continue, examine the step against its done criteria.
5. If an action that you plan conflicts with Intent or Boundaries, stop and ask. Do not resolve the conflict yourself.

## Intent

Today, the browser builds each soft-ui page in JavaScript before it shows the page. On a desktop, the comparison report shows its first paint at about 160 ms. All its charts are drawn at about 145 to 176 ms. On a phone with a 4× slower CPU, the page is drawn at 1.5 to
1.9 s. The build (`softui.py render --fast`) takes about 120 ms. Of that time, Python
start-up and imports take about 70 ms.

After this change, these items are true:

- **Build:** `softui.py render SPEC --fast` writes the page in 80 ms or less (wall time,
  median of 5 runs). The browser check is not part of this time.
- **Load:** the full page, below the fold included, is drawn 80 ms or less after the
  navigation starts. This applies on a desktop (1280 px) and on a phone (390 px, 4× slower
  CPU). There is no network delay: the page and all that it needs are local.
- **How:** Python writes each component as static HTML and SVG. The page uses system fonts
  and loads nothing from the network. JavaScript runs only after the page is drawn: it
  sorts, filters, shows tooltips, and starts the motion. When a filter changes, each part
  that reads the dataset updates, charts included.
- **Diagrams:** a page with a Mermaid diagram (`diagram`, `graph`, `er`, `classes`,
  `sankey`) is exempt. Mermaid still draws it in the browser, and the check reports the
  looser budget that applies.
- **Enforcement:** the test suite fails when an example page or the build is over budget.
  A normal `render` only warns.

**Not doing:**

- Rewriting the recorded eval runs (`soft-ui/eval/runs/`) or their `RESULTS.md` files.
- Changing the wording of the "fixed", "error", and "check" lines.
- Changing the look of the `default` and `quarterly` themes. Only two differences are
  allowed: system fonts in place of web fonts, and SVG charts in place of canvas charts.
- A layout engine for diagrams. Diagram pages keep Mermaid in the browser.
- Making network loads fast. The budget assumes no network delay.

## Approach

**Chosen:** Python draws every component to static HTML and SVG at build time. Python also
writes the markdown and code highlighting. Native HTML gives the folds (`<details>`) and
the tabs (radio inputs with CSS).

The current JavaScript renderer stays, but it runs after the page is drawn. It does not build the page on load. It draws a part again only when a
filter, a sort, or a click changes the data of that part. Chart.js goes away. A small SVG
chart module, ported from the Python chart code, gives the same SVG in the browser.

**Considered:**

- *Keep the browser renderer and make it faster* (a small SVG chart module, lazy parts
  below the fold, minified code). Rejected: the budget is the full page in 80 ms at 4× CPU. Script that builds about 500 DOM nodes cannot meet that budget.
- *Pre-render in headless Chromium at build time.* Rejected: the build budget is 80 ms,
  and a browser start-up alone takes longer.
- *Charts that do not update on a filter* (static SVG only). Rejected by the user: a filter
  must update everything, charts included.

## Ground truth

- **Key files:**
  - `soft-ui/scripts/softui.py` (CLI, YAML, normalise, data, `emit`, `browser_check`)
  - `soft-ui/scripts/registry.py`
  - `soft-ui/scripts/transforms.py`
  - `soft-ui/scripts/verify.js` (the browser check)
  - `soft-ui/assets/runtime.js` (the browser renderer, 1,402 lines: `C.*` components, `L.*` layouts, `md()`, `fmt()`, `chartModel()`)
  - `soft-ui/assets/style.css`, `soft-ui/assets/themes/quarterly.css`
  - `soft-ui/scripts/test_softui.py`
  - The test pages: `soft-ui/examples/gallery.yaml`, `soft-ui/examples/sink.yaml`, `soft-ui/eval/report.yaml`, and the bank report spec. The bank report holds private data, so it stays in the scratchpad and does not go in the repository.
- **Build / test / lint:**
  - `python3 soft-ui/scripts/test_softui.py`
  - `python3 soft-ui/scripts/softui.py render <spec>`: runs the browser check. `--fast` skips the check.
  - The full list of tests in `AGENTS.md`.
  - `python3 improve-writing/scripts/check_writing.py <file>` for prose.
  - `python3 scripts/check_skill_form.py soft-ui/SKILL.md`.
- **Conventions:**
  - `WRITING-GUIDELINES.md` (STE) for all prose.
  - The skill body is at most 200 words.
  - Python uses the standard library plus PyYAML. Node uses only Playwright, and only in the check.
- **Measured facts:**
  - Python start-up is 23 ms. `import softui` is 45 ms, and `import yaml` is 26 ms of that.
  - `yaml.__with_libyaml__` is True, so the CSafeLoader is available.
  - Import costs: `argparse` 6 ms, `subprocess` 9 ms, `tempfile` 9 ms, `difflib` 5 ms, `csv` 4 ms, `statistics` 8 ms.
  - Under the profiler, the comparison report takes 117 ms of script, 30 ms of layout, and 16 ms of style.
  - Chart.js takes 11 ms to evaluate.
- **Prior art:**
  - `quiz-visual/scripts/render_quiz.py` already writes static HTML in Python.
  - The soft-ui eval loops (pilot, then full run, then fixes) showed two things. Agents rely on the exact wording of the "fixed" and "error" lines. Silent wrong values are the costliest failure, for example `pct` on fractions and empty stat tiles.

**Verification rule:** before you call a function, an API, or a library feature that is not listed above, find its actual definition. Read the definition in the source or in the installed package. Do not write a call from your memory of what the API "probably" looks like. If you cannot find the definition, stop and ask.

## Boundaries

- **May modify:**
  - `soft-ui/scripts/**`, `soft-ui/assets/**`, `soft-ui/examples/**`
  - `soft-ui/SKILL.md`, `soft-ui/README.md`
  - `soft-ui/eval/report.yaml`, a new `soft-ui/perf/` folder, and `plans/README.md`
  - The specs can change freely, because the user allowed changes that break the spec format.
- **Must not touch:**
  - `soft-ui/eval/runs/**`
  - The wording of the "fixed", "error", and "check" lines. New lines are permitted.
  - Theme colours, tones, layout, and the responsive rules, except for fonts and the chart drawing.
  - Other skills and plugins.
- **Stop and ask when:** a test you didn't expect fails, a change is necessary outside "may modify", or the instructions of a step are ambiguous. Also stop and ask when you tried the same fix two times without success. Two failed attempts mean that the plan is wrong, not that more effort is necessary.
- **Assumptions (re-check every step):**
  1. With lazy imports and the CSafeLoader, a Python build of a test page fits in 80 ms. Step 1 tests this.
  2. A static HTML and SVG copy of the comparison report finishes its layout and paint in 80 ms at 4× CPU. The copy has system fonts and no script. Step 3 tests this.
  3. SVG that takes its colours from CSS variables (`fill="var(--s1)"`) follows the theme and the dark mode in Chromium and Safari.
  4. The "drawn" time is measured two animation frames after DOMContentLoaded. It matches what a person sees: no part changes size or position after that time (the layout-shift score is 0). Motion, for example a count-up, can change text after that time, but it must not change sizes.
  7. The browser does not compile a script that is stored as `<script type="text/plain">`. Thus, a large runtime that is stored this way, and compiled after `load`, adds no time before the page is drawn.
  5. Headless Chromium with 4× CPU throttling stands in for a phone.
  6. The claude.ai Artifact viewer draws an inline page the same way that headless Chromium does.

**Riskiest assumption:** Assumption 1 (the Python build fits in 80 ms). Step 1 tests this assumption, so step 1 comes first.

## Steps

Each step has a size that fits in one session. All steps are **AUTO**, because the user did
not ask for a checkpoint. Each step declares the files that it **Touches**, and what it
**Depends on**.

### Step 1: Prove that the Python build fits in 80 ms · `[ ]` AUTO · Parallel group: none

- **Do:**
  - Make the imports in `softui.py` and `transforms.py` lazy. Import `subprocess`, `tempfile`, `difflib`, `csv`, `statistics`, and `ast` only in the functions that use them.
  - Use `yaml.CSafeLoader` (with the same rules for booleans and dates) when it exists, and the pure loader otherwise.
  - Add `soft-ui/perf/time_build.py`. It runs `render --fast` 5 times on each test page (gallery, sink, report, and a copy of the bank spec with synthetic data), and prints the median wall time.
  - Add a stub step to `emit` that writes about 500 static elements. The stub stands in for the static drawing, which is not built yet.
- **Done when:**
  - `python3 soft-ui/perf/time_build.py` prints a median of 60 ms or less for each test page, with the stub step included. That leaves 20 ms for the static drawing.
  - `test_softui.py` passes.
  - If the median is more than 80 ms after these changes, mark the step blocked and stop. This is a kill criterion.
- **Out of scope here:** the static drawing itself. Do not change any output.
- **Touches:** `soft-ui/scripts/softui.py`, `soft-ui/scripts/transforms.py`, `soft-ui/perf/time_build.py`, `soft-ui/perf/bank-synthetic.yaml`
- **Depends on:** none

### Step 2: Timing harness and "before" screenshots · `[ ]` AUTO · Parallel group: none

- **Do:**
  - Add `soft-ui/perf/time_load.js`. It loads a page in Chromium at 1280 px, and at 390 px with 4× CPU throttling, and blocks the network. It records the "drawn" time: two `requestAnimationFrame` callbacks after DOMContentLoaded. It also records first paint, and the median of 5 runs.
  - With the current engine, render the four test pages and save their screenshots to `soft-ui/perf/before/<page>-<width>-<light|dark>.png`. Use widths 390 and 1280, and light and dark. Also save the timings to `soft-ui/perf/before/timings.json`.
- **Done when:**
  - The 16 PNG files and `timings.json` exist.
  - `node soft-ui/perf/time_load.js <page>` prints the drawn time on desktop and on the phone for each page.
- **Out of scope here:** any change to the engine.
- **Touches:** `soft-ui/perf/time_load.js`, `soft-ui/perf/before/**`
- **Depends on:** Step 1. It uses the synthetic bank spec.

### Step 3: Prove that a static page draws in 80 ms on a phone · `[ ]` AUTO · Parallel group: none

- **Do:**
  - Make `soft-ui/perf/static-probe.html` from the rendered comparison report. Save the DOM from Chromium. Swap each canvas for an SVG with the same number of marks. Remove all scripts. Use system fonts.
  - Time the file with `time_load.js`.
  - If the phone time is over 80 ms, try `content-visibility: auto` with `contain-intrinsic-size` on the parts below the fold. Also try less CSS: only the rules of the components that the page uses. Record which ones help.
- **Done when:** the file is drawn in 80 ms or less at 4× CPU. Record which CSS changes were necessary, because Step 4 and Step 10 use them. If no change makes 80 ms, mark the step blocked and stop. This is a kill criterion.
- **Out of scope here:** the static drawing in Python.
- **Touches:** `soft-ui/perf/static-probe.html`, `soft-ui/perf/probe-notes.md`
- **Depends on:** Step 2.

### Step 4: System fonts, and the CSS changes from Step 3 · `[ ]` AUTO · Parallel group: P1

- **Do:**
  - Remove the Google Fonts `<link>` tags from `emit`.
  - Set the font tokens to system stacks. Default theme: `system-ui`, `ui-monospace`. Quarterly: Georgia, "Times New Roman", serif for the serif face. "Helvetica Neue", Arial for the sans face. "Arial Narrow" and "Helvetica Neue" condensed for the condensed face.
  - Add the CSS changes that Step 3 found necessary.
- **Done when:**
  - No rendered page holds `fonts.googleapis`.
  - The quarterly and default examples pass the browser check.
- **Out of scope here:** colours and layout.
- **Touches:** `soft-ui/assets/style.css`, `soft-ui/assets/themes/quarterly.css`, `soft-ui/scripts/softui.py` (only the `THEMES` and `FONTS` constants and the link in `emit`)
- **Depends on:** Step 3.

### Step 5: Python text: markdown, formats, tones, code highlighting · `[ ]` AUTO · Parallel group: P1

- **Do:** add `soft-ui/scripts/ssr_text.py` with Python versions of these runtime functions:
  - `inline()`, `md()`, `fmt()` (all formats, including `money`, `ratio`, and `k`)
  - `normTone`, `mapTone`, `cellTone`, the `AUTO` tones, and the severity order
  - `shortDate`
  - A small regex code highlighter. The highlighter marks keywords, strings, numbers, and comments for Python, JS/TS, Go, YAML, JSON, SQL, bash, and diff. It uses the `hljs-*` class names that the CSS already styles.

  Add `soft-ui/scripts/test_ssr_text.py`.
- **Done when:**
  - `test_ssr_text.py` passes, with cases taken from the JavaScript output for the same inputs. For example, `fmt(-1234.5, "money")` gives `−$1,235` with NZD.
  - The highlighter handles 1,000 lines of code in 5 ms or less.
- **Out of scope here:** the components.
- **Touches:** `soft-ui/scripts/ssr_text.py`, `soft-ui/scripts/test_ssr_text.py`
- **Depends on:** Step 1. It needs the import style.

### Step 6: Python SVG charts · `[ ]` AUTO · Parallel group: P1

- **Do:**
  - Add `soft-ui/scripts/svgchart.py`. It builds a chart model from the dataset rows: the port of `chartModel`, `histModel`, and `linreg`.
  - `svgchart.py` draws SVG for each kind: `bar` (vertical, horizontal, stacked), `line`, `area`, `scatter` with trend, `donut`, `waterfall` with subtotals, and `hist`. Each chart has these parts:
    - Axes and gridlines.
    - The y axis on the left or the right (from a theme flag), and square or rounded bars.
    - Marks and bands, a legend, and `<title>` tooltips.
    - Fills that use CSS variables (`var(--s1)` ... `var(--good)`), so the themes and the dark mode work.
    - A `width` argument. An SVG scales its text with its width, so the static page gets a wide drawing (640 units) and a narrow drawing (340 units) of each chart. CSS then shows one of the two (see Step 10).
  - Add `soft-ui/scripts/test_svgchart.py`.
- **Done when:**
  - The tests pass for each kind. The bar and point counts are right, and the axis ticks are right. A severity series uses the status colours.
  - Each chart draws in 2 ms or less in Python.
- **Out of scope here:** the browser port and the motion.
- **Touches:** `soft-ui/scripts/svgchart.py`, `soft-ui/scripts/test_svgchart.py`
- **Depends on:** Step 1.

### Step 7: Browser port of the SVG charts, with a parity test · `[ ]` AUTO · Parallel group: P2

- **Do:**
  - Add `soft-ui/assets/svgchart.js`: a line-by-line port of `svgchart.py` that gives the same SVG text for the same model.
  - Add `soft-ui/perf/test_chart_parity.js`. It runs `svgchart.js` in Node on 12 fixture models, and compares the output with the output of `svgchart.py` for the same models. The comparison ignores whitespace and rounds numbers to 2 decimals.
- **Done when:** `node soft-ui/perf/test_chart_parity.js` prints `parity ok 12/12`.
- **Out of scope here:** wiring the port into the runtime.
- **Touches:** `soft-ui/assets/svgchart.js`, `soft-ui/perf/test_chart_parity.js`, `soft-ui/perf/chart-fixtures.json`
- **Depends on:** Step 6.

### Step 8: Static layouts and summary parts · `[ ]` AUTO · Parallel group: P2

- **Do:** add `soft-ui/scripts/ssr_layout.py`. It draws these parts as HTML:
  - The page header.
  - `row`, `col`, `grid`, `section`, `sidebar`, and `compare` (side by side).
  - `card` and `float`, which fold with `<details>`.
  - `tabs` and `compare: toggle`, which use radio inputs and CSS.
  - `stat`, `stats`, `kv`, `meter`, `callout`, `text`, and `checklist`.

  `ssr_layout.py` also writes the window wrapper (`.su-win`) and the notes. It uses the same class names as the runtime, so `style.css` applies unchanged. Put the CSS for the radio tabs in a new file, `soft-ui/assets/ssr-layout.css`. Add `soft-ui/scripts/test_ssr_layout.py`.
- **Done when:**
  - The tests pass.
  - A Playwright test with JavaScript turned off loads the sink example, drawn only with these parts (with stand-ins for the others). A click on the second tab shows its panel, and hides the first panel.
- **Out of scope here:** the data components.
- **Touches:** `soft-ui/scripts/ssr_layout.py`, `soft-ui/scripts/test_ssr_layout.py`, `soft-ui/assets/ssr-layout.css`, `soft-ui/perf/test_tabs_noscript.js`
- **Depends on:** Step 5.

### Step 9: Static data parts in HTML · `[ ]` AUTO · Parallel group: P2

- **Do:** add `soft-ui/scripts/ssr_html.py`. It draws these parts:
  - `table`, with groups, tones, bars, `top`, and rows that expand with `<details>`. Each row carries a `data-row` index.
  - `list`, `board`, `timeline`, `tree`, `filter` (chips with counts), `statement`, `decision`, and `truth`.
  - `code` with notes, and `diff` (split and unified) with notes.

  Two layouts need a decision that the runtime made in the browser. Make them with CSS only:
  - **Table stacking:** Python estimates the width that each table needs, from its column count and its longest values. Python then gives the table a class for one width band (`su-stack-480`, `-640`, `-800`, `-960`). A container query for each band stacks the table into cards when its box is narrower.
  - **Diffs:** Python writes both the split and the unified layout of a diff. A container query shows the unified layout in a box narrower than 720 px.

  Put this CSS in a new file, `soft-ui/assets/ssr-html.css`. Add `soft-ui/scripts/test_ssr_html.py`.
- **Done when:**
  - The tests pass. For each part, the text content matches what the runtime draws for the same spec. The test gets the runtime text with one Chromium run on a fixture spec, and saves it to a fixture file in this step.
  - At 390 px, the bank month-by-month table shows as cards with no script, and at 1280 px it shows as a table.
- **Out of scope here:** the SVG data parts.
- **Touches:** `soft-ui/scripts/ssr_html.py`, `soft-ui/scripts/test_ssr_html.py`, `soft-ui/assets/ssr-html.css`, `soft-ui/perf/runtime-text-fixture.json`
- **Depends on:** Step 5.

### Step 10: Static data parts in SVG · `[ ]` AUTO · Parallel group: P2

- **Do:** add `soft-ui/scripts/ssr_svg.py`. It draws these parts as SVG or positioned HTML:
  - `chart` (through `svgchart.py`), `heatmap` (with `worst` and totals), `gantt`, `box`, `forest`, and `treemap`.
  - Each chart is drawn twice, wide and narrow. A container query in a new file, `soft-ui/assets/ssr-svg.css`, shows the narrow drawing in a box narrower than 520 px. Thus, the labels keep their size on a phone.
  - The treemap places its cells with percentages in a box of fixed height, so the cells scale without script and the text keeps its size.

  Add `soft-ui/scripts/test_ssr_svg.py`.
- **Done when:**
  - The tests pass.
  - The treemap cells tile 100% of the box, with a total overlap and gap area under 0.5%.
  - On the gallery data, the `<title>` of each box gives the same n, median, and quartiles as the runtime tooltip. Each forest row gives the same estimate and interval text as the runtime.
  - At 390 px, the chart axis labels in the screenshot are 10 px or larger.
- **Out of scope here:** the motion.
- **Touches:** `soft-ui/scripts/ssr_svg.py`, `soft-ui/scripts/test_ssr_svg.py`, `soft-ui/assets/ssr-svg.css`
- **Depends on:** Step 5, Step 6.

### Step 11: Wire the static page and the after-draw runtime · `[ ]` AUTO · Parallel group: none

- **Do:**
  - `emit` writes the static HTML from Steps 8 to 10, then the CSS (`style.css`, the three `ssr-*.css` files, and the theme file), then the data plan.
  - `emit` stores the runtime and `svgchart.js` in `<script type="text/plain" id="su-runtime">`. A tiny loader starts them with `new Function` in a `setTimeout` after the `load` event. The browser thus does not compile them before the page is drawn.
  - Change `runtime.js` so that on load it only attaches behaviour to the static DOM. It must not draw the page again. The behaviour is sort, filters and chips, click-to-filter, tooltips, row expand, and the motion (IntersectionObserver plus the CSS classes).
  - On a filter change, the runtime draws again only the parts that read that dataset. It uses the existing `C.*` renderers, with `svgchart.js` in place of Chart.js.
  - Remove Chart.js and highlight.js from `LIBS`.
  - Pages with diagrams still load Mermaid.
  - Add the bounce motion to the SVG charts as CSS transforms on the bars (`transform-box: fill-box`).
- **Done when:**
  - The four test pages render, and pass the browser check.
  - On the comparison report, the runtime changes no element size or structure between DOMContentLoaded and the first user input. A MutationObserver test counts zero `childList` changes. Text changes from the count-up are allowed.
  - The drawn time with the stored runtime is 5 ms or less from the drawn time with the runtime removed.
  - A Playwright test proves that each interactive feature still works:
    - A click on a filter chip hides rows, and the chart is drawn again for the filtered rows.
    - A sort click orders the rows.
    - A tab switches with script turned off.
- **Out of scope here:** the budget gate and the docs.
- **Touches:** `soft-ui/scripts/softui.py`, `soft-ui/assets/runtime.js`, `soft-ui/assets/themes/quarterly.css` (the motion rules only), `soft-ui/perf/test_interaction.js`
- **Depends on:** Step 4, Step 7, Step 8, Step 9, Step 10.

### Step 12: Budget gate in the check and the tests · `[ ]` AUTO · Parallel group: none

- **Do:**
  - `verify.js` measures the drawn time, median of 3, on desktop and at 4× CPU.
  - Over 80 ms, `render` prints a new line: `check warning page drawn in N ms (budget 80 ms) on phone: slowest part X`. "Slowest part" is the largest node by layout cost.
  - For a page with a diagram, the line says "diagram page" and names the looser budget. That budget is 300 ms on desktop and 1,000 ms on the phone.
  - Add `soft-ui/perf/test_budget.py`. It runs `time_build.py` and `time_load.js` on the example pages. It fails when a build takes more than 80 ms. It also fails when a non-diagram page takes more than 80 ms to draw. Add it to the test list in `AGENTS.md`, beside `test_softui.py`.
  - Add a check that nothing changes size after the drawn time: the layout-shift score is 0.
- **Done when:**
  - `python3 soft-ui/perf/test_budget.py` passes on gallery, sink, and report.
  - A deliberately slow fixture (2,000 table rows) makes `render` print the warning, and makes `test_budget.py` fail.
- **Out of scope here:** making user pages with large data fast.
- **Touches:** `soft-ui/scripts/verify.js`, `soft-ui/scripts/softui.py` (`browser_check` only), `soft-ui/perf/test_budget.py`, `soft-ui/perf/slow-fixture.yaml`, `AGENTS.md` (one test line)
- **Depends on:** Step 2, Step 11.

### Step 13: Docs and specs · `[ ]` AUTO · Parallel group: none

- **Do:**
  - Update these files for the new engine: `soft-ui/SKILL.md` (200 words or less; `--inline` is now needed only for diagram pages), `soft-ui/README.md` (how a page is built, the budgets, system fonts, `soft-ui/perf/`), the `catalog` and `explain` text, and `plans/README.md` (this plan).
  - Update any example spec that the engine changes break.
- **Done when:**
  - `check_writing.py` gives "OBEYS THE GUIDELINES" for `SKILL.md`, `README.md`, and this plan.
  - `check_skill_form.py soft-ui/SKILL.md` passes.
  - Each example renders with "check ok".
- **Out of scope here:** `soft-ui/eval/runs/`.
- **Touches:** `soft-ui/SKILL.md`, `soft-ui/README.md`, `soft-ui/scripts/softui.py` (the `catalog` and help text only), `soft-ui/examples/*.yaml`, `soft-ui/eval/report.yaml`, `plans/README.md`
- **Depends on:** Step 12.

### Step 14: "After" screenshots, review page, and the full test suite · `[ ]` AUTO · Parallel group: none

- **Do:**
  - Render the four test pages with the new engine, and save the screenshots to `soft-ui/perf/after/`, with the same names as in Step 2.
  - Make `soft-ui/perf/compare.html`. It shows each before and after pair side by side, with the timings from both runs. The bank pair is the only one with private data, so it stays in the scratchpad and is shown to the user with `SendUserFile`.
  - Run each test in `AGENTS.md`.
- **Done when:**
  - All tests pass. `pdlc_known_files.py --check` is allowed to fail with its known "repository is shallow" message only.
  - `compare.html` shows 12 pairs from the repository pages, and the user has the bank pairs.
  - The timings table shows each non-diagram page at 80 ms or less for build and for load, on desktop and phone.
- **Out of scope here:** visual tuning. The user reviews the screenshots and asks for changes.
- **Touches:** `soft-ui/perf/after/**`, `soft-ui/perf/compare.html`
- **Depends on:** Step 13.

**Parallel groups:** (each step in P2 has its own module, test file, and CSS file)

- **P1** is Steps 4, 5, and 6. Step 4 touches only CSS and the font constants and link in `softui.py`. Steps 5 and 6 add new modules.
- **P2** is Steps 7, 8, 9, and 10. Each step adds its own module, test file, and CSS file, so no file is shared. Every step in P2 (the four new modules) depends only on steps in P1 (fonts, text, and charts). P1 (fonts, text, and charts) is complete before P2 (the four new modules) starts.
- Steps 1, 2, 3, 11, 12, 13, and 14 run alone. Step 1 tests the riskiest assumption. The other steps are joins, or they depend on the step before them.

## Verification and rollback

- **Human verifies by:**
  - Looking at the before and after screenshots of the four test pages, at phone and desktop width, in light and dark (`soft-ui/perf/compare.html`, plus the bank pairs in the side panel).
  - Reading the timing table in the same page.
- **Failing looks like:**
  - A build or a load over 80 ms on a non-diagram example.
  - A part that the runtime draws again on load (the MutationObserver check fails).
  - A chart whose browser SVG differs from its Python SVG (the parity test fails).
  - A number that differs between the before and after screenshots.
  - A theme that changes apart from the fonts.
- **Rollback:** `git revert` of the commits of this plan, one for each step. The "before" screenshots and timings in `soft-ui/perf/before/` stay as the baseline.
- **Kill criteria:**
  - Step 1 cannot bring a build under 80 ms.
  - Step 3 cannot draw the static comparison report in 80 ms at 4× CPU, even with `content-visibility` and less CSS.
  - The parity test in Step 7 cannot be made to pass without a third chart implementation.

## Progress log

The log has one entry for each step. Add each entry at execution time, not before. The newest entry is last. This log is the only memory that survives between sessions, so record the decisions, not only the actions.
