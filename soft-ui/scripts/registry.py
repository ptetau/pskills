"""The component registry of soft-ui.

This file is the one source of truth for each component: its props, its shorthand, its
aliases, and its example. The catalog, the explain text, and the spec checks all read it.
"""

TONES = ["good", "warn", "bad", "info", "neutral"]
FMTS = ["int", "num", "pct", "ratio", "money", "k", "ms", "s", "bytes", "date", "time", "delta", "code", "md", "raw"]


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
    "fold": P("bool", default=False, doc="put the node in a folded card titled by its title"),
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

comp("compare", "layout", "the same thing several ways, or options side by side: equal columns, or a toggle",
     {"items": P("nodes", req=True), "mode": P("enum", enum=["side", "toggle"], default="side",
                                                 doc="side = equal columns; toggle = one at a time with a switch")},
     short="items", aliases=["versus", "vs", "side-by-side", "alternatives", "views"], example="""
- compare:
  - chart: {kind: bar, data: v, x: account, y: variance}
    title: As a chart
  - table: {data: v}
    title: As a table
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
      "spark": P("list", doc="list of numbers for a sparkline, or a column name (with data)"),
      "fmt": P("enum", enum=FMTS),
      "data": P("data", doc="compute value from data (follows filters)"),
      "of": P("any", doc="with data + where: true shows 'n / total rows' and a percent"),
      "vs": P("col", doc="with data: compare with the same agg of this column (e.g. budget); sets delta and tone"),
      "vs_label": P("str", doc="name of the vs value in the sub line, e.g. budget"),
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
      "order": P("list", doc="with by: tile order"),
      "cols": P("cols", doc="with data: one tile per column, summed (e.g. [revenue, expenses, profit])"),
      "labels": P("map", doc="{column: tile label}"),
      "fmt": P("enum", enum=FMTS)},
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

comp("callout", "summary", "highlighted message box (markdown); {{ sum d.col | money }} fills numbers from data",
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

comp("table", "data", "sortable table; group, filter, search, inline bars, tones, rows that expand",
     {"data": P("data", req=True),
      "cols": P("cols", doc="columns to show, in order: name or {key, label, fmt, w}"),
      "sort": P("str", doc="column to sort by; prefix - for descending"),
      "group": P("col", doc="group rows under a heading per value"),
      "filter": P("cols", doc="columns that get a filter dropdown; true = auto"),
      "search": P("bool", default=False, doc="add a text search box"),
      "limit": P("int", doc="rows per page"),
      "bar": P("cols", doc="numeric columns that get an inline bar"),
      "tone": P("map", doc="{col: {value: tone}} colours cells, e.g. {sev: {high: bad}} or thresholds {p95: {'>300': bad}}"),
      "fmt": P("map", doc="{col: fmt}; fmt is one of " + ", ".join(FMTS)),
      "expand": P("cols", doc="columns shown when a row is clicked open (long text, repro steps)"),
      "top": P("int", doc="show only the first N rows after sort"),
      "order": P("list", doc="group order, e.g. [Revenue, Cost of sales, Operating expenses]"),
      "labels": P("map", doc="{col: header label}"),
      "good": P("map", doc="{col: up|down} colours a delta column: which direction is good"),
      "dense": P("bool", default=False)},
     short="data", aliases=["grid-table", "datatable", "tbl"], data=True, example="""
- table:
    data: findings
    cols: [id, title, sev, flow]
    sort: -sev
    group: flow
    filter: [sev]
    tone: {sev: {high: bad, medium: warn, low: info}}
    expand: [detail, repro]
""")

comp("chart", "data", "bar, line, area, scatter (+trend), donut, waterfall, hist; x marks and bands",
     {"data": P("data", req=True), "kind": P("enum", enum=["bar", "line", "area", "scatter", "donut", "waterfall", "hist"], default="bar"),
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
      "mark": P("list", doc="reference lines: [{y: 300, label: SLO}] or [{x: 2026-11-20, label: release}]"),
      "band": P("list", doc="shaded x ranges: [{from: 2026-11-20, to: 2026-11-29, label: after}]"),
      "labels": P("map", doc="{column or series value: legend label}"),
      "trend": P("bool", default=False, doc="scatter: add a least-squares line and r²"),
      "bins": P("int", doc="hist: number of bins (default: auto)"),
      "total": P("str", doc="waterfall: label of a final total bar, e.g. Net profit"),
      "subtotals": P("list", doc="waterfall: [{after: Cost of sales, label: Gross profit}] adds running-total bars"),
      "height": P("int", default=260)},
     aliases=["plot"], data=True, example="""
- chart: {kind: line, data: lat, x: day, y: [p50, p95], fmt: ms, mark: [{y: 300, label: SLO}]}
- chart: {kind: bar, data: findings, x: sev, agg: count, series: flow, stack: true}
- chart: {kind: hist, data: outcomes, x: minutes, series: arm, bins: 12}
- chart: {kind: scatter, data: runs, x: size, y: ms, trend: true}
- chart: {kind: waterfall, data: bridge, x: step, y: amount, total: Net profit, fmt: money}
""")

comp("heatmap", "data", "grid of cells coloured by value (x by y)",
     {"data": P("data", req=True), "x": P("col", req=True), "y": P("col", req=True),
      "v": P("col", doc="value column; omit to count rows"),
      "agg": P("enum", enum=["count", "sum", "mean", "max"], default="sum"),
      "scale": P("enum", enum=["seq", "div"], default="seq", doc="seq = one hue; div = below/above zero"),
      "fmt": P("enum", enum=FMTS), "labels": P("bool", default=False, doc="print the value in each cell"),
      "worst": P("col", doc="colour each cell by the worst value of this severity column"),
      "totals": P("bool", default=False, doc="add row and column totals"),
      "xorder": P("list", doc="x value order, e.g. [low, medium, high]"), "yorder": P("list")},
     aliases=["matrix"], data=True, example="""
- heatmap: {data: churn, x: week, y: file, v: lines}
- heatmap: {data: findings, x: kind, y: flow, worst: sev, totals: true}   # counts, coloured by worst severity
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
      "tone": P("map"), "open": P("int", default=2, doc="levels open at start"),
      "sep": P("str", doc="path separator; default / (or > when paths use ' > ')")},
     short="paths", aliases=["filetree", "hierarchy", "outline"], data=True, example="""
- tree: {data: changed, path: file, badges: [added, removed]}
""")

