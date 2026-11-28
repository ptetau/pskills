# Change Plan: soft-ui in Go, with pages that build and load in 80 ms

**Owner:** `you` · **Status:** Draft
**Branch:** `claude/ui-soft-assembly-skill-867e0n` · **Plan location:** `plans/soft-ui-80ms.plan.md`
**Progress:** ░░░░░░░░░░░░ 0/16 steps completed (0%)

## How to use this document (read this first, every session)

You are an agent that executes this plan. Assume that you have no memory of earlier sessions.

1. Read Intent, Ground truth, and Boundaries in full (and Approach).
2. Read the Progress log to find the current state. Do not do a completed step again. Do not reopen a decision that the log records.
3. Resume at the first step that is not marked done. Obey the gate of that step. If the step has a `Parallel group` tag that other not-done steps share, those steps run together (see [[quiz-plan-execute]]).
4. After each step, add an entry to the Progress log. Then, before you continue, examine the step against its done criteria.
5. If an action that you plan conflicts with Intent or Boundaries, stop and ask. Do not resolve the conflict yourself.

## Intent

Today, the browser builds each soft-ui page in JavaScript before it shows the page. On a desktop, the comparison report shows its first paint at about 160 ms. All its charts are drawn at about 145 to 176 ms. On a phone with a 4× slower CPU, the page is drawn at 1.5 to 1.9 s. The Python build (`softui.py render --fast`) takes about 120 ms. Python start-up and imports take about 70 ms of that time.

After this change, these items are true:

- **Language:** a Go program replaces the Python program. Go draws every component to static HTML and SVG. A small JavaScript file runs after the page is drawn.
- **Build:** `softui render SPEC --fast` writes the page in 80 ms or less (wall time, median of 5 runs, launcher included). The browser check is not part of this time.
- **Load:** the full page, below the fold included, is drawn 80 ms or less after the navigation starts. This holds on a desktop (1280 px) and on a phone (390 px, 4× slower CPU). There is no network delay: the page and all that it needs are local.
- **Page:** the page uses system fonts and loads nothing from the network. Tabs and folds need no script.
- **After the draw:** the script sorts, filters, searches, shows tooltips, and starts the motion. When a filter changes, tables, lists, counts, and tiles update. Charts stay as drawn and highlight the selected values.
- **Diagrams:** a page with a diagram (`diagram`, `graph`, `er`, `classes`, `sankey`) is exempt. Go writes the Mermaid source, and Mermaid draws it in the browser. The check reports the looser budget that applies.
- **Install:** the skill folder holds prebuilt binaries and a launcher. A plain copy of the folder works with nothing installed.
- **Enforcement:** the test suite fails when an example page or the build is over budget. A normal `render` only warns.

**Not doing:**

- Rewriting the recorded eval runs (`soft-ui/eval/runs/`) or their `RESULTS.md` files.
- Changing the wording of the "fixed", "error", and "check" lines. One exception is allowed: a YAML syntax error can lose its column number if the Go parser does not give one.
- Changing the look of the `default` and `quarterly` themes. Only two differences are allowed: system fonts in place of web fonts, and SVG charts in place of canvas charts.
- A layout engine for diagrams. Diagram pages keep Mermaid in the browser.
- Charts that redraw when a filter changes. Charts highlight the selection instead.
- Making network loads fast. The budget assumes no network delay.
- A Python fallback. The Python program is deleted at the cutover. Rollback is a `git revert`.

## Approach

**Chosen:** a Go program with one dependency, `gopkg.in/yaml.v3`, vendored in the repository. The program parses the YAML spec, repairs mistakes, shapes the data, and writes the page. It writes each component as static HTML or SVG. It also writes the markdown and the code highlighting. It writes diagrams as Mermaid source.

Native HTML gives the folds (`<details>`) and the tabs (radio inputs with CSS). The page script is stored as text, and it starts after the `load` event. The script attaches behaviour to the static page. It does not draw the page.

The skill folder holds prebuilt binaries for six targets (Linux, Mac, and Windows, each for x86 and ARM) in `soft-ui/bin/`. A shell launcher picks the binary for the machine. If no binary matches, the launcher runs `go build` from the vendored source.

**Considered:**

- *TypeScript on Bun (Node as the fallback).* One renderer could run at build time and in the page, so charts could redraw on a filter. Rejected by the user in favour of Go. The cost is that charts highlight and do not redraw.
- *Python with static drawing.* Rejected: the build needs lazy imports to fit 80 ms, and the filter redraw needs a second renderer in JavaScript. The two renderers drift apart.
- *Go compiled to WebAssembly, so that charts redraw.* Rejected: the module is 4 MB (1.1 MB gzipped), which is too much for every page.
- *Keep the browser renderer and make it faster.* Rejected: script that builds about 500 DOM nodes cannot meet 80 ms at 4× CPU.
- *Pre-render in headless Chromium at build time.* Rejected: Chromium start-up alone is longer than the budget.

