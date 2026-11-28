"""The component registry of soft-ui.

This file is the one source of truth for each component: its props, its shorthand, its
aliases, and its example. The catalog, the explain text, and the spec checks all read it.
"""

TONES = ["good", "warn", "bad", "info", "neutral"]
FMTS = ["int", "num", "pct", "ms", "s", "bytes", "date", "time", "delta", "code", "md", "raw"]


def P(t, req=False, enum=None, default=None, doc=""):
    return {"t": t, "req": req, "enum": enum, "default": default, "doc": doc}


# Props that every node accepts.
COMMON = {
    "title": P("str", doc="heading shown above the node"),
    "note": P("str", doc="caption shown below the node (markdown)"),
    "span": P("int", doc="columns to span inside a grid"),
    "w": P("num", doc="relative width inside a row (default 1)"),
    "h": P("int", doc="max height in px; content scrolls"),
    "id": P("str", doc="anchor id"),
    "where": P("map", doc="keep rows that match, e.g. {sev: high} or {sev: [high, med]}"),
}

C = {}


def comp(name, group, doc, props, short=None, aliases=(), example="", data=False):
    C[name] = {"group": group, "doc": doc, "props": props, "short": short,
               "aliases": list(aliases), "example": example.strip("\n"), "data": data}


# ---- layout -------------------------------------------------------------------------

comp("row", "layout", "children side by side; stacks to one column below `min` px each",
     {"items": P("nodes", req=True), "min": P("int", default=240, doc="min child width before the row stacks"),
      "gap": P("enum", enum=["s", "m", "l"], default="m"),
      "align": P("enum", enum=["start", "center", "stretch"], default="stretch")},
     short="items", aliases=["hstack", "split", "flex"], example="""
- row:
  - stat: {label: Passed, value: 412, tone: good}
  - stat: {label: Failed, value: 3, tone: bad}
  - chart: {kind: bar, data: runs, x: suite, y: ms}
    w: 2
""")

comp("col", "layout", "children stacked top to bottom",
     {"items": P("nodes", req=True), "gap": P("enum", enum=["s", "m", "l"], default="m")},
     short="items", aliases=["column", "vstack"], example="""
- col:
  - text: First block
  - text: Second block
""")

comp("grid", "layout", "auto-fit grid of equal cells; children may set `span`",
     {"items": P("nodes", req=True), "min": P("int", default=260, doc="min cell width in px"),
      "cols": P("int", doc="fixed column count (overrides min)"),
      "gap": P("enum", enum=["s", "m", "l"], default="m")},
     short="items", aliases=["tiles", "masonry"], example="""
- grid:
    min: 300
    items:
    - chart: {kind: line, data: lat, x: day, y: p95}
    - chart: {kind: bar, data: lat, x: day, y: errors}
    - table: {data: lat}
      span: 2
""")

comp("tabs", "layout", "one tab per child; the child's `title` is the tab label",
     {"items": P("nodes", req=True)}, short="items", aliases=["tabset"], example="""
- tabs:
  - table: {data: failing}
    title: Failing
  - table: {data: flaky}
    title: Flaky
""")

comp("card", "layout", "bordered panel with a title; `collapse: true` makes it fold",
     {"items": P("nodes", req=True), "collapse": P("bool", default=False),
      "open": P("bool", default=True), "tone": P("enum", enum=TONES)},
     short="items", aliases=["panel", "box"], example="""
- card:
    title: Repro steps
    collapse: true
    items:
    - code: {src: "curl -X POST /cart", lang: bash}
""")

comp("section", "layout", "page section with a heading and no border",
     {"items": P("nodes", req=True)}, short="items", aliases=["part", "chapter"], example="""
- section:
    title: Latency
    items:
    - chart: {kind: line, data: lat, x: day, y: [p50, p95]}
""")

comp("sidebar", "layout", "narrow side column next to a main column",
     {"side": P("nodes", req=True), "main": P("nodes", req=True),
      "at": P("enum", enum=["left", "right"], default="left"),
      "width": P("int", default=300, doc="side width in px")},
     aliases=["split-view"], example="""
- sidebar:
    at: left
    side:
    - tree: {data: files, path: path}
    main:
    - diff: {patch: changes.diff}
""")