comp("filter", "data", "filter chips with counts + search; filters every node on the dataset. Clicking a bar, heatmap cell, or stats-by tile also filters",
     {"data": P("data", req=True), "fields": P("cols", req=True), "search": P("bool", default=True)},
     aliases=["facets", "slicer"], data=True, example="""
- filter: {data: findings, fields: [sev, flow]}
""")

comp("statement", "data", "financial statement (P&L): sections, lines, subtotals, variance",
     {"data": P("data", req=True), "section": P("col", req=True, doc="e.g. Revenue, Cost of sales, Operating expenses"),
      "line": P("col", req=True, doc="account name"), "values": P("cols", req=True, doc="amount columns, e.g. [actual, budget]; rows are summed"),
      "minus": P("list", doc="sections subtracted from the running total, e.g. [Cost of sales, Operating expenses]"),
      "subtotals": P("list", doc="[{label: Gross profit, after: Cost of sales}, {label: Net profit, after: Operating expenses}]"),
      "variance": P("bool", default=True, doc="with 2 values: add difference and % (coloured good/bad by section sign)"),
      "fmt": P("enum", enum=FMTS, default="money"), "order": P("list", doc="section order"),
      "labels": P("map", doc="{value column: header label}")},
     aliases=["pnl", "p&l", "income-statement", "profit-and-loss", "financials"], data=True, example="""
- statement:
    data: pnl
    section: section
    line: account
    values: [actual, budget]
    minus: [Cost of sales, Operating expenses]
    subtotals: [{label: Gross profit, after: Cost of sales}, {label: Net profit, after: Operating expenses}]
""")