## Ground truth

- **Key files (Python, to port, then delete):**
  - `soft-ui/scripts/softui.py` (2,023 lines): CLI, YAML, normalise, repairs, data, `emit`, `browser_check`
  - `soft-ui/scripts/registry.py` (518 lines): components, props, aliases, examples
  - `soft-ui/scripts/transforms.py` (237 lines): dataset steps
  - `soft-ui/scripts/test_softui.py`: the Python tests
- **Key files (kept):**
  - `soft-ui/scripts/verify.js`: the browser check (Node and Playwright). The Go program starts it.
  - `soft-ui/assets/style.css`, `soft-ui/assets/themes/quarterly.css`
  - `soft-ui/assets/runtime.js` (1,402 lines). It is the reference for the component output, and it shrinks to the page script.
- **The corpus of specs for the port (30 specs):**
  - 24 recorded specs: `soft-ui/eval/runs/*/*/tool.yaml`.
  - `soft-ui/examples/gallery.yaml`, `soft-ui/examples/sink.yaml`, and `soft-ui/eval/report.yaml`.
  - A copy of the bank spec with synthetic data, and two deliberately broken specs. Step 2 makes these three. The real bank report holds private data, so it stays in the scratchpad.
- **Build / test / lint:**
  - Today: `python3 soft-ui/scripts/test_softui.py`, and `python3 soft-ui/scripts/softui.py render <spec>` (the browser check runs unless `--fast`).
  - After Step 3: `(cd soft-ui/go && go test ./...)`, and `soft-ui/softui render <spec>`.
  - The full list of tests in `AGENTS.md`.
  - `python3 improve-writing/scripts/check_writing.py <file>` for prose, and `python3 scripts/check_skill_form.py soft-ui/SKILL.md`.
- **Conventions:**
  - `WRITING-GUIDELINES.md` (STE) for all prose.
  - The skill body is at most 200 words.
  - Go uses only the standard library plus `gopkg.in/yaml.v3`, vendored. Node uses only Playwright, and only in the check.
  - Each pull request description follows the attribution lines in the session reminder.
- **Measured facts:**
  - A Go stand-in (parse the YAML spec, read a CSV, write 500 elements) runs in 2.8 ms as one process, from start to end. The binary is 3.5 MB on Linux, and 2.4 MB stripped for the Mac. A cold compile takes 4.7 s.
  - Start-up: Bun 5.5 ms, Node 26 ms, Python 12 ms (34 ms with YAML loaded).
  - Go WebAssembly: 4.0 MB (1.1 MB gzipped).
  - Under the profiler, the comparison report takes 117 ms of script, 30 ms of layout, and 16 ms of style on a desktop.
  - `yaml.v3@v3.0.1` is in the module cache here, and `go` is 1.24.7.
- **Prior art:**
  - `quiz-visual/scripts/render_quiz.py` already writes static HTML.
  - The soft-ui eval loops showed two things. Agents rely on the exact wording of the "fixed" and "error" lines. Silent wrong values are the costliest failure, for example `pct` on fractions and empty stat tiles. Thus, this plan treats the Python output as a contract, and tests the port against it.

**Verification rule:** before you call a function, an API, or a library feature that is not listed above, find its actual definition. Read the definition in the source or in the installed package. Do not write a call from your memory of what the API "probably" looks like. If you cannot find the definition, stop and ask.

## Boundaries

- **May modify:**
  - New folders: `soft-ui/go/`, `soft-ui/bin/`, `soft-ui/perf/`.
  - `soft-ui/assets/**`, `soft-ui/scripts/**`, `soft-ui/examples/**`, `soft-ui/SKILL.md`, `soft-ui/README.md`.
  - New launchers: `soft-ui/softui` and `soft-ui/softui.cmd`.
  - `soft-ui/eval/report.yaml`, `AGENTS.md` (the test list only), and `plans/README.md`.
  - The specs can change freely, because the user allowed changes that break the spec format.
- **Must not touch:**
  - `soft-ui/eval/runs/**`.
  - The wording of the "fixed", "error", and "check" lines. New lines are permitted. The golden test enforces this.
  - Theme colours, tones, layout, and the responsive rules, except for fonts and the chart drawing.
  - Other skills and plugins.
- **Stop and ask when:**
  - A test you did not expect fails, a change is necessary outside "may modify", or the instructions of a step are ambiguous.
  - The Go output differs from a golden file, and the Python behaviour looks like a bug. Do not fix the behaviour in the port. Write the difference in the Progress log, and ask.
  - You tried the same fix two times without success. Two failed attempts mean that the plan is wrong, not that more effort is necessary.
