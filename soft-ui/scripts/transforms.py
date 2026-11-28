"""Data transforms for soft-ui datasets.

A dataset definition can shape its rows before any node sees them:

  d:
    file: results.csv        # or rows:, csv:, or from: <an earlier dataset>
    where: {status: failed}   # keep matching rows; values can be lists or ">300"
    explode: after            # one row per item of a list column
    join: {data: other, on: key, cols: [a, b]}   # add columns from another dataset
    add: {delta: "after - before"}               # computed columns (before group)
    group: [suite]            # one row per group ...
    sum: [ms]                 # ... with these aggregates (also mean, min, max, count)
    pct: [ms]                 # add <col>_pct = share of the column total
    describe: [minutes]       # n, mean, sd, min, q1, median, q3, max (by: col)
    corr: [a, b, c]           # correlation rows: a, b, r
    then: {share: "ms / 1000"}   # computed columns after group
    sort: -ms
    top: 10
    rename: {ms: Time}

Each step reports a short error with the right names when a column is wrong.
"""

import math
import re
import statistics

STEP_KEYS = ("where", "join", "explode", "add", "group", "sum", "mean", "min", "max", "count", "pct", "describe",
             "by", "corr", "then", "sort", "top", "rename", "select")
SOURCE_KEYS = ("file", "path", "src", "rows", "csv", "from")


def is_transform(val):
    return isinstance(val, dict) and any(k in val for k in SOURCE_KEYS) and any(k in val for k in STEP_KEYS)


def _cols(rows):
    out = []
    for r in rows[:500]:
        for k in r:
            if k not in out:
                out.append(k)
    return out