comp("box", "data", "box plots: median, quartiles, whiskers and outliers per group",
     {"data": P("data", req=True), "y": P("col", req=True, doc="numeric column"), "by": P("col", doc="one box per value"),
      "fmt": P("enum", enum=FMTS), "mean": P("bool", default=True, doc="mark the mean")},
     aliases=["boxplot", "box-plot", "whisker"], data=True, example="""
- box: {data: outcomes, y: minutes, by: arm}
""")

comp("forest", "data", "forest plot: estimate and confidence interval per row, with a pooled diamond",
     {"data": P("data", req=True), "label": P("col", req=True), "est": P("col", req=True), "lo": P("col", req=True),
      "hi": P("col", req=True), "weight": P("col", doc="marker size and a weight column"),
      "group": P("col", doc="colour (and badge) by this column, e.g. risk of bias"),
      "pooled": P("map", doc="{est, lo, hi, label} drawn as a diamond"),
      "null": P("num", default=0, doc="line of no effect (1 for ratios)"), "log": P("bool", default=False),
      "left": P("str", doc="label under the left side, e.g. favours treatment"), "right": P("str"),
      "fmt": P("enum", enum=FMTS), "tone": P("map")},
     aliases=["forestplot", "meta-analysis", "ci", "intervals"], data=True, example="""
- forest: {data: studies, label: study, est: md, lo: ci_low, hi: ci_high, weight: weight, group: bias,
           pooled: {est: -9.8, lo: -12.4, hi: -7.2, label: Pooled (RE)}, left: favours CBT-I, right: favours usual care}
""")

comp("treemap", "data", "nested rectangles sized by a value: code size, spend, disk use",
     {"data": P("data", req=True), "size": P("col", req=True), "group": P("col", doc="outer boxes"),
      "label": P("col", doc="cell label (default: first text column)"),
      "color": P("col", doc="numeric column for a sequential colour, e.g. commits"), "fmt": P("enum", enum=FMTS),
      "height": P("int", default=420)},
     aliases=["tree-map", "sizemap"], data=True, example="""
- treemap: {data: files, group: module, size: loc, color: commits_90d, label: path}
""")

comp("decision", "data", "options x criteria matrix with weights, weighted score, rank and margin",
     {"data": P("data", req=True), "option": P("col", req=True), "criteria": P("list", doc="score columns (or keys of a scores map)"),
      "scores": P("col", doc="column holding a {criterion: score} map"),
      "weights": P("any", doc="{criterion: weight} map, or a dataset with criterion and weight columns"),
      "max": P("num", default=5, doc="top of the score scale")},
     aliases=["matrix-decision", "options", "scorecard", "weighted"], data=True, example="""
- decision: {data: options, option: option, scores: scores, weights: criteria}
""")