- **Assumptions (re-check every step):**
  1. A static HTML and SVG copy of the comparison report finishes its layout and paint in 80 ms at 4× CPU. The copy has system fonts and no script. Step 1 tests this. The profiler shows 46 ms of layout and style on a desktop, which is about 184 ms at 4× CPU, so this assumption can fail.
  2. `yaml.v3` can keep the rules of the Python loader: only `true` and `false` are booleans, dates stay strings, and map key order is kept. Step 3 tests this.
  3. Go matches Python for number rounding and formatting. Python `round()` rounds half to even, and JavaScript rounds half up. The tests compare Go with the Python output.
  4. Mermaid source from Go equals the source from Python, character for character, for `graph`, `er`, `classes`, and `sankey`.
  5. SVG that takes its colours from CSS variables (`fill="var(--s1)"`) follows the theme and the dark mode in Chromium and Safari.
  6. The "drawn" time is measured two animation frames after DOMContentLoaded, and the layout-shift score is 0. Motion, for example a count-up, can change text after that time, but it must not change sizes.
  7. The browser does not compile a script that is stored as `<script type="text/plain">`. A script that starts after `load` adds no time before the page is drawn.
  8. Headless Chromium with 4× CPU throttling stands in for a phone.
  9. The launcher adds 5 ms or less to the wall time of a build.
  10. The static page stays small: the comparison report is 400 KB or less without libraries.

**Riskiest assumption:** Assumption 1 (a static page draws in 80 ms at 4× CPU). The Go build time is no longer at risk, because the stand-in took 2.8 ms. This assumption is the one that can end the plan. Step 1 tests this assumption, so Step 1 comes first.

## Steps

Each step has a size that fits in one session. All steps are **AUTO**, because the user did not ask for a checkpoint. Each step declares the files that it **Touches**, and what it **Depends on**.

### Step 1: Prove that a static page draws in 80 ms at 4× CPU · `[ ]` AUTO · Parallel group: none

- **Do:**
  - Add `soft-ui/perf/time_load.js`. It loads a page in Chromium at 1280 px, and at 390 px with 4× CPU throttling. It blocks the network. It records the "drawn" time: two `requestAnimationFrame` callbacks after DOMContentLoaded. It also records first paint and the layout-shift score, and takes the median of 5 runs.
  - Make `soft-ui/perf/static-probe.html` from the rendered comparison report. Save the DOM from Chromium. Swap each canvas for an SVG with the same number of marks. Remove all scripts. Use system fonts.
  - Time the probe. If the phone time is over 80 ms, try each change below. Record which changes help.
  - `content-visibility: auto` with `contain-intrinsic-size` on the parts below the fold.
  - `contain: layout paint` on each window.
  - Only the CSS rules that the page uses.
- **Done when:**
  - The probe is drawn in 80 ms or less at 4× CPU, and on the desktop.
  - `soft-ui/perf/probe-notes.md` lists each CSS change that was necessary, because Steps 12 and 15 use them.
  - If no change reaches 80 ms, mark the step blocked and stop. Ask the user whether the budget changes to the first screen only. This is a kill criterion.
- **Out of scope here:** any Go code, and any change to the engine.
- **Touches:** `soft-ui/perf/time_load.js`, `soft-ui/perf/static-probe.html`, `soft-ui/perf/probe-notes.md`
- **Depends on:** none

### Step 2: Freeze the baseline: goldens, screenshots, and timings · `[ ]` AUTO · Parallel group: none

- **Do:**
  - Add `--dump-plan FILE` to `softui.py`. It writes the compiled plan as JSON with sorted keys.
  - Add `soft-ui/perf/bank-synthetic.yaml` (the bank spec with synthetic data) and `soft-ui/perf/broken-yaml.yaml` and `soft-ui/perf/broken-columns.yaml` (two specs with errors).
  - Add `soft-ui/perf/golden.py`. For each of the 30 specs, it saves the "fixed" and "error" lines to `soft-ui/perf/golden/<name>.out`, and the plan to `soft-ui/perf/golden/<name>.plan.json`.
  - With the current engine, render the four test pages (gallery, sink, report, and the synthetic bank). Save their screenshots to `soft-ui/perf/before/<page>-<width>-<light|dark>.png` at widths 390 and 1280. Save the timings to `soft-ui/perf/before/timings.json`.
- **Done when:**
  - The 30 golden pairs exist.
  - The 16 PNG files and `timings.json` exist.
  - Running `golden.py` again gives no diff, so the goldens are repeatable.
- **Out of scope here:** any change to the output of `render`.
- **Touches:** `soft-ui/scripts/softui.py` (only `--dump-plan`), `soft-ui/perf/golden.py`, `soft-ui/perf/golden/**`, `soft-ui/perf/bank-synthetic.yaml`, `soft-ui/perf/broken-yaml.yaml`, `soft-ui/perf/broken-columns.yaml`, `soft-ui/perf/before/**`
- **Depends on:** Step 1. It uses `time_load.js`.

