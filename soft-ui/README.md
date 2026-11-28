# soft-ui

`/soft-ui` builds a report page from a short YAML spec. The agent names the components
and the data. The script builds the page, checks it in a browser, and reports each
problem. A page that took a long hand-written HTML file takes a spec of about 30 lines.

## How it works

1. The agent runs `python3 scripts/softui.py catalog`. The command prints one line for each
   component, in about 850 tokens.
2. The agent writes a spec, for example:

   ```yaml
   title: Test run 4120
   data: {runs: results.json}
   layout:
   - stats: [{label: Passed, value: 412, tone: good}, {label: Failed, value: 3, tone: bad}]
   - row:
     - chart: {data: runs, x: suite, y: ms, agg: sum}
     - table: {data: runs, cols: [test, status, ms], group: status}
       w: 2
   ```

3. The agent runs `python3 scripts/softui.py render spec.yaml`. The script does these
   steps:
   - The script loads the data.
   - The script fixes small mistakes, for example a wrong component name, a prop alias, or the
     case of a column name. It prints one "fixed" line for each fix, with the right form.
   - The script stops on an error that it cannot fix, and writes nothing. It prints the
     available names, for example the columns of the dataset.
   - The script writes one HTML file, and loads the file in headless Chromium. It reports script
     errors, Mermaid syntax errors, and sideways scroll at phone width.

## The parts

| Part | What it is |
|---|---|
| Layout | `row`, `col`, `grid`, `tabs`, `card`, `section`, `sidebar`, `compare`, `float` |
| Summary | `stat`, `stats`, `kv`, `meter`, `callout`, `text` |
| Data | `table`, `chart` (bar, line, area, scatter with trend, donut, waterfall, hist), `heatmap`, `list`, `board`, `checklist`, `timeline`, `gantt`, `tree`, `filter` |
| Finance and statistics | `statement` (P&L with subtotals and variance), `box`, `forest` |
| Structure and choices | `treemap`, `decision` (weighted options), `truth` (truth table from expressions) |
| Code | `code`, `diff` (both take review `notes` that show under their line) |
| Diagram | `diagram` (Mermaid source), `graph` (edges, with groups, tones, and + / − signs), `sankey`, `er`, `classes` |

A `filter` node filters every node on the same dataset. Tables and lists also have their
own `group`, `filter`, and `search`. Values such as `high`, `fail`, and `done` get a tone
colour with no extra props.

## Data

Give each dataset in `data:` as one of these:

- A list of rows.
- CSV text, or TOON tabular text (`[3]{a,b}:` then one row on each line).
- A path to a `.json`, `.jsonl`, `.csv`, `.tsv`, or `.yaml` file. Add `{file: x.json, key: a.b}`
  to select an array inside the file.

A node can also take its data inline. A dataset can also shape its rows with `where`,
`explode`, `join`, `add`, `group` with `sum`, `mean`, `min`, or `max`, `pct`, `describe`,
`corr`, `sort`, and `top`. Run `softui.py explain data` for the full list.

## Why YAML and not TOON

The agent writes the spec, so the accuracy of the agent's output is more important than
the token count of its input. Studies of model output found that models write JSON and
YAML more correctly than TOON (arXiv 2601.12014, arXiv 2605.29676). TOON saves the most
tokens on flat tables, so soft-ui accepts TOON text for a dataset.

## Files

| File | What it holds |
|---|---|
| `SKILL.md` | The skill |
| `scripts/softui.py` | The command: `catalog`, `explain`, `render` |
| `scripts/registry.py` | Each component: props, aliases, and example. The catalog reads it. |
| `scripts/verify.js` | The browser check |
| `assets/runtime.js`, `assets/style.css` | The page runtime and style, put into each page |
| `examples/sink.yaml` | One node of each core kind |
| `examples/gallery.yaml` | The finance, statistics, structure, logic, and options components |
| `eval/` | The comparison of hand-built pages and soft-ui pages |

## Needs

Python 3 with PyYAML. Without PyYAML, write the spec as JSON. The browser check needs Node
and Playwright, and the script skips the check if they are missing. The page loads
Chart.js, highlight.js, and Mermaid from a CDN, and only the libraries that it uses.

## Tests

```
python3 soft-ui/scripts/test_softui.py
```
