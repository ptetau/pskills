---
name: soft-ui
description: >
  Builds a report page from a short YAML spec, so the agent does not write HTML by hand.
  Has eight layout primitives: row, col, grid, tabs, card, section, sidebar, and float.
  Its data components are stat tiles, tables that group, filter, and sort, charts, and
  heatmaps. Others show item lists, kanban boards, Gantt charts, trees, diffs with review
  notes, code, and Mermaid diagrams. Takes data inline, as CSV or TOON text, or as a JSON, CSV, or YAML
  file. Checks the spec and fixes small mistakes. Tells the agent how to write each fix
  next time. Then loads the page in a browser to make sure that it draws. Use when the
  user says "/soft-ui", or asks for data, findings, a diff, or a plan as a page. Also use when a different skill must show its output to the user as a page.
---

# Soft UI

## Goal

Show results to the user as one checked HTML page. The agent writes only a short YAML
spec. `scripts/softui.py` builds the page, checks it in a browser, and reports each
problem.

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
- When a file holds the data, give its path. Do not copy the data into the spec.
- Put the summary first: stat tiles, then charts, then the detail.
- When `render` prints "fixed", use the "Next time" form in later specs.
- When `render` prints "error", fix the spec and render again. Do not write HTML by
  hand.

## Done when

- `render` prints "check ok".
- The user has the page or its Artifact link.