### Step 3: Go module, YAML loader, launcher, and binaries script · `[ ]` AUTO · Parallel group: none

- **Do:**
  - Make `soft-ui/go/` (module `softui`, Go 1.24). Vendor `gopkg.in/yaml.v3` with `go mod vendor`.
  - Add `main.go` with the commands `catalog`, `explain`, and `render`, as stubs. Embed the `assets` folder with `go:embed`.
  - Add the YAML loader. It walks `yaml.Node` and applies the rules of `load_yaml` in `softui.py`. Only literal `true` and `false` are booleans. Timestamps stay strings, and map key order is kept. A syntax error gives the same message form: `YAML syntax error at line N, column M: ...` plus the hint.
  - Add `soft-ui/scripts/build-binaries.sh`. It cross-compiles six targets (`linux`, `darwin`, and `windows`, each for `amd64` and `arm64`) with `-trimpath` and `-ldflags='-s -w'` into `soft-ui/bin/`.
  - Add the launcher `soft-ui/softui` (POSIX shell). It picks `bin/softui-<os>-<arch>`. If no binary matches, it runs `go build` from `soft-ui/go` and then runs the result. Add `soft-ui/softui.cmd` for Windows.
  - Add `soft-ui/perf/make_yaml_fixture.py`. It runs the Python loader on 20 YAML snippets, including `on:` keys, dates, and bad syntax, and saves the results to `soft-ui/perf/yaml-fixture.json`.
- **Done when:**
  - `(cd soft-ui/go && go test ./...)` passes, with the YAML fixture as one test.
  - `soft-ui/softui render soft-ui/examples/sink.yaml` (the stub) has a wall time of 10 ms or less (median of 9 runs), launcher included.
  - The launcher test passes: with `bin/` empty and a fake `uname`, the launcher runs `go build` from the vendored source with no network.
- **Out of scope here:** any component, and any committed binary. Binaries are committed once, in Step 15.
- **Touches:** `soft-ui/go/**` (new), `soft-ui/softui`, `soft-ui/softui.cmd`, `soft-ui/scripts/build-binaries.sh`, `soft-ui/perf/make_yaml_fixture.py`, `soft-ui/perf/yaml-fixture.json`
- **Depends on:** Step 2.

### Step 4: Data: loaders, dataset steps, and expressions · `[ ]` AUTO · Parallel group: P1 (data, text, and charts)

- **Do:** port into `soft-ui/go/data/`:
  - The loaders: rows, CSV text, TOON text, `.json`, `.jsonl`, `.csv`, `.tsv`, `.yaml`, `.toon`, `.txt`, `.diff` and `.patch`. Also `file#key`, `{file, key}`, parts (`name.key` up to 3 levels), and one object as one row.
  - Type inference (`num`, `date`, `bool`, `str`), and the scalar rules for CSV cells.
  - Each dataset step, in the same order. The steps are `union`, `where`, `explode`, `join`, `add`, and `group` (with `sum`, `mean`, `min`, `max`, and `count`). The others are `pct`, `describe`, `corr`, `pivot`, `then`, `sort` (several columns), `top`, `rename`, and `select`.
  - The expression evaluator, as a parser of its own (no `eval`). It has `+ - * / % **`, comparisons, `and`, `or`, `not`, `x if c else y`, the functions `round` (half to even, like Python), `abs`, `min`, `max`, `len`, `str`, `int`, `float`, `bytes`, `num`, `lower`, `upper`, and `split`. It also has backtick column names and keyword column names such as `from`, and it propagates null the same way. It rejects a call such as `__import__('os')`.
  - The same error text for a missing column, with the list of columns and the order of steps.
- **Done when:**
  - `go test ./data` passes.
  - For each corpus spec that has a top-level `data:` key, the datasets (rows, columns, and types) equal the `data` section of the golden plan. Numbers compare by value, with a tolerance of 1e-9.
  - The cases of `Computed`, `Transforms`, and `RoundTwoFixes` in `test_softui.py` are ported and pass.
- **Out of scope here:** templates, normalisation, and rendering.
- **Touches:** `soft-ui/go/data/**`
- **Depends on:** Step 3.

### Step 5: Text: markdown, formats, tones, and code highlighting · `[ ]` AUTO · Parallel group: P1 (data, text, and charts)

- **Do:** port into `soft-ui/go/text/` the functions of `runtime.js` and `softui.py` that make text:
  - `inline()` and `md()`, `fmt()` for all formats (`int`, `num`, `pct`, `ratio`, `money`, `k`, `ms`, `s`, `bytes`, `date`, `time`, `delta`, `code`, `md`, `raw`, and `.N`), and `shortDate`.
  - `normTone`, `mapTone` with thresholds, `cellTone`, the automatic tones, and the severity order.
  - A small regex code highlighter. It marks keywords, strings, numbers, and comments for Python, JS/TS, Go, YAML, JSON, SQL, bash, and diff. It uses the `hljs-*` class names that the CSS already styles.

  Add `soft-ui/perf/make_text_fixture.js`. It runs the functions of `runtime.js` in Node on about 200 inputs, and saves the results to `soft-ui/perf/text-fixture.json`.