comp("truth", "data", "truth table from boolean expressions (or rows); highlights rows where an output is 1",
     {"inputs": P("list", doc="input names, e.g. [armed, door_open, motion]"),
      "outputs": P("map", doc="{name: expression}, e.g. {alarm: armed and (door_open or motion)}"),
      "data": P("data", doc="or rows of 0/1 values"), "highlight": P("str", doc="output whose 1-rows are highlighted"),
      "only": P("bool", default=False, doc="start with only the highlighted rows shown")},
     aliases=["truthtable", "truth-table", "logic", "logic-table"], example="""
- truth: {inputs: [armed, door_open, motion], outputs: {alarm: "armed and (door_open or motion)"}, highlight: alarm}
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
      "tone": P("map", doc="{nodes column: {value: tone}}; colours nodes"),
      "text": P("str", doc="nodes column used as the node label (e.g. step name for id S1)"),
      "sign": P("col", doc="edge polarity column (+ / −): + solid, − dashed red, as in causal loop diagrams"),
      "cycles": P("bool", default=False, doc="draw edges that are part of a cycle in red, and list the cycles"),
      "edge_tone": P("map", doc="{edge column: {value: tone}} colours edges, e.g. {kind: {power: bad}}")},
     aliases=["network", "dag", "dependency-graph"], data=True, example="""
- graph: {data: deps, from: src, to: dst, dir: LR}
- graph: {data: d.calls, from: from, to: to, label: via, nodes: d.components, by: kind, tone: {volatility: {high: bad}}}
""")

comp("sankey", "diagram", "flows between nodes, width by value (budget, energy, traffic)",
     {"data": P("data", req=True), "from": P("col", req=True), "to": P("col", req=True), "value": P("col", req=True)},
     aliases=["flows", "alluvial"], data=True, example="""
- sankey: {data: flows, from: source, to: target, value: amount}
""")

comp("er", "diagram", "entity-relationship diagram from schema rows (table, column, type, key, references)",
     {"data": P("data", req=True), "table": P("col", req=True), "column": P("col", req=True), "type": P("col"),
      "key": P("col", doc="pk / fk"), "ref": P("col", doc="referenced table.column for a foreign key"),
      "keys_only": P("bool", default=False, doc="show only key columns (large schemas)")},
     aliases=["erd", "schema", "entity-relationship", "db-diagram"], data=True, example="""
- er: {data: schema, table: table, column: column, type: type, key: key, ref: references}
""")

comp("classes", "diagram", "class / type diagram from rows (name, fields, methods, extends)",
     {"data": P("data", req=True), "name": P("col", req=True), "fields": P("col", doc="list or comma text, e.g. 'id: Id'"),
      "methods": P("col"), "extends": P("col"), "link": P("bool", default=True, doc="draw arrows for fields typed as another class")},
     aliases=["classdiagram-data", "types", "contracts", "uml-classes"], data=True, example="""
- classes: {data: contracts, name: type, fields: fields}
""")

PAGE_KEYS = {
    "title": P("str", req=True), "subtitle": P("str"), "meta": P("any", doc="list of badges, or a map"),
    "data": P("map", doc="named datasets"), "layout": P("nodes", req=True),
    "width": P("enum", enum=["narrow", "normal", "wide", "full"], default="normal"),
    "accent": P("str", doc="CSS colour for the accent"),
    "currency": P("str", doc="for fmt money: NZD, USD, EUR, GBP or a symbol"),
    "base": P("str", doc="folder that data paths start from, e.g. ../../reports/R1"),
    "theme": P("enum", enum=["default", "quarterly"], default="default",
               doc="look: default, or quarterly (editorial print on a black-and-grey workstation)"),
}

# Common wrong prop names, mapped to the right one. Fuzzy matching catches the rest.
PROP_ALIASES = {
    "collapse": "fold", "collapsed": "fold", "folded": "fold", "folding": "fold",
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
CHART_KINDS = {"waterfall": "waterfall", "bridge": "waterfall", "hist": "hist", "histogram": "hist", "bar": "bar", "bars": "bar", "barchart": "bar", "column-chart": "bar",
               "line": "line", "linechart": "line", "lines": "line", "area": "area", "areachart": "area",
               "scatter": "scatter", "scatterplot": "scatter", "dots": "scatter", "pie": "donut",
               "donut": "donut", "doughnut": "donut", "piechart": "donut"}

# Mermaid header for each diagram alias, used when the source has no header.
MERMAID_HEADERS = {"sequence": "sequenceDiagram", "sequencediagram": "sequenceDiagram",
                   "flowchart": "flowchart TD", "flow": "flowchart TD", "class": "classDiagram",
                   "classdiagram": "classDiagram", "state": "stateDiagram-v2", "er": "erDiagram",
                   "mindmap": "mindmap"}

CALLOUT_TONES = {"warning": "warn", "info": "info", "tip": "good", "notice": "info", "alert": "warn"}
