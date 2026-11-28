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

- The data to show: rows, CSV text, or a file that a different skill wrote.
- `python3 scripts/softui.py catalog`: one line for each component.
  `explain NAME [NAME ...]` gives the props and an example.

## Outputs

- `<name>.yaml`: the spec.
- `<name>.html`: the page, from `render <name>.yaml`. With the Artifact tool, render
  with `--artifact` and publish the page.

## Constraints

- Run `catalog` before the first spec of a session. Do not read the scripts.
- When a file holds the data, give its path. Do not copy the data into the spec. Shape
  it with the dataset steps in `explain data`, not with numbers worked out by hand.
- Put the summary first: stat tiles, then charts, then the detail.
- When `render` prints "fixed", use the "Next time" form in later specs.
- When `render` prints "error", fix the spec. Do not write HTML by hand.

## Done when

- `render` prints "check ok".
- The user has the page or its Artifact link.