comp("float", "layout", "floating island pinned to a corner of the screen; folds",
     {"items": P("nodes", req=True), "at": P("enum", enum=["br", "bl", "tr", "tl"], default="br"),
      "width": P("int", default=320)},
     short="items", aliases=["island", "overlay", "popover"], example="""
- float:
    title: Legend
    at: br
    items:
    - kv: {Owner: platform, Build: "#4120"}
""")

# ---- summary ------------------------------------------------------------------------

comp("stat", "summary", "one big number with label, delta and optional sparkline",
     {"label": P("str", req=True), "value": P("any", doc="the number; or give data + agg"), "unit": P("str"),
      "delta": P("any", doc="change vs before, e.g. -12% or 3"),
      "good": P("enum", enum=["up", "down"], default="up", doc="which delta direction is good"),
      "tone": P("enum", enum=TONES), "sub": P("str", doc="small line under the value"),
      "spark": P("list", doc="list of numbers for a sparkline"),
      "data": P("data", doc="compute value from data (follows filters)"),
      "agg": P("enum", enum=["count", "sum", "mean", "min", "max"], default="count", doc="with data"),
      "col": P("col", doc="column to aggregate (with data)")},
     aliases=["kpi", "metric"], example="""
- stat: {label: p95 latency, value: 412, unit: ms, delta: +18%, good: down, spark: [300, 320, 390, 412]}
""")

comp("stats", "summary", "row of stat tiles: a list, one tile per row of `data`, or counts `by` a column",
     {"items": P("list", doc="list of stat props"), "data": P("data"),
      "label": P("col", doc="column for labels (with data)"), "value": P("col", doc="column for values (with data)"),
      "tone": P("col", doc="column for tone (with data)"),
      "by": P("col", doc="one tile per value of this column, with its row count (follows filters)"),
      "total": P("str", doc="with by: add a first tile with this label and the total count"),
      "order": P("list", doc="with by: tile order")},
     short="items", aliases=["kpis", "metrics", "tiles-row"], data=True, example="""
- stats:
  - {label: Findings, value: 14}
  - {label: High, value: 3, tone: bad}
- stats: {data: findings, by: sev, total: Findings}   # counts per severity, follows filters
""")

comp("kv", "summary", "key/value pairs (a definition list)",
     {"pairs": P("map", req=True), "cols": P("int", default=1, doc="number of columns"),
      "data": P("data", doc="a single JSON object (or key/value rows) instead of pairs"),
      "keys": P("list", doc="with data: only these keys, in this order")},
     short="pairs", aliases=["facts", "dl", "keyvalue", "keyvalues"], example="""
- kv: {Branch: feat/cart, Base: main, Author: dana, Commits: 7}
- kv: {data: run.json, keys: [app, commit, minutes]}
""")

comp("meter", "summary", "progress bar for value out of max",
     {"value": P("num", req=True), "max": P("num", default=100), "label": P("str"),
      "tone": P("enum", enum=TONES)}, aliases=["progress", "gauge"], example="""
- meter: {label: Coverage, value: 81, max: 100, tone: good}
""")

comp("callout", "summary", "highlighted message box (markdown)",
     {"text": P("text", req=True), "tone": P("enum", enum=TONES, default="info")},
     short="text", aliases=["alert", "admonition", "banner", "warning", "info", "tip", "notice"], example="""
- callout: {tone: warn, text: "3 tests are **flaky** and were retried."}
""")

comp("text", "summary", "markdown text",
     {"md": P("text", req=True)}, short="md", aliases=["markdown", "paragraph", "prose"],
     example="""
- text: |
    The cart service owns **pricing**. See `cart/price.py`.
""")

# ---- data ---------------------------------------------------------------------------