def _list(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [x.strip() for x in v.split(",") if x.strip()]
    return list(v) if isinstance(v, (list, tuple)) else [v]


def _match(v, want):
    if isinstance(want, list):
        return str(v) in [str(w) for w in want]
    if isinstance(want, str):
        m = re.match(r"^(>=|<=|!=|>|<)\s*(.+)$", want)
        if m:
            o, x = m.group(1), m.group(2).strip()
            try:
                a, b = float(v), float(x)
            except (TypeError, ValueError):
                a, b = str(v), x
            return {">=": a >= b, "<=": a <= b, ">": a > b, "<": a < b, "!=": a != b}[o]
    return str(v) == str(want)


def apply(ctx, rows, spec, path, fix_col, add_columns):
    """Run each transform step of spec over rows. fix_col(cols, name, step) returns a column or None."""
    rows = [dict(r) for r in rows]

    def col(name, step):
        return fix_col(_cols(rows), name, f"{path}.{step}")

    if "where" in spec:
        w = spec["where"]
        if isinstance(w, dict):
            conds = [(col(k, "where"), v) for k, v in w.items()]
            conds = [(c, v) for c, v in conds if c]
            rows = [r for r in rows if all(_match(r.get(c), v) for c, v in conds)]
        else:
            ctx.err(path, 'where must be a map, e.g. where: {status: failed} or {ms: ">500"}')
    if "explode" in spec:
        c = col(spec["explode"], "explode")
        if c:
            out = []
            for r in rows:
                v = r.get(c)
                items = v if isinstance(v, list) else ([] if v in (None, "") else [v])
                for it in items:
                    out.append({**r, c: it})
            rows = out
    if "join" in spec:
        j = spec["join"]
        other = ctx.data.get(j.get("data")) if isinstance(j, dict) else None
        if not other:
            ctx.err(path, f"join needs data: <an earlier dataset>. Datasets: {', '.join(ctx.data) or 'none'}")
        else:
            on = _list(j.get("on"))
            left = col(on[0], "join.on") if on else None
            right = fix_col(other["cols"], on[-1], f"{path}.join.on") if on else None
            if left and right:
                take = [c for c in (_list(j.get("cols")) or [c for c in other["cols"] if c != right])]
                take = [fix_col(other["cols"], c, f"{path}.join.cols") for c in take]
                index = {}
                for o in other["rows"]:
                    index.setdefault(str(o.get(right)), o)
                for r in rows:
                    o = index.get(str(r.get(left)), {})
                    for c in take:
                        if c and c not in r:
                            r[c] = o.get(c)
            elif not on:
                ctx.err(path, "join needs on: <key column> (or [left, right])")
    if "add" in spec:
        rows = add_columns(ctx, rows, spec["add"], path + ".add")
    aggs = {a: _list(spec.get(a)) for a in ("sum", "mean", "min", "max")}
    if "group" in spec:
        keys = [col(k, "group") for k in _list(spec["group"])]
        keys = [k for k in keys if k]
        for a in aggs:
            aggs[a] = [c for c in (col(x, a) for x in aggs[a]) if c]
        cname = spec.get("count", "count")
        cname = "count" if cname is True else cname
        groups = {}
        for r in rows:
            groups.setdefault(tuple(str(r.get(k)) for k in keys), []).append(r)
        out = []
        for g, rs in groups.items():
            row = {k: rs[0].get(k) for k in keys}
            if cname:
                row[cname] = len(rs)
            for a, cs in aggs.items():
                for c in cs:
                    vals = [float(x[c]) for x in rs if isinstance(x.get(c), (int, float)) and not isinstance(x.get(c), bool)]
                    if not vals:
                        row[c] = None
                        continue
                    v = sum(vals) if a == "sum" else statistics.fmean(vals) if a == "mean" else min(vals) if a == "min" else max(vals)
                    name = c if sum(1 for x in aggs.values() if c in x) == 1 else f"{c}_{a}"
                    row[name] = int(v) if float(v).is_integer() and a != "mean" else round(v, 4)
            out.append(row)
        rows = out
    if "pct" in spec:
        for c in _list(spec["pct"]):
            c2 = col(c, "pct")
            if c2:
                tot = sum(float(r.get(c2) or 0) for r in rows) or 1
                for r in rows:
                    r[f"{c2}_pct"] = round(100 * float(r.get(c2) or 0) / tot, 1)
    if "describe" in spec:
        by = col(spec["by"], "by") if spec.get("by") else None
        targets = [c for c in (col(x, "describe") for x in _list(spec["describe"])) if c]
        groups = {}
        for r in rows:
            groups.setdefault(r.get(by) if by else None, []).append(r)
        out = []
        for g, rs in groups.items():
            for c in targets:
                v = sorted(float(r[c]) for r in rs if isinstance(r.get(c), (int, float)) and not isinstance(r.get(c), bool))
                if not v:
                    continue
                q = statistics.quantiles(v, n=4) if len(v) > 1 else [v[0]] * 3
                row = ({by: g} if by else {}) | {"measure": c, "n": len(v), "mean": round(statistics.fmean(v), 3),
                                                 "sd": round(statistics.stdev(v), 3) if len(v) > 1 else 0,
                                                 "min": v[0], "q1": round(q[0], 3), "median": round(statistics.median(v), 3),
                                                 "q3": round(q[2], 3), "max": v[-1]}
                out.append(row)
        rows = out
    if "corr" in spec:
        cs = [c for c in (col(x, "corr") for x in _list(spec["corr"])) if c]
        out = []
        for a in cs:
            for b in cs:
                pairs = [(float(r[a]), float(r[b])) for r in rows
                         if isinstance(r.get(a), (int, float)) and isinstance(r.get(b), (int, float))]
                out.append({"a": a, "b": b, "r": round(_pearson(pairs), 3) if len(pairs) > 2 else None})
        rows = out
    if "then" in spec:
        rows = add_columns(ctx, rows, spec["then"], path + ".then")
    if "sort" in spec:
        s = str(spec["sort"])
        c = col(s.lstrip("-+"), "sort")
        if c:
            rows.sort(key=lambda r: (r.get(c) is None, r.get(c) if isinstance(r.get(c), (int, float)) else str(r.get(c))),
                      reverse=s.startswith("-"))
            if s.startswith("-"):
                rows.sort(key=lambda r: r.get(c) is None)
    if "top" in spec:
        try:
            rows = rows[:int(spec["top"])]
        except (TypeError, ValueError):
            ctx.err(path, "top must be a number")
    if "rename" in spec and isinstance(spec["rename"], dict):
        ren = {col(k, "rename"): v for k, v in spec["rename"].items()}
        rows = [{ren.get(k, k) or k: v for k, v in r.items()} for r in rows]
    if "select" in spec:
        keep = [c for c in (col(x, "select") for x in _list(spec["select"])) if c]
        rows = [{k: r.get(k) for k in keep} for r in rows]
    return rows


def _pearson(pairs):
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if not sx or not sy:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in pairs) / (sx * sy)