- **Done when:**
  - `go test ./text` passes, with the fixture as one test. For example, `fmt(-1234.5, "money")` gives `−$1,235` with NZD.
  - A benchmark shows that the highlighter handles 1,000 lines of code in 5 ms or less.
- **Out of scope here:** components, and templates.
- **Touches:** `soft-ui/go/text/**`, `soft-ui/perf/make_text_fixture.js`, `soft-ui/perf/text-fixture.json`
- **Depends on:** Step 3.

### Step 6: SVG charts · `[ ]` AUTO · Parallel group: P1 (data, text, and charts)

- **Do:** write `soft-ui/go/svg/`. The package takes the number formatter and the series colour rule as arguments, and does not import the text package.
  - Port `chartModel`, `histModel`, and `linreg`.
  - Draw SVG for each kind: `bar` (vertical, horizontal, stacked), `line`, `area`, `scatter` with trend, `donut`, `waterfall` with subtotals, and `hist`.
  - Each chart has axes and gridlines, marks and bands, a legend, and `<title>` tooltips. The y axis is on the left or the right, and the bars are square or rounded, from a theme flag.
  - Fills use CSS variables (`var(--s1)` to `var(--good)`).
  - Each mark has `data-k` (the category) and `data-s` (the series) for the page script.
  - Each chart is drawn at two widths: wide (640 units) and narrow (340 units). CSS shows one of the two (see Step 11).
- **Done when:**
  - `go test ./svg` passes. For each kind, the mark counts and the axis ticks are right, and a severity series uses the status colours.
  - Eight charts have golden SVG snapshots.
  - A benchmark shows that each chart draws in 1 ms or less.
- **Out of scope here:** the chart component and the page script.
- **Touches:** `soft-ui/go/svg/**`
- **Depends on:** Step 3.

### Step 7: Registry, normalisation, repairs, and templates · `[ ]` AUTO · Parallel group: none

- **Do:**
  - Port `registry.py` into `soft-ui/go/spec/registry.go`: the components, props, aliases, examples, `PROP_ALIASES`, and the chart kinds.
  - Port the normalisation into `soft-ui/go/spec/`. The functions are `normalise_page`, `norm_nodes`, `norm_node`, `find_comp_key`, `norm_props`, `build`, `coerce`, `default_required`, `check_cols`, `resolve_data`, `col_fix`, and `pct_check`. Also port the `fold` wrap and the repair of `stats` items. Keep the "fixed" and "error" lines word for word.
  - Port the template engine (`{{ sum d.col | money }}`). It uses the data and text packages.
  - Add `soft-ui/go/render/render.go`: the render context, the HTML builder, and a registration map. Each render step registers its components in its own file with an `init()` function, so the next steps change no shared file.
  - Add `--dump-plan FILE` to the Go program.
- **Done when:**
  - `go test ./spec` passes.
  - For all 30 corpus specs, the "fixed" and "error" lines equal the golden `.out` files. The plan equals the golden plan, except for the fields that Step 8 makes (the Mermaid `src`, `rows`, `exprs`, and `files`).
  - The `Repairs`, `Templates`, `RoundTwoFixes`, and `NewComponents` cases of `test_softui.py` are ported and pass.
- **Out of scope here:** the derived fields, and HTML.
- **Touches:** `soft-ui/go/spec/**`, `soft-ui/go/render/render.go`, `soft-ui/go/main.go`
- **Depends on:** Step 4, Step 5.

### Step 8: Derived forms: Mermaid source, truth rows, diffs, and notes · `[ ]` AUTO · Parallel group: none

- **Do:** port the work of `finish()` in `softui.py` into `soft-ui/go/spec/derive.go` and `soft-ui/go/spec/mermaid.go`:
  - The Mermaid source for `graph` (groups, node text, signs, tones, edge tones, cycles with the strongly connected parts, and the legend), `er`, `classes`, `sankey` (with the cycle error), and `diagram` (the header guess).
  - The truth-table rows from boolean expressions, and the `decision` weights.
  - The `code` line ranges, and the language from the file name.
  - The `diff` parser for `patch`, and for `before` and `after`.
  - The review notes.
- **Done when:**
  - The plan equals the golden plan for all 30 corpus specs, with no ignored fields. Mermaid text equals the Python text character for character.
  - The remaining cases of `test_softui.py` are ported and pass.
- **Out of scope here:** HTML and SVG.
- **Touches:** `soft-ui/go/spec/derive.go`, `soft-ui/go/spec/mermaid.go`
- **Depends on:** Step 7.