comp("table", "data", "sortable table; group, filter, search, inline bars, tones",
     {"data": P("data", req=True),
      "cols": P("cols", doc="columns to show, in order: name or {key, label, fmt, w}"),
      "sort": P("str", doc="column to sort by; prefix - for descending"),
      "group": P("col", doc="group rows under a heading per value"),
      "filter": P("cols", doc="columns that get a filter dropdown; true = auto"),
      "search": P("bool", default=False, doc="add a text search box"),
      "limit": P("int", doc="rows per page"),
      "bar": P("cols", doc="numeric columns that get an inline bar"),
      "tone": P("map", doc="{col: {value: tone}} colours cells, e.g. {sev: {high: bad}}"),
      "fmt": P("map", doc="{col: fmt}; fmt is one of " + ", ".join(FMTS)),
      "dense": P("bool", default=False)},
     short="data", aliases=["grid-table", "datatable", "tbl"], data=True, example="""
- table:
    data: findings
    cols: [id, title, sev, flow]
    sort: -sev
    group: flow
    filter: [sev]
    tone: {sev: {high: bad, medium: warn, low: info}}
""")

comp("chart", "data", "bar / line / area / scatter / donut; severity series get status colours",
     {"data": P("data", req=True), "kind": P("enum", enum=["bar", "line", "area", "scatter", "donut"], default="bar"),
      "x": P("col", req=True, doc="category or time column"),
      "y": P("cols", doc="value column(s); omit with agg: count"),
      "agg": P("enum", enum=["none", "count", "sum", "mean", "min", "max"], default="none",
               doc="group rows by x (and series) and aggregate y"),
      "series": P("col", doc="split into one series per value of this column"),
      "stack": P("bool", default=False), "horizontal": P("bool", default=False),
      "sort": P("enum", enum=["none", "x", "y", "-y"], default="none"),
      "limit": P("int", doc="keep the first N x values after sort"),
      "fmt": P("enum", enum=FMTS, doc="value format"),
      "zero": P("bool", default=True, doc="start the value axis at zero"),
      "mark": P("list", doc="reference lines: [{y: 300, label: SLO}]"),
      "height": P("int", default=260)},
     aliases=["plot"], data=True, example="""
- chart: {kind: line, data: lat, x: day, y: [p50, p95], fmt: ms, mark: [{y: 300, label: SLO}]}
- chart: {kind: bar, data: findings, x: sev, agg: count, series: flow, stack: true}
""")

comp("heatmap", "data", "grid of cells coloured by value (x by y)",
     {"data": P("data", req=True), "x": P("col", req=True), "y": P("col", req=True),
      "v": P("col", doc="value column; omit to count rows"),
      "agg": P("enum", enum=["count", "sum", "mean", "max"], default="sum"),
      "scale": P("enum", enum=["seq", "div"], default="seq", doc="seq = one hue; div = below/above zero"),
      "fmt": P("enum", enum=FMTS), "labels": P("bool", default=False, doc="print the value in each cell")},
     aliases=["matrix"], data=True, example="""
- heatmap: {data: churn, x: week, y: file, v: lines}
""")

comp("list", "data", "list of item cards: title, body, badges; groupable",
     {"data": P("data", req=True), "head": P("col", req=True, doc="column for the item title"),
      "body": P("col", doc="column for the body (markdown)"),
      "badges": P("cols", doc="columns shown as badges"),
      "code": P("col", doc="column shown as a code block"),
      "group": P("col"), "tone": P("map", doc="{col: {value: tone}}; sets the stripe colour"),
      "filter": P("cols"), "search": P("bool", default=False),
      "collapse": P("bool", default=False, doc="fold each body until clicked")},
     aliases=["findings", "cards", "feed", "issues"], data=True, example="""
- list:
    data: findings
    head: title
    body: detail
    badges: [sev, flow]
    code: repro
    group: sev
    tone: {sev: {high: bad, medium: warn}}
""")

comp("board", "data", "kanban board: one column per value of `by`",
     {"data": P("data", req=True), "by": P("col", req=True), "head": P("col", req=True),
      "order": P("list", doc="column order of `by` values"), "badges": P("cols"),
      "body": P("col"), "tone": P("map")},
     aliases=["kanban", "swimlanes"], data=True, example="""
- board: {data: changes, by: status, head: title, order: [planned, building, verify, done], badges: [owner]}
""")

