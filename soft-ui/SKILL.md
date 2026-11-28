---
name: soft-ui
description: >
  Builds a report page from a short YAML spec, so the agent does not write HTML by hand.
  Has layout primitives: row, col, grid, tabs, card, section, sidebar, compare, and float.
  Its components show dashboards, tables, and charts. They also show a P&L statement,
  a waterfall, a histogram, a box plot, a forest plot, causal graphs, and a Sankey. Others
  show ER, class, and Mermaid diagrams, a treemap, diffs with review notes, truth tables,
  and a decision matrix.
  Shapes data with filters, joins, groups, and computed columns. Fixes small mistakes and
  says how to write them next time, then checks the page in a browser. Use when the user
  says "/soft-ui", or asks for data, a diff, a model, or a plan as a page. Also
  use when a different skill must show its output to the user as a page.
---

# Soft UI

## Goal

Show results to the user as one checked HTML page. The agent writes only a short YAML
spec. `scripts/softui.py` builds and checks the page.

## Inputs

- The data: rows, CSV text, or files.
- `python3 scripts/softui.py catalog`, then `explain NAME` or `explain data`.

## Outputs

- `<name>.yaml`: the spec.
- `<name>.html` and `<name>.png`, from `render <name>.yaml --shot <name>.png`. With the
  Artifact tool, also add `--artifact` and publish the page. For a file that the user
  opens, add `--inline`.

## Constraints

- Run `catalog` first. Do not read the scripts.
- Give each data file by its path, and shape it with the dataset steps. Do not type
  numbers that the data holds: write `{{ sum d.col | money }}` in text.
- Open with a `callout` that answers the question of the reader. Give each chart a
  `note` that says what the chart shows.
- After a "fixed" line, use its "Next time" form. After an "error", fix the spec. Do
  not write HTML by hand.

## Done when

- `render` prints "check ok".
- The screenshot shows the right numbers.
- The user has the page or its Artifact link.