### Step 9: Static layouts and summary parts · `[ ]` AUTO · Parallel group: P2 (static components)

- **Do:** write `soft-ui/go/render/layout.go`. It draws these parts as HTML, with the class names of the runtime, so `style.css` applies unchanged:
  - The page header.
  - `row`, `col`, `grid`, `section`, `sidebar`, and `compare` (side by side).
  - `card` and `float`, which fold with `<details>`.
  - `tabs` and `compare: toggle`, which use radio inputs and CSS.
  - `stat`, `stats`, `kv`, `meter`, `callout`, `text`, `checklist`, and the window wrapper (`.su-win`) with the notes.

  Put the CSS for the radio tabs in `soft-ui/assets/ssr-layout.css`.
- **Done when:**
  - `go test ./render` passes for these parts.
  - A Playwright test with JavaScript turned off loads a page that uses these parts. A click on the second tab shows its panel, and hides the first panel.
  - The text content of each part equals the text that the runtime draws for the same spec.
- **Out of scope here:** the data parts, and the page script.
- **Touches:** `soft-ui/go/render/layout.go`, `soft-ui/assets/ssr-layout.css`, `soft-ui/perf/test_tabs_noscript.js`
- **Depends on:** Step 8.

### Step 10: Static data parts in HTML · `[ ]` AUTO · Parallel group: P2 (static components)

- **Do:** write `soft-ui/go/render/html.go`. It draws these parts:
  - `table`, with groups, tones, bars, `top`, `limit` pages, and rows that expand with `<details>`. Each row carries `data-row` and the raw values of the filter and sort columns as `data-*` attributes.
  - `list`, `board`, `timeline`, `tree`, `filter` (chips with counts), `statement`, `decision`, and `truth`.
  - `code` with notes, and `diff` (split and unified) with notes.

  Two layouts need a choice that the runtime made in the browser. Make them with CSS only:
  - **Table stacking:** Go estimates the width that each table needs, from its column count and its longest values. Go gives the table a class for one width band (`su-stack-480`, `-640`, `-800`, `-960`). A container query for each band stacks the table into cards when its box is narrower.
  - **Diffs:** Go writes both the split and the unified layout. A container query shows the unified layout in a box narrower than 720 px.

  Put this CSS in `soft-ui/assets/ssr-html.css`.
- **Done when:**
  - `go test ./render` passes for these parts.
  - The text content of each part equals the text that the runtime draws for the same spec. One Chromium run on a fixture spec saves the runtime text to `soft-ui/perf/runtime-text-fixture.json` in this step.
  - At 390 px, the bank month-by-month table shows as cards with no script, and at 1280 px it shows as a table.
- **Out of scope here:** the SVG parts.
- **Touches:** `soft-ui/go/render/html.go`, `soft-ui/assets/ssr-html.css`, `soft-ui/perf/runtime-text-fixture.json`
- **Depends on:** Step 8.

### Step 11: Static data parts in SVG · `[ ]` AUTO · Parallel group: P2 (static components)

- **Do:** write `soft-ui/go/render/svgparts.go`. It draws these parts:
  - `chart` (through the `svg` package, with the formatter and the series colours from the text package), `heatmap` (with `worst` and totals), `gantt`, `box`, `forest`, and `treemap`.
  - Each chart is drawn twice, wide and narrow. A container query in `soft-ui/assets/ssr-svg.css` shows the narrow drawing in a box narrower than 520 px. Thus, the labels keep their size on a phone.
  - The treemap places its cells with percentages in a box of fixed height, so the cells scale without script and the text keeps its size.
- **Done when:**
  - `go test ./render` passes for these parts.
  - The treemap cells tile 100% of the box, with a total overlap and gap area under 0.5%.
  - On the gallery data, the `<title>` of each box plot gives the same n, median, and quartiles as the runtime tooltip. Each forest row gives the same estimate and interval text as the runtime.
  - At 390 px, the chart axis labels in the screenshot are 10 px or larger.
- **Out of scope here:** the motion.
- **Touches:** `soft-ui/go/render/svgparts.go`, `soft-ui/assets/ssr-svg.css`
- **Depends on:** Step 6, Step 8.

### Step 12: Assemble the static page · `[ ]` AUTO · Parallel group: none