comp("checklist", "data", "items with done / not done",
     {"items": P("list", doc="strings; prefix [x] for done"), "data": P("data"),
      "text": P("col"), "done": P("col")},
     short="items", aliases=["todo", "todos"], data=True, example="""
- checklist: ["[x] Lock the checks", "[x] Build", "[ ] Verify", "[ ] Show"]
""")

comp("timeline", "data", "events in date order, as a vertical line",
     {"data": P("data", req=True), "at": P("col", req=True, doc="date or time column"),
      "text": P("col", req=True), "tone": P("map"), "badges": P("cols")},
     aliases=["changelog"], data=True, example="""
- timeline: {data: events, at: when, text: what, badges: [who]}
""")

comp("gantt", "data", "bars on a time axis: one per task",
     {"data": P("data", req=True), "task": P("col", req=True), "start": P("col", req=True),
      "end": P("col", doc="end date; or use days"), "days": P("col", doc="duration in days"),
      "group": P("col"), "tone": P("map"), "today": P("str", doc="date of a 'today' line")},
     aliases=["roadmap", "schedule"], data=True, example="""
- gantt: {data: plan, task: step, start: from, end: to, group: phase, tone: {status: {late: bad}}}
""")

comp("tree", "data", "folding file or object tree from paths",
     {"paths": P("list", doc="list of paths a/b/c"), "data": P("data"),
      "path": P("col", doc="path column (with data)"), "badges": P("cols"),
      "tone": P("map"), "open": P("int", default=2, doc="levels open at start")},
     short="paths", aliases=["filetree", "hierarchy", "outline"], data=True, example="""
- tree: {data: changed, path: file, badges: [added, removed]}
""")

comp("filter", "data", "filter chips + search; filters every node on the same dataset (tables, lists, charts, stats...)",
     {"data": P("data", req=True), "fields": P("cols", req=True), "search": P("bool", default=True)},
     aliases=["facets", "slicer"], data=True, example="""
- filter: {data: findings, fields: [sev, flow]}
""")

# ---- code ---------------------------------------------------------------------------

comp("code", "code", "highlighted code; optional line range and marked lines",
     {"src": P("text", req=True, doc="code text, or a file path"), "lang": P("str"),
      "lines": P("str", doc="line range to show, e.g. 10-40"),
      "mark": P("list", doc="line numbers to highlight"),
      "start": P("int", default=1, doc="number of the first line"),
      "wrap": P("bool", default=False),
      "notes": P("data", doc="notes shown under their line: rows with line, text (and title, severity)")},
     short="src", aliases=["snippet", "codeblock", "stacktrace"], example="""
- code: {src: src/cart.py, lang: python, lines: 40-60, mark: [52]}
""")

comp("diff", "code", "side-by-side or unified diff from a patch, or from before/after",
     {"patch": P("text", doc="unified diff text, or a .diff/.patch file"),
      "before": P("text", doc="old text or file"), "after": P("text", doc="new text or file"),
      "mode": P("enum", enum=["split", "unified"], default="split"),
      "lang": P("str"), "files": P("list", doc="only show these files"),
      "context": P("int", default=3),
      "notes": P("data", doc="review notes shown under their line: rows with file, line, text (and title, severity)")},
     aliases=["compare"], example="""
- diff: {patch: changes.diff, mode: split}
- diff: {before: old.yaml, after: new.yaml, mode: unified}
- diff: {patch: pr.diff, notes: review}   # review rows: file, line, title, comment, severity
""")

# ---- diagram ------------------------------------------------------------------------

comp("diagram", "diagram", "Mermaid diagram: flowchart, sequence, class, state, er, gantt, mindmap",
     {"src": P("text", req=True, doc="Mermaid source")}, short="src",
     aliases=["mermaid", "sequence", "flowchart", "flow", "class", "classdiagram", "state", "er", "uml",
              "sequencediagram", "mindmap"], example="""
- diagram: |
    sequenceDiagram
      Client->>API: POST /cart
      API-->>Client: 201
""")