- **Do:**
  - Write the page in `soft-ui/go/render/page.go`. It holds the static HTML from Steps 9 to 11, then the CSS, then a compact data block. The CSS is `style.css`, the three `ssr-*.css` files, and the theme file.
  - The data block holds only the columns that filters and aggregates use, and the row counts. It does not hold the full datasets.
  - Apply the CSS changes from `probe-notes.md`.
  - Replace the web fonts with system font stacks. Default theme: `system-ui` and `ui-monospace`. Quarterly: Georgia and "Times New Roman" (serif), "Helvetica Neue" and Arial (sans), and "Arial Narrow" and "Helvetica Neue" (condensed).
  - Complete the `render` command: `--fast`, `--shot`, `--artifact`, `--inline`, `--theme`, and `--dump-plan`. The browser check is `node scripts/verify.js`. If Node or Playwright is missing, print "check skipped", as now.
  - Diagram pages load Mermaid. `--inline` downloads Mermaid once into the cache (`~/.cache/soft-ui`), as now. Chart.js and highlight.js go away.
  - Store the page script in `<script type="text/plain" id="su-runtime">` with a tiny loader that starts it with `new Function` in a `setTimeout` after `load`.
- **Done when:**
  - The four test pages render with the Go program, and pass the browser check.
  - With JavaScript turned off, each page shows all its content, and each tab and fold works.
  - The comparison report is 400 KB or less without libraries.
  - No rendered page holds `fonts.googleapis`.
  - `go test ./...` passes.
- **Out of scope here:** the page script (Step 13), and the budget gate.
- **Touches:** `soft-ui/go/render/page.go`, `soft-ui/go/main.go`, `soft-ui/assets/style.css`, `soft-ui/assets/themes/quarterly.css` (fonts only)
- **Depends on:** Step 9, Step 10, Step 11.

### Step 13: The page script: interaction and motion · `[ ]` AUTO · Parallel group: none

- **Do:**
  - Write `soft-ui/assets/enhancer.js` and delete `soft-ui/assets/runtime.js`. The script does these things after the page is drawn:
    - Sort a table by a column, and search and filter by chips (from the `data-*` attributes).
    - Click on a bar, a heatmap cell, or a tile to filter. Recount the stat tiles and the chip counts. Highlight the selected marks on the charts. Show the page numbers of a `limit` table.
    - Show a tooltip (square and black in `quarterly`), and keep the folds and tabs that need no script.
    - Start the bounce motion with an `IntersectionObserver`, and the count-up of the stat numbers. Both stay off for reduced motion.
    - Start Mermaid on a diagram page, and start it again when the theme changes.
  - The script does not change the size or the structure of the page on load.
  - Write `soft-ui/perf/test_interaction.js` (Playwright). It tests each interaction above.
- **Done when:**
  - `node soft-ui/perf/test_interaction.js` passes:
    - A click on a filter chip hides rows, recounts the tiles and the chip counts, and highlights the matching bars.
    - A sort click orders the rows.
    - A click on a bar filters the table.
  - On the comparison report, a MutationObserver counts zero `childList` changes between DOMContentLoaded and the first user input. Text changes from the count-up are allowed.
  - The drawn time with the stored script is 5 ms or less from the drawn time with the script removed.
- **Out of scope here:** the budget gate.
- **Touches:** `soft-ui/assets/enhancer.js`, `soft-ui/assets/runtime.js` (deleted), `soft-ui/assets/themes/quarterly.css` (the motion rules only), `soft-ui/perf/test_interaction.js`
- **Depends on:** Step 12.

### Step 14: The budget gate · `[ ]` AUTO · Parallel group: none

- **Do:**
  - `verify.js` measures the drawn time (median of 3) on a desktop and at 4× CPU, and the layout-shift score.
  - Over 80 ms, `render` prints a new line: `check warning page drawn in N ms (budget 80 ms) on phone: slowest part X`. "Slowest part" is the largest node by layout cost.
  - For a page with a diagram, the line says "diagram page" and names the looser budget. That budget is 300 ms on a desktop and 1,000 ms on the phone.
  - Add `soft-ui/go/budget_test.go`. It runs the binary with `--fast` 5 times on each example page, and runs `time_load.js`. It fails when a build takes more than 80 ms. It also fails when a non-diagram page takes more than 80 ms to draw, or when the layout-shift score is above 0.
  - Add the Go tests to the test list in `AGENTS.md`.
- **Done when:**
  - `(cd soft-ui/go && go test ./...)` passes on the gallery, sink, report, and synthetic bank pages.
  - A deliberately slow fixture (`soft-ui/perf/slow-fixture.yaml`, with 2,000 table rows) makes `render` print the warning, and makes the budget test fail.
- **Out of scope here:** making a user page with large data fast.
- **Touches:** `soft-ui/scripts/verify.js`, `soft-ui/go/budget_test.go`, `soft-ui/go/render/page.go` (the warning only), `soft-ui/perf/slow-fixture.yaml`, `AGENTS.md` (the test list only)
- **Depends on:** Step 13.

### Step 15: Cutover, binaries, and docs · `[ ]` AUTO · Parallel group: none

- **Do:**
  - Run `soft-ui/scripts/build-binaries.sh`, and commit the six binaries once. Rebuild them only when the Go source changes after this step, to limit the growth of the git history.
  - Delete `softui.py`, `registry.py`, `transforms.py`, and `test_softui.py`. Remove the Python tests that Go replaces from the list in `AGENTS.md`.
  - Update `soft-ui/SKILL.md` (200 words or less; the command is `soft-ui/softui render`; `--inline` is needed only for diagram pages), `soft-ui/README.md` (how a page is built, the budgets, system fonts, the binaries and the `go build` fallback, `soft-ui/perf/`), and the `catalog` and `explain` text (in the Go source).
  - Update `plans/README.md`, and any example spec that the engine changes break.
- **Done when:**
  - A copy of the `soft-ui` folder in a temporary directory, with `go` removed from `PATH`, renders `sink.yaml` with "check ok".
  - The launcher runs `go build` when `bin/` is empty, and works with no network.
  - `check_writing.py` gives "OBEYS THE GUIDELINES" for `SKILL.md`, `README.md`, and this plan. `check_skill_form.py soft-ui/SKILL.md` passes.
  - Each example renders with "check ok".
- **Out of scope here:** `soft-ui/eval/runs/`.
- **Touches:** `soft-ui/bin/**`, `soft-ui/scripts/*.py` (deleted), `soft-ui/SKILL.md`, `soft-ui/README.md`, `soft-ui/go/**` (the catalog text only), `soft-ui/examples/*.yaml`, `soft-ui/eval/report.yaml`, `AGENTS.md`, `plans/README.md`
- **Depends on:** Step 14.

### Step 16: "After" screenshots, the review page, and the full test suite · `[ ]` AUTO · Parallel group: none

- **Do:**
  - Render the four test pages with the Go program, and save the screenshots to `soft-ui/perf/after/`, with the same names as in Step 2.
  - Make `soft-ui/perf/compare.html`. It shows each before and after pair side by side, with the timings from both runs. The synthetic bank pair is the only one with fake data. The real bank pair stays in the scratchpad, and goes to the user with `SendUserFile`.
  - Run each test in `AGENTS.md`.
- **Done when:**
  - All tests pass. `pdlc_known_files.py --check` is allowed to fail with its known "repository is shallow" message only.
  - `compare.html` shows the pairs from the repository pages, and the user has the real bank pairs.
  - The timing table shows each non-diagram page at 80 ms or less. This holds for the build and for the load, on a desktop and on a phone.
- **Out of scope here:** visual tuning. The user reviews the screenshots and asks for changes.
- **Touches:** `soft-ui/perf/after/**`, `soft-ui/perf/compare.html`
- **Depends on:** Step 15.

**Parallel groups:** (each step in a group has its own folder or file, so no file is shared)

- **P1 (data, text, and charts)** is Steps 4, 5, and 6. They write `go/data/`, `go/text/`, and `go/svg/`. The chart package takes the formatter and the colour rule as arguments, so Step 6 does not depend on Step 5.
- **P2 (static components)** is Steps 9, 10, and 11. They write `layout.go`, `html.go`, and `svgparts.go`, and each has its own CSS file. They depend only on Step 7 and Step 8, and those steps finish before P2 (static components) starts. Step 11 also depends on Step 6, which is in P1 (data, text, and charts).
- Steps 1, 2, 3, 7, 8, and 12 to 16 run alone. Step 1 tests the riskiest assumption. The other steps are joins, or they depend on the step before them.

## Verification and rollback

- **Human verifies by:**
  - Looking at the before and after screenshots of the four test pages, at phone and desktop width, in light and dark (`soft-ui/perf/compare.html`, plus the real bank pairs in the side panel).
  - Reading the timing table in the same page.
  - Not covered: agents using the new `catalog` text. The plan does not re-run the eval. The golden test of the repair lines is the substitute.
  - Not covered: the Windows and ARM binaries. They compile, but the plan runs only the Linux x86 binary. A test with a fake `uname` checks that the launcher picks the right name.
- **Failing looks like:**
  - A build or a load over 80 ms on a non-diagram example.
  - A golden file that differs (a repair line, or a plan field).
  - A part that the script draws again or resizes on load (the MutationObserver check fails).
  - A number that differs between the before and after screenshots.
  - A theme that changes apart from the fonts.
  - A copied folder that does not run.
- **Rollback:** `git revert` of the commits of this plan, one for each step. The "before" screenshots, timings, and goldens in `soft-ui/perf/` stay as the baseline. Reverting Step 15 restores the Python program and removes the binaries from the tree, but the binaries stay in the git history.
- **Kill criteria:**
  - Step 1 cannot draw the static page in 80 ms at 4× CPU, even with `content-visibility` and less CSS.
  - A golden difference in Step 7 or Step 8 stays, because only a new wording of a repair line would remove it. The user does not accept that wording.
  - The static comparison report is over 400 KB, and no change makes it smaller.

## Progress log

The log has one entry for each step. Add each entry at execution time, not before. The newest entry is last. This log is the only memory that survives between sessions, so record the decisions, not only the actions.