comp("graph", "diagram", "flowchart drawn from an edge list in data",
     {"data": P("data", req=True), "from": P("col", req=True), "to": P("col", req=True),
      "label": P("col", doc="edge label column"), "dir": P("enum", enum=["LR", "TD", "RL", "BT"], default="LR"),
      "group": P("col", doc="put `from` nodes in a box per value of this edge column"),
      "nodes": P("data", doc="node rows (name + attributes) for by and tone"),
      "key": P("str", doc="node name column in nodes (default name/id)"),
      "by": P("str", doc="box nodes by this column of nodes, e.g. kind"),
      "tone": P("map", doc="{nodes column: {value: tone}}; colours nodes")},
     aliases=["network", "dag", "dependency-graph"], data=True, example="""
- graph: {data: deps, from: src, to: dst, dir: LR}
- graph: {data: d.calls, from: from, to: to, label: via, nodes: d.components, by: kind, tone: {volatility: {high: bad}}}
""")

PAGE_KEYS = {
    "title": P("str", req=True), "subtitle": P("str"), "meta": P("any", doc="list of badges, or a map"),
    "data": P("map", doc="named datasets"), "layout": P("nodes", req=True),
    "width": P("enum", enum=["narrow", "normal", "wide", "full"], default="normal"),
    "accent": P("str", doc="CSS colour for the accent"),
}

# Common wrong prop names, mapped to the right one. Fuzzy matching catches the rest.
PROP_ALIASES = {
    "columns": "cols", "fields": "cols", "group_by": "group", "groupby": "group", "groupBy": "group",
    "sort_by": "sort", "sortby": "sort", "orderby": "sort", "order_by": "sort",
    "type": "kind", "chart": "kind", "x_axis": "x", "xaxis": "x", "y_axis": "y", "yaxis": "y",
    "values": "y", "value_col": "v", "color": "series", "colour": "series", "hue": "series",
    "language": "lang",  "source": "src", "content": "src", "body_md": "body",
    "children": "items", "content_items": "items", "nodes": "items", "blocks": "items",
    "label_col": "label", "aggregate": "agg", "aggregation": "agg", 
    "highlight": "mark", "lines_marked": "mark", "range": "lines", "old": "before", "new": "after",
    "left": "before", "right": "after", "message": "text", "body_text": "body", 
    "heading": "title", "caption": "note", "subtitle": "note", "width_px": "width", "max_height": "h",
    "height_px": "height", "title_col": "head", "header": "head",  
    "date": "at", "time": "at", "when": "at", "duration": "days", "from_col": "from", "to_col": "to",
    "direction": "dir", "orientation": "dir", "per_page": "limit", "page_size": "limit", 
    "pairs_map": "pairs", "data_ref": "data", "dataset": "data", "source_data": "data", "rows": "data",
    "filters": "filter", "searchable": "search", "stacked": "stack", "horiz": "horizontal",
}

# Words an agent uses for a chart kind, mapped to a chart. `bar: {...}` = `chart: {kind: bar, ...}`.
CHART_KINDS = {"bar": "bar", "bars": "bar", "barchart": "bar", "column-chart": "bar", "histogram": "bar",
               "line": "line", "linechart": "line", "lines": "line", "area": "area", "areachart": "area",
               "scatter": "scatter", "scatterplot": "scatter", "dots": "scatter", "pie": "donut",
               "donut": "donut", "doughnut": "donut", "piechart": "donut"}

# Mermaid header for each diagram alias, used when the source has no header.
MERMAID_HEADERS = {"sequence": "sequenceDiagram", "sequencediagram": "sequenceDiagram",
                   "flowchart": "flowchart TD", "flow": "flowchart TD", "class": "classDiagram",
                   "classdiagram": "classDiagram", "state": "stateDiagram-v2", "er": "erDiagram",
                   "mindmap": "mindmap"}

CALLOUT_TONES = {"warning": "warn", "info": "info", "tip": "good", "notice": "info", "alert": "warn"}
